from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

VAST_CASH_URL = os.environ.get("VAST_CASH_URL", "https://vast-cash-7tjvrgb42ytw49kqtng8yk.streamlit.app")
VAST_CASH_REPO = os.environ.get("VAST_CASH_REPOSITORY", "tonybaylis81-gif/Vast-cash")
PAPER_TRADE_URL = "https://paper-api.alpaca.markets"
STATE_FILE = Path(os.environ.get("PEGASUS_WATCH_STATE", "data/LEDGER/vast_cash_watch_state.json"))


def _request(url: str, headers: dict | None = None, timeout: int = 15):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "PEGASUS-VAST-CASH-WATCH/1.0"})
    return urllib.request.urlopen(req, timeout=timeout)


def _secret(names: list[str]) -> str | None:
    try:
        import streamlit as st
        for name in names:
            value = st.secrets.get(name)
            if value:
                return str(value).strip()
    except Exception:
        pass
    for name in names:
        value = os.getenv(name)
        if value:
            return value.strip()
    return None


def _alpaca_headers() -> dict | None:
    key = _secret(["PAPER_API_KEY", "ALPACA_API_KEY", "ALPACA_API_KEY_ID"])
    secret = _secret(["PAPER_API_SECRET", "ALPACA_SECRET_KEY", "ALPACA_API_SECRET"])
    if not key or not secret:
        return None
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}


def _load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def snapshot() -> dict:
    """Read-only snapshot. This module never submits, cancels, or modifies orders."""
    result = {"checked_at": datetime.now(timezone.utc).isoformat(), "web": {}, "github": {}, "paper": {}}

    try:
        with _request(VAST_CASH_URL) as r:
            result["web"] = {"online": 200 <= r.getcode() < 400, "status": r.getcode()}
    except Exception as exc:
        result["web"] = {"online": False, "message": str(exc)}

    try:
        with _request(
            f"https://api.github.com/repos/{VAST_CASH_REPO}/commits/main",
            {"Accept": "application/vnd.github+json", "User-Agent": "PEGASUS-VAST-CASH-WATCH/1.0"},
        ) as r:
            data = json.loads(r.read().decode())
            result["github"] = {"online": True, "sha": data.get("sha", "")[:12], "message": (data.get("commit", {}).get("message", "") or "").splitlines()[0]}
    except Exception as exc:
        result["github"] = {"online": False, "message": str(exc)}

    headers = _alpaca_headers()
    if not headers:
        result["paper"] = {"configured": False, "message": "Alpaca PAPER credentials are not configured for PEGASUS."}
        return result

    try:
        with _request(f"{PAPER_TRADE_URL}/v2/account", headers) as r:
            account = json.loads(r.read().decode())
        with _request(f"{PAPER_TRADE_URL}/v2/orders?status=open&limit=100", headers) as r:
            orders = json.loads(r.read().decode())
        with _request(f"{PAPER_TRADE_URL}/v2/positions", headers) as r:
            positions = json.loads(r.read().decode())
        result["paper"] = {
            "configured": True,
            "connected": True,
            "account_status": account.get("status"),
            "cash": account.get("cash"),
            "buying_power": account.get("buying_power"),
            "portfolio_value": account.get("portfolio_value"),
            "open_orders": [{"id": o.get("id"), "symbol": o.get("symbol"), "side": o.get("side"), "status": o.get("status"), "qty": o.get("qty")} for o in orders if isinstance(o, dict)],
            "positions": [{"symbol": p.get("symbol"), "qty": p.get("qty"), "market_value": p.get("market_value"), "unrealized_pl": p.get("unrealized_pl")} for p in positions if isinstance(p, dict)],
        }
    except Exception as exc:
        result["paper"] = {"configured": True, "connected": False, "message": str(exc)}
    return result


def detect_changes(current: dict) -> list[str]:
    previous = _load_state()
    alerts: list[str] = []
    if previous:
        old_sha = previous.get("github", {}).get("sha")
        new_sha = current.get("github", {}).get("sha")
        if old_sha and new_sha and old_sha != new_sha:
            alerts.append(f"VAST CASH code changed: {old_sha} -> {new_sha}.")
        old_orders = {o.get("id"): o for o in previous.get("paper", {}).get("open_orders", [])}
        new_orders = {o.get("id"): o for o in current.get("paper", {}).get("open_orders", [])}
        for oid, order in new_orders.items():
            if oid not in old_orders:
                alerts.append(f"New PAPER order: {order.get('side')} {order.get('qty')} {order.get('symbol')}.")
        for oid, order in old_orders.items():
            if oid not in new_orders:
                alerts.append(f"PAPER order left open-order list: {order.get('side')} {order.get('qty')} {order.get('symbol')} ({oid}).")
        old_pos = {p.get("symbol"): p for p in previous.get("paper", {}).get("positions", [])}
        new_pos = {p.get("symbol"): p for p in current.get("paper", {}).get("positions", [])}
        for symbol in sorted(set(old_pos) | set(new_pos)):
            if old_pos.get(symbol) != new_pos.get(symbol):
                alerts.append(f"PAPER position changed: {symbol}.")
    if not current.get("web", {}).get("online", False):
        alerts.append("VAST CASH web application is not responding.")
    if not current.get("github", {}).get("online", False):
        alerts.append("VAST CASH GitHub repository could not be checked.")
    paper = current.get("paper", {})
    if paper.get("configured") and not paper.get("connected"):
        alerts.append("Alpaca PAPER account could not be reached.")
    _save_state(current)
    return alerts


if __name__ == "__main__":
    current = snapshot()
    alerts = detect_changes(current)
    print(json.dumps({"alerts": alerts, "snapshot": current}, indent=2))
