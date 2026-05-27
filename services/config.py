import os
from dataclasses import dataclass

from dotenv import load_dotenv


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
    api_key: str
    chat_rate_limit_per_minute: int
    chat_rate_limit_window_seconds: int
    video_feed_fps: int
    weather_alerts_url: str
    weather_alerts_min_interval_seconds: int
    weather_alerts_max_items: int


def load_config() -> AppConfig:
    load_dotenv(override=False)
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
        api_key=os.getenv("API_KEY", "").strip(),
        chat_rate_limit_per_minute=int(os.getenv("CHAT_RATE_LIMIT_PER_MINUTE", "20")),
        chat_rate_limit_window_seconds=int(
            os.getenv("CHAT_RATE_LIMIT_WINDOW_SECONDS", "60")
        ),
        video_feed_fps=max(1, int(os.getenv("VIDEO_FEED_FPS", "15"))),
        weather_alerts_url=os.getenv(
            "WEATHER_ALERTS_URL",
            "https://apiprevmet3.inmet.gov.br/avisos/rss",
        ),
        weather_alerts_min_interval_seconds=int(
            os.getenv("WEATHER_ALERTS_MIN_INTERVAL_SECONDS", "900")
        ),
        weather_alerts_max_items=int(os.getenv("WEATHER_ALERTS_MAX_ITEMS", "8")),
    )
