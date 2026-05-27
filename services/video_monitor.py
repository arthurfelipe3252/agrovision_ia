"""Orquestrador do pipeline de visão.

Aplica o padrão **Pipes & Filters** sobre os ports do domínio:

    frame -> Detector.detect       -> list[Detection]
          -> Detector.annotate     -> frame anotado (cópia)
          -> AlertGate.submit      -> list[AlertEvent]
          -> EventStore.save       -> persistência

Não conhece YOLO, OpenCV (além do VideoCapture) nem SQLite. As
dependências chegam pelo construtor já tipadas pelos Protocols em
`services.domain`, e a validação estrutural é feita via
`isinstance` para detectar quebra de contrato no boot.
"""

import threading
import time

import cv2

from services.config import AppConfig
from services.domain import AlertGate, Detector, EventStore


class VideoMonitor:
    def __init__(
        self,
        config: AppConfig,
        detector: Detector,
        alert_gate: AlertGate,
        event_store: EventStore,
    ) -> None:
        assert isinstance(detector, Detector), "detector deve cumprir o port Detector"
        assert isinstance(alert_gate, AlertGate), "alert_gate deve cumprir o port AlertGate"
        assert isinstance(event_store, EventStore), "event_store deve cumprir o port EventStore"

        self.config = config
        self.detector = detector
        self.alert_gate = alert_gate
        self.event_store = event_store

        self.last_frame = None
        self.last_frame_lock = threading.Lock()
        self.capture_online = False
        self.connected = False
        self.stop_event = threading.Event()

    def start(self) -> None:
        thread = threading.Thread(target=self._process_stream, daemon=True)
        thread.start()

    def _process_stream(self) -> None:
        while not self.stop_event.is_set():
            cap = cv2.VideoCapture(self.config.camera_source)
            if not cap.isOpened():
                self.capture_online = False
                self.connected = False
                time.sleep(self.config.camera_reconnect_seconds)
                continue

            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except cv2.error:
                pass

            self.capture_online = True
            self.connected = True

            while not self.stop_event.is_set():
                ok, frame = cap.read()
                if not ok:
                    self.connected = False
                    break

                self.connected = True
                self._process_frame(frame)

            cap.release()
            time.sleep(self.config.camera_reconnect_seconds)

    def _process_frame(self, frame) -> None:
        detections = self.detector.detect(frame)
        annotated = self.detector.annotate(frame, detections)
        for event in self.alert_gate.submit(detections, annotated):
            self.event_store.save(event)
        with self.last_frame_lock:
            self.last_frame = annotated

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
