"""Adapter de visão computacional baseado em Ultralytics YOLO.

Implementa o port `services.domain.Detector`. Responsabilidades:

- carregar o modelo `.pt` no construtor;
- expor `detect(frame)` retornando uma lista imutável de `Detection`
  já filtrada por `target_classes`;
- expor `annotate(frame, detections)` que **devolve uma cópia** do
  frame com as bounding boxes desenhadas (não muta o original).
"""

from typing import Any

import cv2
from ultralytics import YOLO

from services.domain import Detection


class YoloDetector:
    def __init__(
        self,
        model_path: str,
        confidence_threshold: float,
        target_classes: set[str],
    ) -> None:
        self._model = YOLO(model_path)
        self._confidence_threshold = confidence_threshold
        self._target_classes = target_classes

    def detect(self, frame: Any) -> list[Detection]:
        results = self._model(frame, conf=self._confidence_threshold, verbose=False)
        detections: list[Detection] = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                cls_id = int(box.cls[0].item())
                label = self._model.names[cls_id]
                if label not in self._target_classes:
                    continue
                confidence = float(box.conf[0].item())
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                detections.append(
                    Detection(label=label, confidence=confidence, bbox=(x1, y1, x2, y2))
                )
        return detections

    def annotate(self, frame: Any, detections: list[Detection]) -> Any:
        annotated = frame.copy()
        for detection in detections:
            x1, y1, x2, y2 = detection.bbox
            text = f"{detection.label} {detection.confidence:.2f}"
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                annotated,
                text,
                (x1, max(20, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )
        return annotated
