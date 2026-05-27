"""Mensagens publicas seguras para resposta ao cliente.

Detalhes tecnicos das excecoes nunca devem chegar ao browser. Estas
constantes sao usadas pelo `app.py` e pelos clientes externos quando
algo falha. O log completo da excecao continua disponivel em stderr
do servidor.
"""

GENERIC_AGENT_ERROR = (
    "Falha temporaria ao gerar resposta. Tente novamente em alguns instantes."
)

GENERIC_UPSTREAM_ERROR = (
    "Servico interno indisponivel no momento."
)

GENERIC_RATE_LIMIT_MESSAGE = (
    "Muitas requisicoes em sequencia. Aguarde alguns segundos antes de tentar novamente."
)
