# AgroVision AI

Documentação principal da atividade: evolução do projeto para monitoramento de tráfego com YOLO + chat com Ollama + agente de IA em Python.

## 1) O que o sistema faz hoje

O AgroVision AI monitora uma fonte de vídeo, detecta objetos relevantes e registra eventos para análise.

Fluxo atual:
- Fonte de vídeo (webcam/stream autorizado)
- Backend FastAPI abre o stream com OpenCV
- YOLO analisa os frames
- Eventos são salvos no SQLite
- Dashboard exibe feed e histórico de eventos

## 2) Por que estamos fazendo isso

Esta evolução consolida, em um único projeto:
- visão computacional (YOLO),
- backend (FastAPI),
- persistência (SQLite),
- IA local (Ollama),
- e arquitetura por serviços (agente + orquestração).

Objetivo didático: mostrar como um sistema evolui por camadas, de detecção visual até interpretação em linguagem natural.

## 3) Versões usadas no projeto

Ambiente sugerido para aula/laboratório:
- Python: 3.10+ (recomendado 3.11)
- Ollama: instalado e ativo em `http://127.0.0.1:11434`
- Modelo LLM padrão: `llama3`
- Modelo de visão padrão: `yolov8n.pt`

Dependências estão em `requirements.txt`.

## 4) Componentes do sistema

- **Câmera**: fonte de vídeo local ou pública/autorizada.
- **OpenCV**: captura frames e alimenta o pipeline.
- **YOLO**: detecta objetos e retorna label/confiança.
- **SQLite**: guarda eventos detectados.
- **Dashboard**: mostra feed e eventos.
- **Ollama**: gera respostas em linguagem natural.
- **Agente**: organiza contexto, regras e objetivo para o modelo.

## 5) Diferença entre YOLO, Ollama e agente

- **YOLO**: predição visual (objeto + confiança).
- **Ollama**: execução local do modelo de linguagem.
- **Agente**: camada Python que define papel, regras, contexto e memória curta para orientar o LLM.

Resumo curto:
- YOLO detecta.
- Ollama escreve.
- Agente orienta como escrever com base nos eventos.

## 6) Arquitetura atual de arquivos

Estrutura principal implementada:
- `app.py`
- `services/config.py`
- `services/schemas.py`
- `services/event_repository.py`
- `services/capture_store.py`
- `services/video_monitor.py`
- `services/ollama_client.py`
- `services/monitoring_agent.py`
- `templates/index.html`
- `static/dashboard.css`
- `static/dashboard.js`

## 7) Instalação do Ollama

