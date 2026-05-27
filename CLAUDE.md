# CLAUDE.md — AgroVision AI

> Este arquivo documenta as convenções, padrões e decisões arquiteturais do projeto **AgroVision AI**. Foi construído ao longo da revisão crítica documentada em `docs/relatorio_atividade.md` e serve de guia para futuras sessões de desenvolvimento.

---

## 1. O que é o projeto

Aplicação que une:

- **Visão computacional** (YOLOv8 via `ultralytics`) sobre um stream de vídeo;
- **Persistência** dos eventos detectados em SQLite;
- **Agente de linguagem natural** local (Ollama / llama3) que interpreta os eventos.

O stream e o LLM rodam locais; o projeto é didático. **Não há reconhecimento facial nem identificação pessoal — só classes genéricas (`person`, `car`, `motorcycle`, `truck`, `bus`).**

## 2. Comandos essenciais

```powershell
# Setup
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Subir o servidor (modo dev, sem API key)
python -m uvicorn app:app --reload

# Subir com autenticação ativa
$env:API_KEY = "alguma-chave-secreta"
python -m uvicorn app:app --reload

# Gerar PDF do relatório
python docs/build_pdf.py
```

Pré-requisitos: Python 3.11+, Ollama rodando em `127.0.0.1:11434` com o modelo definido em `OLLAMA_MODEL` (padrão `llama3`).

## 3. Arquitetura: padrões adotados

Trabalhamos sob a combinação **Layered + Hexagonal (Ports & Adapters) + Pipeline**. Esta seção é normativa: **qualquer evolução do projeto deve respeitar estes padrões**.

### 3.1 Camadas

```
PRESENTATION         templates/ + static/
API (transport)      app.py
APPLICATION          VideoMonitor (orquestra pipeline)
                     MonitoringAgent (functional core, puro)
DOMAIN (puro)        services/domain.py
                       Value objects:  Detection, AlertEvent
                       Ports:          Detector, AlertGate, EventStore,
                                       LlmClient, RateLimiter
                       Exceptions:     LlmUnavailableError
INFRASTRUCTURE       vision/      YoloDetector      -> Detector
(adapters)           alerts/      AlertEngine       -> AlertGate
                     persistence/ EventRepository   -> EventStore
                     agent/       OllamaClient      -> LlmClient
                     security/    InMemoryRateLimiter -> RateLimiter
                     external/    (reservado para integrações futuras)
```

### 3.2 Pipeline de visão

O `VideoMonitor._process_frame` é o pipeline; deve permanecer thin:

```python
def _process_frame(self, frame) -> None:
    detections = self.detector.detect(frame)
    annotated  = self.detector.annotate(frame, detections)
    for event in self.alert_gate.submit(detections, annotated):
        self.event_store.save(event)
    with self.last_frame_lock:
        self.last_frame = annotated
```

**Não adicionar lógica aqui.** Cada estágio é responsabilidade do adapter por trás do port.

## 4. Estrutura de pastas

```
agrovision_ia/
├── app.py                         composition root + rotas FastAPI
├── services/
│   ├── domain.py                  value objects, Ports, exceptions de domínio
│   ├── config.py                  AppConfig (frozen dataclass) + load_dotenv
│   ├── video_monitor.py           orquestrador thin do pipeline
│   ├── vision/
│   │   ├── yolo_detector.py       implementa Detector
│   │   └── capture_store.py       helpers de filesystem (JPEGs)
│   ├── alerts/
│   │   └── alert_engine.py        implementa AlertGate
│   ├── persistence/
│   │   └── event_repository.py    implementa EventStore (SQLite)
│   ├── agent/
│   │   ├── monitoring_agent.py    functional core PURO (prompt building)
│   │   ├── ollama_client.py       implementa LlmClient
│   │   └── schemas.py             Pydantic DTOs do chat
│   ├── security/
│   │   ├── auth.py                build_api_key_dependency
│   │   ├── errors.py              mensagens públicas seguras
│   │   ├── headers.py             SecurityHeadersMiddleware
│   │   ├── prompt_safety.py       sanitize_user_prompt + DEFENSIVE_SYSTEM_RULES
│   │   └── rate_limiter.py        InMemoryRateLimiter
│   └── external/                  reservado para integrações futuras
├── templates/index.html
├── static/{dashboard.css, dashboard.js, captures/}
├── docs/
│   ├── relatorio_atividade.md
│   ├── relatorio_atividade.pdf
│   ├── build_pdf.py
│   └── atividade.txt
├── requirements.txt
└── .env / .env.example / .gitignore
```

