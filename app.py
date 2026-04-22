import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from services.config import load_config
from services.event_repository import EventRepository
from services.monitoring_agent import AGENT_PROFILE, build_agent_messages, build_event_context
from services.ollama_client import OllamaClient
from services.schemas import ChatRequest
from services.video_monitor import VideoMonitor

config = load_config()
event_repository = EventRepository(config.db_path)
video_monitor = VideoMonitor(config, event_repository)
ollama_client = OllamaClient(
    base_url=config.ollama_url,
    model=config.ollama_model,
    timeout=config.ollama_timeout,
    keep_alive=config.ollama_keep_alive,
)

app = FastAPI(title=config.app_title)

os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def startup_event():
    event_repository.init_db()
    video_monitor.start()
    ollama_client.warmup()


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    events = event_repository.list_events(20)
    return templates.TemplateResponse(request=request, name="index.html", context={"events": events})


@app.get("/health")
def health():
    return {"status": "ok", "service": config.app_title}


@app.get("/events")
def get_events():
    return JSONResponse(content=event_repository.list_events(50))


@app.get("/frame")
def get_frame():
    frame = video_monitor.get_frame_jpeg()
    if frame is None:
        return JSONResponse(content={"message": "Ainda sem frame disponivel."}, status_code=503)
    return Response(content=frame, media_type="image/jpeg")


@app.get("/camera/status")
def camera_status():
    return video_monitor.get_status()


@app.get("/video_feed")
def video_feed():
    def frame_generator():
        boundary = b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
        while True:
            frame = video_monitor.get_frame_jpeg()
            if frame is not None:
                yield boundary + frame + b"\r\n"

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/agent/status")
def agent_status():
    recent_events = event_repository.list_events(config.agent_event_limit)
    return {
        "name": AGENT_PROFILE.name,
        "role": AGENT_PROFILE.role,
        "goal": AGENT_PROFILE.goal,
        "events_in_context": len(recent_events),
        "context_preview": build_event_context(recent_events)[:600],
    }


@app.post("/chat/stream")
def chat_stream(payload: ChatRequest):
    events = event_repository.list_events(config.agent_event_limit)
    messages = build_agent_messages(
        question=payload.question,
        history=[m.model_dump() for m in payload.history],
        events=events,
        max_history_messages=config.max_history_messages,
    )

    def stream_generator():
        try:
            for chunk in ollama_client.chat_stream(messages):
                yield chunk
        except Exception as error:
            yield f"\n[ERRO] {error}"

    return StreamingResponse(stream_generator(), media_type="text/plain; charset=utf-8")
