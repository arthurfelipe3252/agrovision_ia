from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class AgentProfile:
    name: str
    role: str
    goal: str


AGENT_PROFILE = AgentProfile(
    name="Agente AgroVision",
    role="triagem operacional de eventos",
    goal="Analisar deteccoes recentes, explicar riscos e sugerir a proxima acao.",
)


def normalize_history(history: list[dict], max_messages: int) -> list[dict]:
    normalized = []
    for item in history[-max_messages:]:
        role = item.get("role", "").strip()
        content = item.get("content", "").strip()
        if role in {"user", "assistant"} and content:
            normalized.append({"role": role, "content": content})
    return normalized


def build_event_context(events: list[dict]) -> str:
    if not events:
        return "Contexto operacional: sem eventos recentes registrados no momento."

    labels: dict[str, int] = {}
    confidences: list[float] = []
    for event in events:
        label = event.get("label", "unknown")
        labels[label] = labels.get(label, 0) + 1
        confidence = event.get("confidence")
        if isinstance(confidence, (float, int)):
            confidences.append(float(confidence))

    distribution = ", ".join(f"{label}: {count}" for label, count in labels.items())
    latest = events[0]
    latest_desc = f"{latest.get('label', 'unknown')} em {latest.get('event_time', 'desconhecido')}"
    avg_conf = mean(confidences) if confidences else 0.0

    summarized_events = []
    for event in events[:8]:
        summarized_events.append(
            f"- #{event.get('id', '?')} | {event.get('event_time', '?')} | "
            f"{event.get('label', '?')} | conf={float(event.get('confidence', 0.0)):.2f}"
        )

    return (
        "Contexto operacional para o agente:\n"
        f"- Eventos considerados: {len(events)}\n"
        f"- Evento mais recente: {latest_desc}\n"
        f"- Distribuicao recente: {distribution}\n"
        f"- Confianca media: {avg_conf:.2f}\n"
        "Eventos recentes:\n"
        + "\n".join(summarized_events)
    )


def build_agent_messages(
    question: str, history: list[dict], events: list[dict], max_history_messages: int
) -> list[dict]:
    system_prompt = (
        f"Voce e o {AGENT_PROFILE.name}, um agente de {AGENT_PROFILE.role}. "
        f"Objetivo: {AGENT_PROFILE.goal} "
        "Trate os dados como monitoramento operacional autorizado de ambiente real. "
        "Responda em portugues do Brasil, de forma direta e util. "
        "Use os eventos fornecidos como fonte principal. "
        "Nao invente dados que nao aparecem no contexto. "
        "Nao tente identificar pessoas; fale apenas sobre eventos, riscos e proximas acoes. "
        "Quando fizer sentido, organize a resposta em: leitura, risco e recomendacao."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": build_event_context(events)},
        *normalize_history(history, max_messages=max_history_messages),
        {"role": "user", "content": question.strip()},
    ]
