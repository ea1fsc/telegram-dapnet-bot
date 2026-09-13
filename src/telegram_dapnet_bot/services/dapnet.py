from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

import httpx

from telegram_dapnet_bot.services.radioid import process_dmr_id
from telegram_dapnet_bot.services.txgroups import SERVER_DE, filter_tx_groups, parse_tx_groups

logger = logging.getLogger(__name__)


class DapnetError(Exception):
    pass


@dataclass(frozen=True)
class SubscriberCheck:
    exists_user: bool
    exists_callsign: bool
    pager_count: int | None
    pagers_visible: bool

    @property
    def ok(self) -> bool:
        if not self.exists_user or not self.exists_callsign:
            return False
        if self.pagers_visible:
            return (self.pager_count or 0) >= 1
        return True


class DapnetClient:
    def __init__(
        self,
        urls: dict[str, str] | str,
        callsign: str,
        password: str,
        *,
        timeout: float = 20.0,
        default_server: str = SERVER_DE,
    ) -> None:
        if isinstance(urls, str):
            urls = {default_server: urls}
        self._urls = {key: value.rstrip("/") for key, value in urls.items() if value}
        self._default_server = default_server
        self._auth = (callsign, password)
        self._timeout = timeout

    def url_for(self, server: str | None = None) -> str:
        key = server or self._default_server
        return self._urls.get(key) or self._urls[self._default_server]

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        retries: int = 3,
        server: str | None = None,
    ) -> httpx.Response:
        url = f"{self.url_for(server)}{path}"
        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in range(retries):
                try:
                    response = await client.request(
                        method, url, auth=self._auth, json=json
                    )
                except httpx.HTTPError as exc:
                    last_error = exc
                    logger.warning("DAPNET request failed (%s): %s", url, exc)
                    continue
                if response.status_code in {429, 500, 502, 503, 504} and attempt + 1 < retries:
                    continue
                return response
        raise DapnetError(f"DAPNET request failed: {last_error}")

    async def get_user(self, callsign: str) -> dict[str, Any] | None:
        response = await self._request("GET", f"/users/{callsign}")
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise DapnetError(f"DAPNET /users returned HTTP {response.status_code}")
        return response.json()

    async def get_callsign(self, callsign: str) -> dict[str, Any] | None:
        for path in (f"/callSigns/{callsign}", f"/callsigns/{callsign}"):
            response = await self._request("GET", path)
            if response.status_code == 404:
                continue
            if response.status_code >= 400:
                raise DapnetError(f"DAPNET {path} returned HTTP {response.status_code}")
            return response.json()
        return None

    async def check_subscriber(self, callsign: str) -> SubscriberCheck:
        user = await self.get_user(callsign)
        record = await self.get_callsign(callsign)
        pagers = None
        visible = False
        if isinstance(record, dict) and "pagers" in record:
            visible = True
            pagers_raw = record.get("pagers") or []
            pagers = len(pagers_raw) if isinstance(pagers_raw, list) else 0
        return SubscriberCheck(
            exists_user=user is not None,
            exists_callsign=record is not None,
            pager_count=pagers,
            pagers_visible=visible,
        )

    def pager_rics(self, record: dict[str, Any] | None) -> list[int]:
        return parse_pager_rics(record)

    async def list_transmitter_groups(self, server: str | None = None) -> list[str]:
        names: list[str] = []
        for path in ("/transmitterGroups", "/transmittergroups"):
            response = await self._request("GET", path, server=server)
            if response.status_code == 404:
                continue
            if response.status_code >= 400:
                logger.warning(
                    "DAPNET %s returned HTTP %s", path, response.status_code
                )
                continue
            payload = response.json()
            rows = payload if isinstance(payload, list) else []
            for row in rows:
                if isinstance(row, str):
                    names.append(row)
                elif isinstance(row, dict):
                    name = row.get("name") or row.get("transmitterGroupName")
                    if name:
                        names.append(str(name))
            if names:
                break
        return filter_tx_groups(names)

    async def send_call(
        self,
        text: str,
        recipients: str | list[str],
        transmitter_groups: str | list[str],
        *,
        server: str | None = None,
        emergency: bool = False,
    ) -> dict[str, Any]:
        if isinstance(recipients, str):
            names = [recipients.strip().lower()] if recipients.strip() else []
        else:
            names = [name.strip().lower() for name in recipients if name and name.strip()]
        if not names:
            raise DapnetError("No DAPNET destinations were selected")
        groups = parse_tx_groups(transmitter_groups)
        payload = {
            "text": text[:80],
            "callSignNames": names,
            "transmitterGroupNames": groups,
            "emergency": emergency,
        }
        logger.info(
            "DAPNET POST /calls to %s groups=%s server=%s",
            names,
            groups,
            server or self._default_server,
        )
        response = await self._request("POST", "/calls", json=payload, server=server)
        logger.info(
            "DAPNET API resp %s: %s",
            response.status_code,
            response.text[:300],
        )
        if response.status_code >= 400:
            detail = response.text[:300]
            raise DapnetError(
                f"DAPNET rejected the call (HTTP {response.status_code}): {detail}"
            )
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError:
            return {}


def parse_pager_rics(record: dict[str, Any] | None) -> list[int]:
    if not isinstance(record, dict) or "pagers" not in record:
        return []
    found: list[int] = []
    seen: set[int] = set()
    for item in record.get("pagers") or []:
        raw = item
        if isinstance(item, dict):
            raw = item.get("number") or item.get("ric") or item.get("name")
        ric = process_dmr_id(raw)
        if ric <= 0 or ric in seen:
            continue
        seen.add(ric)
        found.append(ric)
    return found
