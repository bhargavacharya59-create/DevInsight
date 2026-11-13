"""
Loki log aggregation client.
Queries the Loki HTTP API for logs.
Reports connection status accurately.
"""
from datetime import datetime, UTC
from typing import List, Optional, Dict, Any, Tuple
import logging
import aiohttp
import json

from app.core.config import settings

logger = logging.getLogger("devinsight.loki")


class LokiClient:
    """Async Loki HTTP API client."""

    def __init__(self, url: Optional[str] = None) -> None:
        self.base_url = (url or settings.LOKI_URL).rstrip("/")
        self._connected: Optional[bool] = None
        self._last_error: Optional[str] = None

    async def check_connection(self) -> Tuple[bool, Optional[str]]:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{self.base_url}/ready") as resp:
                    if resp.status == 200:
                        self._connected = True
                        self._last_error = None
                        return True, None
                    err = f"Loki returned HTTP {resp.status}"
                    self._connected = False
                    self._last_error = err
                    return False, err
        except Exception as e:
            err = str(e)
            self._connected = False
            self._last_error = err
            return False, err

    async def query_logs(
        self,
        query: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100,
        direction: str = "backward",
    ) -> Optional[List[Dict[str, Any]]]:
        """Query logs using LogQL."""
        url = f"{self.base_url}/loki/api/v1/query_range"
        params: Dict[str, Any] = {
            "query": query,
            "limit": limit,
            "direction": direction,
        }
        if start:
            params["start"] = int(start.timestamp() * 1e9)  # nanoseconds
        if end:
            params["end"] = int(end.timestamp() * 1e9)

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return self._parse_streams(data)
                    logger.warning("Loki query failed: HTTP %d", resp.status)
                    return None
        except Exception as e:
            logger.error("Loki query error: %s", e)
            return None

    async def get_service_logs(
        self,
        service: str,
        severity: Optional[str] = None,
        minutes_back: int = 60,
        limit: int = 100,
    ) -> Optional[List[Dict[str, Any]]]:
        """Query logs for a specific service."""
        from datetime import timedelta
        end = datetime.now(UTC)
        start = end - timedelta(minutes=minutes_back)

        if severity:
            query = f'{{service="{service}"}} |= `{severity.upper()}`'
        else:
            query = f'{{service="{service}"}}'

        return await self.query_logs(query, start=start, end=end, limit=limit)

    async def get_error_logs(
        self,
        minutes_back: int = 60,
        limit: int = 200,
    ) -> Optional[List[Dict[str, Any]]]:
        """Fetch error-level logs across all services."""
        from datetime import timedelta
        end = datetime.now(UTC)
        start = end - timedelta(minutes=minutes_back)
        query = '{job="shopsphere"} |= "ERROR"'
        return await self.query_logs(query, start=start, end=end, limit=limit)

    @staticmethod
    def _parse_streams(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Loki stream results into flat log entries."""
        entries = []
        streams = data.get("data", {}).get("result", [])
        for stream in streams:
            labels = stream.get("stream", {})
            for ts_ns, line in stream.get("values", []):
                try:
                    ts = datetime.fromtimestamp(int(ts_ns) / 1e9)
                    # Try to parse JSON log line
                    try:
                        parsed = json.loads(line)
                    except json.JSONDecodeError:
                        parsed = {"message": line}

                    entries.append({
                        "timestamp": ts.isoformat() + "Z",
                        "level": parsed.get("level", labels.get("level", "INFO")),
                        "message": parsed.get("message", line),
                        "service": labels.get("service", parsed.get("service", "unknown")),
                        "trace_id": parsed.get("trace_id"),
                        "span_id": parsed.get("span_id"),
                        "request_id": parsed.get("request_id"),
                    })
                except Exception:
                    continue

        return sorted(entries, key=lambda e: e["timestamp"], reverse=True)

    @property
    def connected(self) -> Optional[bool]:
        return self._connected

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error


