"""Regra de negócio que converte detecções em eventos operacionais.

Implementa o port `services.domain.AlertGate`. Mantém duas pequenas
state machines por label:

- `_consecutive_frames` — quantos frames seguidos o label apareceu;
- `_last_alert_time` — última vez que aquele label disparou evento.

Um evento só é emitido quando:
    consecutive_frames[label] >= min_consecutive_frames
e
    now - last_alert_time[label] > alert_cooldown_seconds

A escrita do JPEG anotado em disco é responsabilidade desta camada,
porque é parte do mesmo "ato" de emitir o evento (mantém atomicidade
entre arquivo e linha no banco).
"""

import threading
import time
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any

import cv2

from services.domain import AlertEvent, Detection
from services.vision.capture_store import (
    build_capture_filename,
    build_capture_path,
    build_public_image_path,
    ensure_capture_dir,
)


class AlertEngine:
    def __init__(
        self,
        target_classes: set[str],
        min_consecutive_frames: int,
        alert_cooldown_seconds: int,
        save_dir: str,
    ) -> None:
        self._target_classes = target_classes
        self._min_consecutive_frames = min_consecutive_frames
        self._alert_cooldown_seconds = alert_cooldown_seconds
        self._save_dir = save_dir
        self._consecutive_frames: dict[str, int] = defaultdict(int)
        self._last_alert_time: dict[str, float] = defaultdict(lambda: 0.0)
        self._lock = threading.Lock()
        ensure_capture_dir(self._save_dir)

    def submit(
        self, detections: list[Detection], annotated_frame: Any
    ) -> list[AlertEvent]:
        with self._lock:
            found_labels = {detection.label for detection in detections}
            best_confidence_by_label: dict[str, float] = {}
            for detection in detections:
                current = best_confidence_by_label.get(detection.label, 0.0)
                if detection.confidence > current:
                    best_confidence_by_label[detection.label] = detection.confidence

            for label in self._target_classes:
                if label in found_labels:
                    self._consecutive_frames[label] += 1
                else:
                    self._consecutive_frames[label] = 0

            now = time.time()
            events: list[AlertEvent] = []
            for label in found_labels:
                if self._consecutive_frames[label] < self._min_consecutive_frames:
                    continue
                if (now - self._last_alert_time[label]) <= self._alert_cooldown_seconds:
                    continue

                event_id = str(uuid.uuid4())[:8]
                filename = build_capture_filename(label, event_id)
                filepath = build_capture_path(self._save_dir, filename)
                cv2.imwrite(filepath, annotated_frame)
                public_path = build_public_image_path(filename)

                event = AlertEvent(
                    event_id=event_id,
                    event_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    label=label,
                    confidence=best_confidence_by_label.get(label, 0.0),
                    image_path=public_path,
                )
                events.append(event)
                self._last_alert_time[label] = now

            return events
