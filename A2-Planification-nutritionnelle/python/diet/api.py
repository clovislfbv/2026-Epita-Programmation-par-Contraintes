from __future__ import annotations

import json
from typing import Any, Dict

from .weekly import benchmark_weekly as _benchmark_weekly
from .weekly import solve_weekly as _solve_weekly


def _load_payload(payload: Any) -> Dict[str, Any]:
    """Convert various payload types (dict, str, JsProxy) to a Python dict.

    Handles Pyodide JsProxy objects by first trying .to_py(), then
    Object.fromEntries(), and finally JSON round-tripping as a last resort.
    """
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        return json.loads(payload)

    # ── Pyodide JsProxy handling ──
    if hasattr(payload, "to_py"):
        try:
            converted = payload.to_py()
            if isinstance(converted, dict):
                return converted
            if isinstance(converted, str):
                return json.loads(converted)
        except Exception:
            pass

    # Fallback: try JSON.stringify on the JS side via the proxy
    if hasattr(payload, "js_id"):
        try:
            from pyodide.ffi import to_js  # noqa: F401
            import js  # type: ignore

            json_str = js.JSON.stringify(payload)
            return json.loads(json_str)
        except Exception:
            pass

    # Final fallback: iterate proxy as a Map-like object
    if callable(getattr(payload, "keys", None)):
        try:
            result = {}
            for key in payload.keys():
                val = payload[key]
                if hasattr(val, "to_py"):
                    val = val.to_py()
                result[key] = val
            if result:
                return result
        except Exception:
            pass

    raise TypeError(
        f"payload must be dict or json string, got {type(payload).__name__}"
    )


def solve_weekly_api(payload: Any) -> Dict[str, Any]:
    data = _load_payload(payload)
    return _solve_weekly(
        data["dishes"],
        data["bounds"],
        season=str(data.get("season", "summer")),
        budget=float(data["budget"]) if data.get("budget") is not None else None,
        preferences=data.get("preferences", {}),
        days=int(data.get("days", 7)),
        solver=str(data.get("solver", "cpsat")),
    )


def solve_weekly_json(payload: Any) -> str:
    return json.dumps(solve_weekly_api(payload))


def benchmark_weekly_api(payload: Any) -> Dict[str, Any]:
    data = _load_payload(payload)
    return _benchmark_weekly(
        data["dishes"],
        data["bounds"],
        season=str(data.get("season", "summer")),
        budget=float(data["budget"]) if data.get("budget") is not None else None,
        preferences=data.get("preferences", {}),
        days=int(data.get("days", 7)),
    )


def benchmark_weekly_json(payload: Any) -> str:
    return json.dumps(benchmark_weekly_api(payload))


solve_weekly = solve_weekly_api
benchmark_weekly = benchmark_weekly_api