## 5. Regras invioláveis

### 5.1 Ports vivem em `services/domain.py`

Toda fronteira de infraestrutura tem **port em `domain.py`**, declarado com `@runtime_checkable`, e o composition root (`app.py`) valida cada dependência com `assert isinstance(..., Port)`. Ports atuais: `Detector`, `AlertGate`, `EventStore`, `LlmClient`, `RateLimiter`.

**Ao criar nova integração:**
1. Adicione um `Protocol` em `services/domain.py` com `@runtime_checkable`.
2. Implemente o adapter em `services/<camada>/`.
3. Instancie no `app.py` e injete via construtor.
4. Adicione `assert isinstance(...)` no construtor que recebe a dependência.

### 5.2 `domain.py` é folha

`services/domain.py` **não importa de nenhum outro módulo de `services/`**. Apenas stdlib + `typing`. Manter assim evita import cíclico.

### 5.3 `services/agent/monitoring_agent.py` é functional core PURO

- Sem I/O.
- Sem imports de outros módulos do projeto.
- Políticas de segurança (`sanitize_user_prompt`, `DEFENSIVE_SYSTEM_RULES`) são **injetadas** como parâmetros, não importadas.

```python
def build_agent_messages(
    question, history, events, max_history_messages,
    sanitize_user: Callable[[str], str] = _identity,
    defensive_rules: str | None = None,
) -> list[dict]: ...
```

Quem injeta as políticas concretas é o `app.py`.

### 5.4 SQL vive apenas em `services/persistence/event_repository.py`

Confirmado por grep: nenhum outro arquivo importa `sqlite3` ou executa SQL direto. Toda persistência passa pelo port `EventStore`. **Não inserir SQL fora dessa pasta.**

### 5.5 Contrato HTTP de `/events` é imutável

O JSON em `GET /events` tem as chaves `id, event_time, label, confidence, image_path`. O `dashboard.js` depende disso. **Não renomear, não remover, não trocar tipos.** Se precisar de novos campos, adicione sem mexer nos existentes.

### 5.6 Composition root está no `app.py`

Todas as dependências são instanciadas no `app.py` e injetadas via construtor. **Não usar `import` para resolver dependências dentro dos adapters.** Não criar singletons em outros módulos.

### 5.7 Adapters de infraestrutura não conhecem mensagens públicas

`OllamaClient` levanta `LlmUnavailableError` (domain) quando o upstream falha; **não** importa mensagens de `services/security/errors.py`. A camada de transporte (`app.py`) faz o mapeamento exception → mensagem pública.

Padrão a seguir para novos adapters:
- Adapter levanta exception de domínio (definir em `services/domain.py` se ainda não existir).
- `app.py` captura e responde com mensagem genérica de `services/security/errors.py`.
- Detalhe técnico vai para `logger.exception` ou `logger.error`, nunca para o cliente.

## 6. Padrões de segurança

### 6.1 Autenticação opt-in

- Modo dev: `API_KEY=` vazio no `.env` — rotas operacionais abertas.
- Modo seguro: `API_KEY=<segredo>` — header `X-API-Key` obrigatório nas rotas operacionais. Comparação via `secrets.compare_digest`.
- Rotas SEMPRE públicas: `GET /` (dashboard) e `GET /health`. Tudo o mais é operacional.

### 6.2 Rate limit em `/chat/stream`

Aplicado via `Depends(enforce_chat_rate_limit)`. Configurável por `.env`:
- `CHAT_RATE_LIMIT_PER_MINUTE` (padrão 20)
- `CHAT_RATE_LIMIT_WINDOW_SECONDS` (padrão 60)

Sempre que adicionar endpoint que faça inferência cara (LLM, vision), aplicar rate limit.

### 6.3 Cabeçalhos HTTP

