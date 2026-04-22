import os
from datetime import datetime


def ensure_capture_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def build_capture_filename(label: str, event_id: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{label}_{event_id}.jpg"


def build_capture_path(save_dir: str, filename: str) -> str:
    return os.path.join(save_dir, filename)


def build_public_image_path(filename: str) -> str:
    return f"/static/captures/{filename}"
