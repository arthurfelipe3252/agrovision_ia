"""Rate limiter in-memory por IP usando janela deslizante.

Sem dependências externas, sem Redis. Adequado a deployments single-process.
Para multi-worker/multi-host seria preciso storage compartilhado, mas o
escopo deste projeto (didático, single instance) torna isso suficiente.
"""

import threading
import time
from collections import defaultdict, deque
from typing import Deque, DefaultDict


class InMemoryRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        if max_requests <= 0:
            raise ValueError("max_requests deve ser positivo")
        if window_seconds <= 0:
            raise ValueError("window_seconds deve ser positivo")
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._hits: DefaultDict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, identity: str) -> bool:
        """Retorna True se a requisição cabe na janela; False se foi excedida."""
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[identity]
            cutoff = now - self._window_seconds
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self._max_requests:
                return False
            bucket.append(now)
            return True
