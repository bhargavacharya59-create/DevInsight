"""
OpenTelemetry / Tempo trace client.
Queries Tempo (or a generic OTLP-compatible backend) for traces.
"""
from datetime import datetime, UTC, timedelta
from typing import List, Optional, Dict, Any, Tuple
import logging
import aiohttp

from app.core.config import settings

logger = logging.getLogger("devinsight.otel")


class OTelClient:
    """Client for querying traces from Tempo or a compatible backend."""

    def __init__(self, url: Optional[str] = None) -> None:
        # Tempo's HTTP API (compatible with Jaeger query)
        self.base_url = (url or settings.OTEL_COLLECTOR_URL).rstrip("/")
        self._connected: Optional[bool] = None
        self._last_error: Optional[str] = None

    async def check_connection(self) -> Tuple[bool, Optional[str]]:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                # Tempo readiness endpoint
                async with session.get(f"{self.base_url}/ready") as resp:
                    if resp.status in (200, 204):
                        self._connected = True
                        self._last_error = None
                        return True, None
                    err = f"OTel backend returned HTTP {resp.status}"
                    self._connected = False
                    self._last_error = err
                    return False, err
        except Exception as e:
            err = str(e)
            self._connected = False
            self._last_error = err
            return False, err

    async def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific trace by ID."""
        url = f"{self.base_url}/api/traces/{trace_id}"
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return None
        except Exception as e:
            logger.error("Trace fetch error: %s", e)
            return None

    async def search_traces(
        self,
        service: Optional[str] = None,
        operation: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        min_duration_ms: Optional[float] = None,
        limit: int = 20,
        minutes_back: int = 60,
    ) -> Optional[List[Dict[str, Any]]]:
        """Search for traces matching criteria."""
        url = f"{self.base_url}/api/search"
        end = datetime.now(UTC)
        start = end - timedelta(minutes=minutes_back)

        params: Dict[str, Any] = {
            "limit": limit,
            "start": int(start.timestamp()),
            "end": int(end.timestamp()),
        }
        if service:
            params["service.name"] = service
        if operation:
            params["name"] = operation
        if min_duration_ms:
            params["minDuration"] = f"{int(min_duration_ms)}ms"

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("traces", [])
                    return None
        except Exception as e:
            logger.error("Trace search error: %s", e)
            return None

    @property
    def connected(self) -> Optional[bool]:
        return self._connected

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error


