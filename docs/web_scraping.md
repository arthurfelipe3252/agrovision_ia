# Camada de Web Scraping — Alertas Climaticos (INMET)

## 1. Objetivo e relevancia
O AgroVision AI monitora pessoas e veiculos em tempo real. Alertas climaticos (chuva intensa, tempestade, geada, baixa umidade) aumentam o risco operacional e ajudam o agente a priorizar recomendacoes. Por isso, a camada de scraping foi criada para **enriquecer o contexto** do sistema com dados publicos do INMET.

## 2. O que a camada faz
- Consulta o **RSS publico de avisos do INMET**.
- Extrai campos relevantes de cada alerta (evento, severidade, area, inicio/fim).
- Normaliza os dados em **JSON estruturado**.
- Aplica **cache + rate limit** para evitar excesso de requisicoes.
- Trata falhas de rede e devolve um payload com status `stale` ou `error`.

## 3. Fonte publica utilizada
- **INMET RSS (avisos):** https://apiprevmet3.inmet.gov.br/avisos/rss
- Licenca informada no proprio RSS como conteudo publico.

## 4. Como funciona (visao tecnica)
### 4.1 Port e adapter
- Port definido em `services/domain.py`: `WeatherAlertSource`.
- Adapter implementado em `services/external/weather_alert_scraper.py`: `InmetWeatherAlertScraper`.

### 4.2 Fluxo de dados
1. O adapter faz download do RSS.
2. O XML e parseado.
3. O campo `description` (HTML) e convertido para texto.
4. Os dados sao organizados em um dict com `alerts`.
5. O payload e retornado para a API.

### 4.3 Rate limit e cache
- O adapter guarda o ultimo resultado em memoria.
- Se a chamada ocorre antes do intervalo minimo (`WEATHER_ALERTS_MIN_INTERVAL_SECONDS`), devolve o cache.

### 4.4 Tratamento de erro
- Falhas de rede ou parsing geram log e retorno com `status: "error"`.
- Se houver cache valido, o retorno vira `status: "stale"` com ultima leitura conhecida.

## 5. Formato do JSON
Exemplo simplificado:

```json
{
  "source": "INMET RSS",
  "url": "https://apiprevmet3.inmet.gov.br/avisos/rss",
  "fetched_at": "2026-05-27T13:10:41+00:00",
  "status": "ok",
  "alerts": [
    {
      "title": "Aviso de Tempestade. Severidade Grau: Perigo Potencial",
      "link": "https://apiprevmet3.inmet.gov.br/avisos/rss/54504",
      "pub_date": "Wed, 27 May 2026 12:00:00 +0000",
      "event": "Tempestade",
      "severity": "Perigo Potencial",
      "start": "2026-05-27 12:00:00.0",
      "end": "2026-05-27 21:00:00.0",
      "description": "Chuva entre 20 e 30 mm/h...",
      "area": "Metropolitana de Sao Paulo, ...",
      "status": "Alert",
      "graphic_link": "https://avisos.inmet.gov.br/54504"
    }
  ]
}
```

## 6. Integracao com o sistema
- **API:** endpoint protegido `GET /weather/alerts`.
- **Dashboard:** card “Alertas Climaticos (INMET)” renderiza os itens.
- **Agente:** o contexto climatico e injetado no prompt (system message) para enriquecer respostas.

## 7. Configuracao via .env
```env
WEATHER_ALERTS_URL=https://apiprevmet3.inmet.gov.br/avisos/rss
WEATHER_ALERTS_MIN_INTERVAL_SECONDS=900
WEATHER_ALERTS_MAX_ITEMS=8
```

## 8. Por que isso melhora o AgroVision
- **Contexto de risco:** clima adverso aumenta risco quando ha pessoas/veiculos.
- **Recomendacoes melhores:** o agente pode sugerir cuidados em caso de chuva forte ou tempestade.
- **Relevancia operacional:** alertas oficiais sao sinal confiavel para monitoramento.

## 9. Limites e cuidados
- O RSS e uma fonte externa e pode ficar fora do ar.
- O adapter evita excesso de requisicoes e sempre retorna um payload seguro.
- O sistema nao depende do scraping para funcionar, apenas enriquece o contexto.
