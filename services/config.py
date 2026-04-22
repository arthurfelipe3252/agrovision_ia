import os
from dataclasses import dataclass


def _load_env_file(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def _parse_source(raw_source: str):
    if raw_source.isdigit():
        return int(raw_source)
    return raw_source


def _parse_target_classes(raw_target_classes: str) -> set[str]:
    values = [item.strip() for item in raw_target_classes.split(",")]
    return {item for item in values if item}


@dataclass(frozen=True)
class AppConfig:
    app_title: str
    camera_source: int | str
    camera_reconnect_seconds: float
    model_path: str
    confidence_threshold: float
    target_classes: set[str]
    save_dir: str
    db_path: str
    min_consecutive_frames: int
    alert_cooldown_seconds: int
    ollama_url: str
    ollama_model: str
    ollama_timeout: int
    ollama_keep_alive: str
    agent_event_limit: int
    max_history_messages: int


def load_config() -> AppConfig:
    _load_env_file()
    return AppConfig(
        app_title=os.getenv("APP_TITLE", "AgroVision AI"),
        camera_source=_parse_source(os.getenv("CAMERA_SOURCE", "0")),
        camera_reconnect_seconds=float(os.getenv("CAMERA_RECONNECT_SECONDS", "5")),
        model_path=os.getenv("MODEL_PATH", "yolov8n.pt"),
        confidence_threshold=float(os.getenv("CONFIDENCE_THRESHOLD", "0.45")),
        target_classes=_parse_target_classes(
            os.getenv("TARGET_CLASSES", "person,car,motorcycle,truck,bus")
        ),
        save_dir=os.getenv("SAVE_DIR", "static/captures"),
        db_path=os.getenv("DB_PATH", "detections.db"),
        min_consecutive_frames=int(os.getenv("MIN_CONSECUTIVE_FRAMES", "3")),
        alert_cooldown_seconds=int(os.getenv("ALERT_COOLDOWN_SECONDS", "20")),
        ollama_url=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/chat"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3"),
        ollama_timeout=int(os.getenv("OLLAMA_TIMEOUT", "120")),
        ollama_keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", "30m"),
        agent_event_limit=int(os.getenv("AGENT_EVENT_LIMIT", "12")),
        max_history_messages=int(os.getenv("MAX_HISTORY_MESSAGES", "8")),
    )
