import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from services.agent.monitoring_agent import (
    AGENT_PROFILE,
    build_agent_messages,
    build_event_context,
)
from services.agent.ollama_client import OllamaClient
from services.agent.schemas import ChatRequest
from services.alerts.alert_engine import AlertEngine
from services.config import load_config
from services.domain import LlmUnavailableError, RateLimiter
from services.persistence.event_repository import EventRepository
from services.security.auth import build_api_key_dependency
from services.security.errors import (
    GENERIC_AGENT_ERROR,
    GENERIC_RATE_LIMIT_MESSAGE,
    GENERIC_UPSTREAM_ERROR,
)
from services.security.headers import SecurityHeadersMiddleware
from services.security.prompt_safety import (
    DEFENSIVE_SYSTEM_RULES,
    sanitize_user_prompt,
)
from services.security.rate_limiter import InMemoryRateLimiter
from services.video_monitor import VideoMonitor
from services.vision.yolo_detector import YoloDetector


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("agrovision")


config = load_config()
event_repository = EventRepository(config.db_path)
detector = YoloDetector(
    model_path=config.model_path,
    confidence_threshold=config.confidence_threshold,
    target_classes=config.target_classes,
)
alert_engine = AlertEngine(
    target_classes=config.target_classes,
    min_consecutive_frames=config.min_consecutive_frames,
    alert_cooldown_seconds=config.alert_cooldown_seconds,
    save_dir=config.save_dir,
)
video_monitor = VideoMonitor(
    config=config,
    detector=detector,
    alert_gate=alert_engine,
    event_store=event_repository,
)
ollama_client = OllamaClient(
    base_url=config.ollama_url,
    model=config.ollama_model,
    timeout=config.ollama_timeout,
    keep_alive=config.ollama_keep_alive,
)

require_api_key = build_api_key_dependency(config.api_key)
chat_rate_limiter: RateLimiter = InMemoryRateLimiter(
    max_requests=config.chat_rate_limit_per_minute,
    window_seconds=config.chat_rate_limit_window_seconds,
)
assert isinstance(chat_rate_limiter, RateLimiter), "chat_rate_limiter deve cumprir o port RateLimiter"


def enforce_chat_rate_limit(request: Request) -> None:
    identity = request.client.host if request.client else "anon"
    if not chat_rate_limiter.allow(identity):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=GENERIC_RATE_LIMIT_MESSAGE,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    event_repository.init()
    video_monitor.start()
    # Warmup roda em background para nao bloquear o boot enquanto o
    # modelo carrega no Ollama. A primeira pergunta pode ainda esperar
    # se o warmup nao tiver terminado, mas o servidor ja aceita requests.
    asyncio.create_task(asyncio.to_thread(ollama_client.warmup))
    yield


app = FastAPI(title=config.app_title, lifespan=lifespan)
app.add_middleware(SecurityHeadersMiddleware)

os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    events = event_repository.list_recent(20)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "events": events,
            "api_key_required": bool(config.api_key),
        },
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": config.app_title,
        "api_key_required": bool(config.api_key),
    }


@app.get("/events", dependencies=[Depends(require_api_key)])
def get_events():
    return JSONResponse(content=event_repository.list_recent(50))


@app.get("/frame", dependencies=[Depends(require_api_key)])
def get_frame():
    frame = video_monitor.get_frame_jpeg()
    if frame is None:
        return JSONResponse(
            content={"message": "Ainda sem frame disponivel."},
            status_code=503,
        )
    return Response(content=frame, media_type="image/jpeg")


@app.get("/camera/status", dependencies=[Depends(require_api_key)])
def camera_status():
    return video_monitor.get_status()


@app.get("/video_feed", dependencies=[Depends(require_api_key)])
def video_feed():
    sleep_interval = 1.0 / config.video_feed_fps
    boundary = b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"

    def frame_generator():
        try:
            while True:
                frame = video_monitor.get_frame_jpeg()
                if frame is not None:
                    yield boundary + frame + b"\r\n"
                time.sleep(sleep_interval)
        except (BrokenPipeError, ConnectionResetError, GeneratorExit):
            return

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/agent/status", dependencies=[Depends(require_api_key)])
def agent_status():
    recent_events = event_repository.list_recent(config.agent_event_limit)
    return {
        "name": AGENT_PROFILE.name,
        "role": AGENT_PROFILE.role,
        "goal": AGENT_PROFILE.goal,
        "events_in_context": len(recent_events),
        "context_preview": build_event_context(recent_events)[:600],
    }


@app.post(
    "/chat/stream",
    dependencies=[Depends(require_api_key), Depends(enforce_chat_rate_limit)],
)
def chat_stream(payload: ChatRequest):
    events = event_repository.list_recent(config.agent_event_limit)
    messages = build_agent_messages(
        question=payload.question,
        history=[m.model_dump() for m in payload.history],
        events=events,
        max_history_messages=config.max_history_messages,
        sanitize_user=sanitize_user_prompt,
        defensive_rules=DEFENSIVE_SYSTEM_RULES,
    )

    def stream_generator():
        try:
            for chunk in ollama_client.chat_stream(messages):
                yield chunk
        except LlmUnavailableError:
            logger.warning("Upstream LLM indisponivel")
            yield f"\n{GENERIC_UPSTREAM_ERROR}"
        except Exception:
            logger.exception("Falha ao gerar resposta do agente")
            yield f"\n{GENERIC_AGENT_ERROR}"

    return StreamingResponse(stream_generator(), media_type="text/plain; charset=utf-8")
