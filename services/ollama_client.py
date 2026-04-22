import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout: int, keep_alive: str):
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.keep_alive = keep_alive

    def _build_request(self, messages: list[dict], stream: bool) -> Request:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "keep_alive": self.keep_alive,
        }
        body = json.dumps(payload).encode("utf-8")
        return Request(
            self.base_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

    def chat(self, messages: list[dict]) -> str:
        request = self._build_request(messages, stream=False)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw_response = response.read().decode("utf-8")
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Ollama HTTP {error.code}: {detail}") from error
        except URLError as error:
            raise RuntimeError(f"Falha ao conectar no Ollama: {error.reason}") from error

        parsed = json.loads(raw_response)
        message = parsed.get("message", {})
        content = message.get("content", "").strip()
        if not content:
            return "Sem resposta do modelo."
        return content

    def chat_stream(self, messages: list[dict]):
        request = self._build_request(messages, stream=True)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                for raw_line in response:
                    decoded = raw_line.decode("utf-8").strip()
                    if not decoded:
                        continue
                    chunk = json.loads(decoded)
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if chunk.get("done"):
                        break
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Ollama HTTP {error.code}: {detail}") from error
        except URLError as error:
            raise RuntimeError(f"Falha ao conectar no Ollama: {error.reason}") from error

    def warmup(self) -> bool:
        try:
            _ = self.chat([{"role": "user", "content": "ping"}])
            return True
        except Exception:
            return False