Windows:
1. Baixar em [ollama.com/download](https://ollama.com/download)
2. Verificar instalação:
   - `ollama --version`

Linux/macOS:
- `curl -fsSL https://ollama.com/install.sh | sh`
- `ollama --version`

Baixar modelo padrão:
- `ollama pull llama3`
- `ollama list`

## 8) Configuração do `.env`

Exemplo de uso local:

```env
APP_TITLE=AgroVision AI

CAMERA_SOURCE=https://wzmedia.dot.ca.gov/D11/C214_SB_5_at_Via_De_San_Ysidro.stream/playlist.m3u8
CAMERA_RECONNECT_SECONDS=5
MODEL_PATH=yolov8n.pt
CONFIDENCE_THRESHOLD=0.45
TARGET_CLASSES=person,car,motorcycle,truck,bus
MIN_CONSECUTIVE_FRAMES=3
ALERT_COOLDOWN_SECONDS=20
SAVE_DIR=static/captures
DB_PATH=detections.db

OLLAMA_URL=http://127.0.0.1:11434/api/chat
OLLAMA_MODEL=llama3
OLLAMA_TIMEOUT=120
OLLAMA_KEEP_ALIVE=30m
AGENT_EVENT_LIMIT=12
MAX_HISTORY_MESSAGES=8
```

Observação: não versionar `.env` com credenciais, chaves ou fontes privadas.

## 9) Passo a passo para rodar o projeto

1. Criar e ativar ambiente virtual:
   - `python -m venv .venv`
   - `.\.venv\Scripts\Activate.ps1`
2. Instalar dependências:
   - `pip install -r requirements.txt`
3. Criar `.env` local a partir do template:
   - `copy .env.example .env` (Windows)
4. Garantir Ollama ativo e modelo baixado:
   - `ollama list`
5. Subir a API:
   - `python -m uvicorn app:app --reload`
6. Abrir o dashboard:
   - `http://127.0.0.1:8000`

## 10) Como validar a câmera

Rotas úteis:
- `GET /camera/status`
- `GET /frame`
- `GET /video_feed`

## 11) Como validar o YOLO

- `GET /events`
- Esperado: eventos com `event_time`, `label`, `confidence` e `image_path`.

## 12) Como validar o agente

- Painel web (chat)
- `GET /agent/status`
- `POST /chat/stream` (resposta incremental token a token)

Pergunta de teste:
- "Leia os eventos recentes, avalie o risco e recomende a próxima ação."

## 13) O que acontece quando o usuário pergunta no chat

Fluxo esperado:
1. Front envia pergunta ao backend.
2. Backend busca eventos recentes.
3. Agente monta contexto operacional.
4. Ollama gera resposta textual em streaming.
5. Painel renderiza a resposta.

## 14) O que o agente não faz

O agente:
- não substitui o YOLO,
- não reconhece identidade de pessoas,
- não acessa câmera por conta própria,
- não executa automações externas (nesta etapa).

Ele interpreta eventos já detectados e sugere próxima ação.

## 15) Aprendizados desta evolução

- Separação de responsabilidades melhora manutenção.
- IA visual e IA de linguagem têm papéis diferentes.
- Agente é arquitetura de uso do modelo, não "modelo novo".
- Observabilidade por rotas reduz tempo de diagnóstico.

## 16) Roteiro sugerido de aula

1. Base do projeto (FastAPI + YOLO + SQLite)
2. Ollama local
3. Camada de agente
4. Câmera pública/autorizada
5. Pipeline completo e próximos passos

## 17) Perguntas boas para testar o agente

- "O que foi detectado nos últimos eventos?"
- "Existe padrão no monitoramento atual?"
- "Qual o risco operacional agora?"
- "Qual próxima ação recomendada?"

## 18) Problemas comuns

- **Ollama não responde**: validar `http://127.0.0.1:11434/api/tags` e usar `ollama serve`.
- **Modelo ausente**: `ollama pull llama3`.
- **Sem eventos**: verificar fonte da câmera e conexão.
- **Resposta genérica**: conferir se há eventos recentes no contexto.
- **`/video_feed` não abre**: testar antes se `/camera/status` indica `online=true` e `has_live_frame=true`.

## 19) Cuidados éticos e legais

Uso recomendado:
- apenas câmeras públicas oficiais ou privadas autorizadas,
- finalidade didática/operacional legítima,
- sem reconhecimento facial,
- sem tentativa de identificação pessoal.

## 20) Onde mexer para evoluir

- Fonte de vídeo: `.env` (`CAMERA_SOURCE`)
- Modelo LLM: `.env` (`OLLAMA_MODEL`)
- Comportamento do agente: `services/monitoring_agent.py`
- Classes detectadas: configuração central em `services/config.py` (`TARGET_CLASSES`)

## Checklist rápido de entrega

- API sobe com `python -m uvicorn app:app --reload`.
- `GET /health` retorna status `ok`.
- `GET /camera/status` indica conexão de câmera ativa.
- `GET /events` retorna lista de eventos (mesmo vazia no início).
- `GET /agent/status` retorna perfil e contexto do agente.
- Dashboard abre em `http://127.0.0.1:8000` e envia perguntas no chat.

## 21) Resumo final

Este projeto conecta visão computacional e IA generativa local em um fluxo único:
- vídeo vira detecção,
- detecção vira histórico,
- histórico vira interpretação operacional.

Mensagem principal:
o agente não é só o modelo.  
É o modelo + contexto + regras + organização da aplicação.