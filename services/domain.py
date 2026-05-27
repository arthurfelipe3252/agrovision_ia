"""Tipos de domínio e contratos (ports) do AgroVision AI.

Este módulo é uma folha (leaf): não importa nada de `services/*`,
para evitar ciclos. Concentra:

- **Value objects** imutáveis trafegados entre camadas (`Detection`,
  `AlertEvent`).
- **Ports** (interfaces estruturais) que cada adapter de infraestrutura
  deve cumprir (`Detector`, `AlertGate`, `EventStore`, `LlmClient`).

Todos os Protocols são `@runtime_checkable`, o que permite que o
composition root valide as dependências injetadas via `isinstance`.
"""

from dataclasses import dataclass
from typing import Any, Iterable, Protocol, runtime_checkable


@dataclass(frozen=True)
class Detection:
    """Detecção bruta de um objeto em um frame, já filtrada por classe-alvo."""

    label: str
    confidence: float
    bbox: tuple[int, int, int, int]


@dataclass(frozen=True)
class AlertEvent:
    """Evento operacional emitido pelo gate de alertas e persistido pelo store."""

    event_id: str
    event_time: str
    label: str
    confidence: float
    image_path: str


@runtime_checkable
class Detector(Protocol):
    """Port para serviços de visão. Inferência + anotação visual."""

    def detect(self, frame: Any) -> list[Detection]:
        ...

    def annotate(self, frame: Any, detections: list[Detection]) -> Any:
        """Retorna uma NOVA matriz anotada. Nunca muta `frame`."""
        ...


@runtime_checkable
class AlertGate(Protocol):
    """Port para a regra de negócio que converte detecções em eventos."""

    def submit(
        self, detections: list[Detection], annotated_frame: Any
    ) -> list[AlertEvent]:
        ...


@runtime_checkable
class EventStore(Protocol):
    """Port para persistência de eventos.

    `list_recent` retorna `list[dict]` deliberadamente: é o contrato
    público consumido pelo dashboard via /events. Manter shape estável.
    """

    def init(self) -> None:
        ...

    def save(self, event: AlertEvent) -> None:
        ...

    def list_recent(self, limit: int) -> list[dict]:
        ...


@runtime_checkable
class LlmClient(Protocol):
    """Port para clientes de modelos de linguagem (chat com streaming).

    Implementacoes devem levantar `LlmUnavailableError` quando o upstream
    estiver inacessivel ou retornar erro tecnico. A camada de transporte
    e responsavel por mapear isso em mensagem publica segura.
    """

    def chat_stream(self, messages: list[dict]) -> Iterable[str]:
        ...

    def warmup(self) -> bool:
        ...


@runtime_checkable
class WeatherAlertSource(Protocol):
    """Port para fontes externas de alertas climaticos."""

    def fetch_alerts(self) -> dict:
        ...


@runtime_checkable
class RateLimiter(Protocol):
    """Port para limitadores de taxa por identidade (IP, usuario, etc.)."""

    def allow(self, identity: str) -> bool:
        ...


class LlmUnavailableError(Exception):
    """Sinaliza falha de upstream em adapters de `LlmClient`.

    Capturada pela camada de transporte (`app.py`), que decide qual
    mensagem publica devolver ao cliente. O detalhe tecnico fica em log.
    """
