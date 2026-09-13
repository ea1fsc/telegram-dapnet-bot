from __future__ import annotations

from dataclasses import dataclass
import logging

import httpx

logger = logging.getLogger(__name__)

RADIOID_URL = "https://radioid.net/api/dmr/user/?callsign={callsign}"
MIN_RIC = 1
MAX_RIC = 2_097_151


@dataclass(frozen=True)
class RadioIdRic:
    ric: int
    callsign: str


def process_dmr_id(dmr_id: int) -> int:
    """Map a DMR ID onto the POCSAG RIC range used by DAPNET (from PagerBot)."""
    try:
        value = int(dmr_id)
    except (TypeError, ValueError):
        return 0
    if value > MAX_RIC and len(str(value)) > 1:
        trimmed = int(str(value)[1:])
        if MIN_RIC <= trimmed <= MAX_RIC:
            return trimmed
    if MIN_RIC <= value <= MAX_RIC:
        return value
    return 0


async def lookup_rics(callsign: str, *, timeout: float = 10.0) -> list[RadioIdRic]:
    url = RADIOID_URL.format(callsign=callsign.upper())
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        logger.warning("RadioID lookup failed for %s: %s", callsign, exc)
        return []
    except ValueError:
        logger.warning("RadioID returned invalid JSON for %s", callsign)
        return []

    found: list[RadioIdRic] = []
    seen: set[int] = set()
    for row in payload.get("results") or []:
        ric = process_dmr_id(row.get("id"))
        name = str(row.get("callsign") or "").strip()
        if ric <= 0 or not name or ric in seen:
            continue
        seen.add(ric)
        found.append(RadioIdRic(ric=ric, callsign=name))
    return found
