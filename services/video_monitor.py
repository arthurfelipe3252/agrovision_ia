import threading
import time
import uuid
from collections import defaultdict

import cv2
from ultralytics import YOLO

from services.capture_store import (
    build_capture_filename,
    build_capture_path,
    build_public_image_path,
    ensure_capture_dir,
)
from services.config import AppConfig
from services.event_repository import EventRepository


class VideoMonitor:
    def __init__(self, config: AppConfig, event_repository: EventRepository):
        self.config = config
        self.event_repository = event_repository
        self.model = YOLO(config.model_path)
        self.last_frame = None
        self.last_frame_lock = threading.Lock()
        self.detection_state = defaultdict(int)
        self.last_alert_time = defaultdict(lambda: 0.0)
        self.capture_online = False
        self.connected = False
        self.stop_event = threading.Event()
        ensure_capture_dir(self.config.save_dir)

    def start(self) -> None:
        thread = threading.Thread(target=self._process_stream, daemon=True)
        thread.start()

    def _should_alert(self, label: str) -> bool:
        now = time.time()
        return (now - self.last_alert_time[label]) > self.config.alert_cooldown_seconds

    def _process_stream(self) -> None:
        while not self.stop_event.is_set():
            cap = cv2.VideoCapture(self.config.camera_source)
            if not cap.isOpened():
                self.capture_online = False
                self.connected = False
                time.sleep(self.config.camera_reconnect_seconds)
                continue

            self.capture_online = True
            self.connected = True

            while not self.stop_event.is_set():
                ok, frame = cap.read()
                if not ok:
                    self.connected = False
                    break

                self.connected = True
                self._process_frame(frame)
                time.sleep(0.05)

            cap.release()
            time.sleep(self.config.camera_reconnect_seconds)

    def _process_frame(self, frame) -> None:
        results = self.model(frame, conf=self.config.confidence_threshold, verbose=False)

        found_labels = set()
        best_conf_by_label = {}

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for box in boxes:
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                label = self.model.names[cls_id]
                if label not in self.config.target_classes:
                    continue

                found_labels.add(label)
                if label not in best_conf_by_label or conf > best_conf_by_label[label]:
                    best_conf_by_label[label] = conf

                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                self._draw_box(frame, x1, y1, x2, y2, label, conf)

        for label in self.config.target_classes:
            self.detection_state[label] = self.detection_state[label] + 1 if label in found_labels else 0

        for label in found_labels:
            if (
                self.detection_state[label] >= self.config.min_consecutive_frames
                and self._should_alert(label)
            ):
                event_id = str(uuid.uuid4())[:8]
                filename = build_capture_filename(label, event_id)
                filepath = build_capture_path(self.config.save_dir, filename)
                cv2.imwrite(filepath, frame)
                image_path = build_public_image_path(filename)
                confidence = best_conf_by_label.get(label, 0.0)
                self.event_repository.save_event(event_id, label, confidence, image_path)
                self.last_alert_time[label] = time.time()

        with self.last_frame_lock:
            self.last_frame = frame.copy()

    @staticmethod
    def _draw_box(frame, x1, y1, x2, y2, label, confidence) -> None:
        text = f"{label} {confidence:.2f}"
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(
            frame,
            text,
            (x1, max(20, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )

    def get_frame_jpeg(self):
        with self.last_frame_lock:
            if self.last_frame is None:
                return None
            success, buffer = cv2.imencode(".jpg", self.last_frame)
            if not success:
                return None
            return buffer.tobytes()

    def get_status(self) -> dict:
        source_type = "webcam" if isinstance(self.config.camera_source, int) else "stream"
        has_frame = self.get_frame_jpeg() is not None
        return {
            "online": self.capture_online,
            "connected": self.connected,
            "has_live_frame": has_frame,
            "source_type": source_type,
        }