`SecurityHeadersMiddleware` adiciona em toda resposta: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`. Não remover.

### 6.4 Input do usuário no LLM

Toda string vinda do cliente que chega no LLM deve passar por `sanitize_user_prompt` (`services/security/prompt_safety.py`). O `DEFENSIVE_SYSTEM_RULES` deve estar no array de mensagens antes do `user`.

### 6.5 Tratamento de erro

- Cliente recebe apenas mensagens fixas de `services/security/errors.py`.
- Servidor loga o detalhe completo via `logger.exception` (com traceback) ou `logger.error`.
- **Nunca** `yield f"\n[ERRO] {error}"` ou similar.

## 7. Configuração

- Variáveis carregadas via `python-dotenv` em `services/config.py`.
- `AppConfig` é `@dataclass(frozen=True)` — imutável.
- Toda nova flag de comportamento configurável deve ser:
  1. Campo em `AppConfig`.
  2. Carregado em `load_config()` com `os.getenv("NAME", "<default>")` e conversão de tipo.
  3. Documentado no `.env.example` com comentário explicativo.
  4. Documentado no `.env` real (não commitado).

## 8. Logging

```python
import logging
logger = logging.getLogger(__name__)
```

Não usar `print` para diagnóstico. `logger.basicConfig` já é configurado no `app.py` no boot.

## 9. Padrões anti — o que NÃO fazer

| Anti-pattern | Por quê |
|---|---|
| Importar de outro adapter (e.g. `agent/` importando de `security/`) | Cria acoplamento cruzado entre camadas de infraestrutura. Use ports e injeção. |
| Adicionar lógica em `app.py` além de roteamento e composition | Quebra "thin controllers". Mova para um serviço da camada apropriada. |
| SQL fora de `services/persistence/` | Quebra isolamento da camada de dados. |
| `print()` para diagnóstico | Use `logger`. |
| Mensagem de erro técnica chegando ao cliente | Vaza informação. Mensagem fixa de `services/security/errors.py`. |
| Argumentos posicionais soltos para dados de domínio | Use o value object (`AlertEvent`, etc.). |
| Singleton em escopo de módulo (`X = X()` no topo de um arquivo de serviço) | Quebra composition root. Instancie no `app.py`. |
| Esconder erros silenciosamente (`except Exception: pass`) | Logue com `logger.exception` antes de seguir. |
| Configuração hardcoded no código | Vá para `.env` + `AppConfig`. |
| Endpoint novo sem `dependencies=[Depends(require_api_key)]` quando for operacional | Quebra o gate opt-in da Seção 6.1. |

## 10. Convenções de código

- Type hints em assinaturas públicas.
- Dataclasses imutáveis (`frozen=True`) para value objects.
- `Protocol` com `@runtime_checkable` para ports.
- Sem comentários redundantes; o nome da função/classe deve carregar a intenção.
- Comentário só quando o **porquê** não é óbvio do código (constraint escondida, workaround específico).
- Português do Brasil em docstrings e comentários (consistente com o resto do projeto e com o agente).

## 11. Padrões de teste

Não há suíte de testes automatizada hoje. A validação é manual:

- `python -c "import app"` — checa import graph e isinstance dos Protocols.
- `python -m uvicorn app:app` + `curl` nas rotas-chave.
- Para mudanças no agente, perguntar no chat e validar a resposta.

Se for adicionar pytest, isolar testes por camada respeitando as fronteiras dos ports — mockar via classes que implementam o Protocol, não classes concretas.

## 12. Onde mexer ao evoluir

| Necessidade | Onde |
|---|---|
| Trocar modelo YOLO | `MODEL_PATH` no `.env`, ou novo adapter em `services/vision/` |
| Trocar LLM provider | Novo adapter em `services/agent/` cumprindo `LlmClient`; instanciar no `app.py` |
| Trocar banco | Novo adapter em `services/persistence/` cumprindo `EventStore` |
| Adicionar integração externa (scraping, weather API, etc.) | Adapter em `services/external/`, novo port em `domain.py`, instância no `app.py` |
| Ajustar comportamento do agente | `services/agent/monitoring_agent.py` (mantenha puro) |
| Endurecer segurança | `services/security/` |
| Adicionar nova rota | `app.py`, aplicando `require_api_key` se for operacional |

## 13. Estado das partes da atividade

- **Parte 1 (arquitetura):** concluída. Documentada em `docs/relatorio_atividade.md` §1.
- **Parte 2 (segurança):** concluída. Documentada em §2, incluindo reconciliação arquitetural em §2.9.
- **Parte 3 (refator de IA):** concluída. Documentada em §3 (4 trechos).
- **Parte 4 (web scraping):** **pendente, atribuída a outro membro do grupo.** O subpacote `services/external/` está reservado e o padrão Hexagonal exige: novo `Protocol` em `domain.py`, adapter em `external/`, injeção no `app.py`. Não embutir `requests`/`BeautifulSoup` em rotas ou templates.

## 14. Fonte canônica

Em caso de dúvida sobre uma decisão de design, consultar `docs/relatorio_atividade.md` — toda decisão registrada tem justificativa. Em caso de conflito entre este `CLAUDE.md` e o código atual: o código é a verdade; abra issue antes de mudar.
