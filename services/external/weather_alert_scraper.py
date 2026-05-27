"""Scraper de alertas climaticos do INMET (RSS publico).

Adapter que implementa o port `services.domain.WeatherAlertSource`.
"""

from __future__ import annotations

import html
import logging
import re
import threading
import time
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from services.domain import WeatherAlertSource


logger = logging.getLogger(__name__)


class InmetWeatherAlertScraper(WeatherAlertSource):
    """Busca alertas climaticos do RSS publico do INMET com cache e rate limit."""

    def __init__(
        self,
        feed_url: str,
        min_interval_seconds: int,
        max_items: int,
        timeout_seconds: int = 10,
    ) -> None:
        self._feed_url = feed_url
        self._min_interval_seconds = max(60, int(min_interval_seconds))
        self._max_items = max(1, int(max_items))
        self._timeout_seconds = max(3, int(timeout_seconds))
        self._lock = threading.Lock()
        self._last_fetch_ts = 0.0
        self._cached: dict | None = None

    def fetch_alerts(self) -> dict:
        now = time.time()
        with self._lock:
            if self._cached and (now - self._last_fetch_ts) < self._min_interval_seconds:
                return self._cached

        try:
            payload = self._refresh()
        except Exception:
            logger.exception("Falha ao buscar alertas climaticos do INMET")
            fallback = self._fallback_payload()
            with self._lock:
                self._cached = fallback
                self._last_fetch_ts = now
            return fallback

        with self._lock:
            self._cached = payload
            self._last_fetch_ts = now
        return payload

    def _refresh(self) -> dict:
        request = urllib.request.Request(
            self._feed_url,
            headers={"User-Agent": "AgroVisionAI/1.0 (+https://github.com)"},
        )
        with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
            data = response.read()

        alerts = self._parse_rss(data)
        now = datetime.now(timezone.utc).isoformat()
        return {
            "source": "INMET RSS",
            "url": self._feed_url,
            "fetched_at": now,
            "status": "ok",
            "alerts": alerts,
        }

    def _fallback_payload(self) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        if self._cached:
            stale = dict(self._cached)
            stale["status"] = "stale"
            stale["error"] = "Fonte indisponivel no momento. Usando cache recente."
            stale["fetched_at"] = now
            return stale
        return {
            "source": "INMET RSS",
            "url": self._feed_url,
            "fetched_at": now,
            "status": "error",
            "alerts": [],
            "error": "Fonte indisponivel no momento.",
        }

    def _parse_rss(self, data: bytes) -> list[dict]:
        root = ET.fromstring(data)
        channel = root.find("channel")
        if channel is None:
            return []

        alerts: list[dict] = []
        for item in channel.findall("item")[: self._max_items]:
            title = _text(item.find("title"))
            link = _text(item.find("link"))
            pub_date = _text(item.find("pubDate"))
            description_html = _text(item.find("description"))
            details = _parse_description_table(description_html)
            alerts.append(
                {
                    "title": title,
                    "link": link,
                    "pub_date": pub_date,
                    "event": details.get("event", ""),
                    "severity": details.get("severity", ""),
                    "start": details.get("start", ""),
                    "end": details.get("end", ""),
                    "description": details.get("description", ""),
                    "area": details.get("area", ""),
                    "status": details.get("status", ""),
                    "graphic_link": details.get("graphic_link", ""),
                }
            )
        return alerts


def _text(node: ET.Element | None) -> str:
    if node is None or node.text is None:
        return ""
    return node.text.strip()


def _normalize_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_value.lower().strip()


def _strip_html(value: str) -> str:
    unescaped = html.unescape(value)
    return re.sub(r"<[^>]+>", "", unescaped).replace("\xa0", " ").strip()


def _parse_description_table(description_html: str) -> dict[str, str]:
    if not description_html:
        return {}

    cleaned = description_html.replace("\n", " ")
    pairs = re.findall(r"<tr>\s*<th[^>]*>(.*?)</th>\s*<td>(.*?)</td>\s*</tr>", cleaned, re.I)
    mapping = {
        "evento": "event",
        "severidade": "severity",
        "inicio": "start",
        "fim": "end",
        "descricao": "description",
        "area": "area",
        "status": "status",
        "link grafico": "graphic_link",
    }

    data: dict[str, str] = {}
    for raw_key, raw_value in pairs:
        key = _normalize_key(_strip_html(raw_key))
        value = _strip_html(raw_value)
        if key in mapping:
            data[mapping[key]] = value
    return data
