"""Autenticação opcional por API key.

Comportamento:

- Se `expected_api_key` for vazia, o dependency permite tudo (modo dev).
- Se estiver definida, o cliente deve enviar o header `X-API-Key`
  com o mesmo valor; caso contrário, a rota retorna 401.

A comparação usa `secrets.compare_digest` para evitar leaks por
timing analysis em chaves curtas.
"""

import secrets
from typing import Callable

from fastapi import Header, HTTPException, status


def build_api_key_dependency(expected_api_key: str) -> Callable:
    expected = expected_api_key.strip()

    async def require_api_key(
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ) -> None:
        if not expected:
            return
        provided = (x_api_key or "").strip()
        if not provided or not secrets.compare_digest(provided, expected):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais ausentes ou invalidas.",
            )

    return require_api_key
