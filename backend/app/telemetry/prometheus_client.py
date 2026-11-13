"""
Prometheus telemetry client.
Queries the Prometheus HTTP API for metrics.
Reports connection status accurately — does NOT pretend to be connected if not.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
import aiohttp

from app.core.config import settings

logger = logging.getLogger("devinsight.prometheus")


class PrometheusClient:
    """Async Prometheus HTTP API client."""

    def __init__(self, url: Optional[str] = None) -> None:
        self.base_url = (url or settings.PROMETHEUS_URL).rstrip("/")
        self._connected: Optional[bool] = None
        self._last_error: Optional[str] = None

    async def check_connection(self) -> Tuple[bool, Optional[str]]:
        """Check if Prometheus is reachable."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{self.base_url}/-/ready") as resp:
                    if resp.status == 200:
                        self._connected = True
                        self._last_error = None
                        return True, None
                    else:
                        err = f"Prometheus returned HTTP {resp.status}"
                        self._connected = False
                        self._last_error = err
                        return False, err
        except Exception as e:
            err = str(e)
            self._connected = False
            self._last_error = err
            return False, err

    async def query_instant(self, promql: str) -> Optional[Dict[str, Any]]:
        """Execute a PromQL instant query."""
        url = f"{self.base_url}/api/v1/query"
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url, params={"query": promql}) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("data", {})
                    logger.warning("Prometheus query failed: HTTP %d", resp.status)
                    return None
        except Exception as e:
            logger.error("Prometheus instant query error: %s", e)
            return None

    async def query_range(
        self,
        promql: str,
        start: datetime,
        end: datetime,
        step: str = "60s",
    ) -> Optional[List[Dict[str, Any]]]:
        """Execute a PromQL range query."""
        url = f"{self.base_url}/api/v1/query_range"
        params = {
            "query": promql,
            "start": start.timestamp(),
            "end": end.timestamp(),
            "step": step,
        }
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("data", {}).get("result", [])
                    return None
        except Exception as e:
            logger.error("Prometheus range query error: %s", e)
            return None

    async def get_request_rate(self, service: str = "shopsphere") -> Optional[float]:
        result = await self.query_instant(
            f'sum(rate(http_requests_total{{job="{service}"}}[5m]))'
        )
        return self._extract_scalar(result)

    async def get_error_rate(self, service: str = "shopsphere") -> Optional[float]:
        result = await self.query_instant(
            f'sum(rate(http_requests_total{{job="{service}",status=~"5.."}}[5m])) / '
            f'sum(rate(http_requests_total{{job="{service}"}}[5m])) * 100'
        )
        return self._extract_scalar(result)

    async def get_latency_p95(self, service: str = "shopsphere") -> Optional[float]:
        result = await self.query_instant(
            f'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{job="{service}"}}[5m])) by (le)) * 1000'
        )
        return self._extract_scalar(result)

    async def get_cpu_utilization(self) -> Optional[float]:
        result = await self.query_instant(
            '100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
        )
        return self._extract_scalar(result)

    async def get_memory_utilization(self) -> Optional[float]:
        result = await self.query_instant(
            '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100'
        )
        return self._extract_scalar(result)

    @staticmethod
    def _extract_scalar(data: Optional[Dict]) -> Optional[float]:
        if not data:
            return None
        result_list = data.get("result", [])
        if result_list:
            try:
                return float(result_list[0]["value"][1])
            except (KeyError, IndexError, ValueError):
                return None
        return None

    @property
    def connected(self) -> Optional[bool]:
        return self._connected

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error
