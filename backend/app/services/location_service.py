"""Reverse geocoding adapter used by the complaint form."""

from __future__ import annotations

from typing import Any
import time

import httpx

from app.config import get_settings
from app.exceptions import AIServiceError, ProviderUnavailableError, ValidationError

_catalog_cache: dict[str, Any] | None = None
_catalog_loaded_at = 0.0
_CATALOG_TTL_SECONDS = 24 * 60 * 60


async def _india_catalog() -> dict[str, Any]:
    global _catalog_cache, _catalog_loaded_at
    settings = get_settings()
    if _catalog_cache is not None and time.time() - _catalog_loaded_at < _CATALOG_TTL_SECONDS:
        return _catalog_cache
    if not settings.INDIA_LOCATION_DATA_URL.strip():
        raise ProviderUnavailableError("An approved India location catalog is not configured")
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(settings.INDIA_LOCATION_DATA_URL)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderUnavailableError("India location catalog is temporarily unavailable") from exc
    catalog = _normalise_catalog(payload)
    if not catalog["states"]:
        raise ProviderUnavailableError("India location catalog did not contain any states")
    _catalog_cache = catalog
    _catalog_loaded_at = time.time()
    return catalog


def _normalise_catalog(payload: Any) -> dict[str, Any]:
    raw_states = payload.get("states", payload) if isinstance(payload, dict) else payload
    states: list[dict[str, Any]] = []
    for raw_state in raw_states if isinstance(raw_states, list) else []:
        if isinstance(raw_state, str):
            states.append({"name": raw_state, "districts": []})
            continue
        if not isinstance(raw_state, dict):
            continue
        state_name = raw_state.get("name") or raw_state.get("state") or raw_state.get("state_name")
        if not state_name:
            continue
        raw_districts = raw_state.get("districts") or raw_state.get("children") or []
        districts: list[dict[str, Any]] = []
        for raw_district in raw_districts:
            if isinstance(raw_district, str):
                districts.append({"name": raw_district, "sub_districts": []})
                continue
            if not isinstance(raw_district, dict):
                continue
            district_name = raw_district.get("name") or raw_district.get("district") or raw_district.get("district_name")
            if district_name:
                raw_subdistricts = raw_district.get("sub_districts") or raw_district.get("subdistricts") or raw_district.get("tehsils") or []
                subdistricts = [
                    {"name": item if isinstance(item, str) else item.get("name") or item.get("sub_district") or item.get("tehsil")}
                    for item in raw_subdistricts
                    if isinstance(item, str) or (isinstance(item, dict) and (item.get("name") or item.get("sub_district") or item.get("tehsil")))
                ]
                districts.append({"name": district_name, "sub_districts": subdistricts})
        states.append({"name": str(state_name), "districts": districts})
    states.sort(key=lambda item: item["name"].casefold())
    return {"country": "India", "country_code": "IN", "states": states}


async def india_states() -> list[dict[str, Any]]:
    return [{"name": item["name"], "district_count": len(item["districts"])} for item in (await _india_catalog())["states"]]


async def india_districts(state: str) -> list[dict[str, Any]]:
    catalog = await _india_catalog()
    match = next((item for item in catalog["states"] if item["name"].casefold() == state.strip().casefold()), None)
    if not match:
        raise ValidationError("Unknown Indian state or union territory")
    return [{"name": item["name"], "sub_district_count": len(item["sub_districts"])} for item in match["districts"]]


async def india_sub_districts(state: str, district: str) -> list[dict[str, str]]:
    catalog = await _india_catalog()
    state_match = next((item for item in catalog["states"] if item["name"].casefold() == state.strip().casefold()), None)
    if not state_match:
        raise ValidationError("Unknown Indian state or union territory")
    district_match = next((item for item in state_match["districts"] if item["name"].casefold() == district.strip().casefold()), None)
    if not district_match:
        raise ValidationError("Unknown district for the selected state")
    return district_match["sub_districts"]


async def reverse_geocode(latitude: float, longitude: float) -> dict[str, Any]:
    settings = get_settings()
    if settings.GEOCODING_PROVIDER.lower() == "disabled":
        return {"formatted_address": None, "state": None, "district": None, "city": None, "locality": None, "pincode": None}
    try:
        async with httpx.AsyncClient(timeout=8.0, headers={"User-Agent": settings.GEOCODING_USER_AGENT}) as client:
            response = await client.get(settings.GEOCODING_URL, params={"lat": latitude, "lon": longitude, "format": "jsonv2", "addressdetails": 1})
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise AIServiceError("Location address lookup is temporarily unavailable") from exc
    address = payload.get("address") or {}
    return {
        "formatted_address": payload.get("display_name"),
        "state": address.get("state"),
        "district": address.get("state_district") or address.get("district") or address.get("county"),
        "city": address.get("city") or address.get("town") or address.get("municipality") or address.get("village"),
        "locality": address.get("suburb") or address.get("neighbourhood") or address.get("quarter") or address.get("road"),
        "pincode": address.get("postcode"),
        "country": address.get("country"),
        "country_code": address.get("country_code"),
    }
