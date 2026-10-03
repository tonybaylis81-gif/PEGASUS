from __future__ import annotations

import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from collections.abc import Mapping

VAST_CASH_URL = os.environ.get("VAST_CASH_URL", "https://vast-cash-7tjvrgb42ytw49kqtng8yk.streamlit.app")
VAST_CASH_REPO = os.environ.get("VAST_CASH_REPOSITORY", "tonybaylis81-gif/Vast-cash")
PAPER_TRADE_URL = "https://paper-api.alpaca.markets"


def _secret(names: list[str]) -> str | None:
    wanted = {x.upper() for x in names}
    try:
        import streamlit as st
        def walk(v):
            if isinstance(v, Mapping):
                for k, x in v.items():
                    if str(k).upper() in wanted and x is not None and str(x).strip():
                        return str(x).strip()
                    found = walk(x)
                    if found:
                        return found
        found = walk(st.secrets)
        if found:
            return found
    except Exception:
        pass
    for name in wanted:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return None


def _request(url: str, headers: dict | None = None, timeout: int = 10):
    request = urllib.request.Request(
        url,
        headers=headers or {"User-Agent": "PEGASUS-VAST-CASH-SENTINEL/1.0"},
    )
    return urllib.request.urlopen(request, timeout=timeout)


def check_web_app(url: str = VAST_CASH_URL) -> dict:
    """Check whether the public VAST CASH Streamlit endpoint responds."""
    checked = datetime.now(timezone.utc).isoformat()
    try:
        with _request(url, timeout=12) as response:
            code = getattr(response, "status", response.getcode())
            return {
                "online": 200 <= code < 400,
                "status": code,
                "url": url,
                "checked_at": checked,
                "message": "VAST CASH web application responded.",
            }
    except Exception as exc:
        return {
            "online": False,
            "status": None,
            "url": url,
            "checked_at": checked,
            "message": f"VAST CASH web endpoint unavailable: {exc}",
        }


def check_github() -> dict:
    """Check the VAST CASH repository's current main-branch commit."""
    checked = datetime.now(timezone.utc).isoformat()
    url = f"https://api.github.com/repos/{VAST_CASH_REPO}/commits/main"
    try:
        with _request(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "PEGASUS-VAST-CASH-SENTINEL/1.0",
        }, timeout=12) as response:
            import json
            data = json.loads(response.read().decode("utf-8"))
            return {
                "online": True,
                "sha": data.get("sha", "")[:12],
                "message": (data.get("commit", {}).get("message", "") or "").splitlines()[0],
                "checked_at": checked,
            }
    except Exception as exc:
        return {"online": False, "sha": "", "message": str(exc), "checked_at": checked}


def _alpaca_headers() -> dict | None:
    key = _secret(["PAPER_API_KEY", "ALPACA_API_KEY", "ALPACA_API_KEY_ID", "API_KEY"])
    secret = _secret(["PAPER_API_SECRET", "ALPACA_SECRET_KEY", "ALPACA_API_SECRET", "API_SECRET", "SECRET_KEY"])
    if not key or not secret:
        return None
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}


def check_paper_account() -> dict:
    """Read-only check of the Alpaca PAPER account and open orders."""
    checked = datetime.now(timezone.utc).isoformat()
    headers = _alpaca_headers()
    if not headers:
        return {"configured": False, "checked_at": checked, "message": "No Alpaca PAPER credentials configured in Pegasus."}
    try:
        with _request(f"{PAPER_TRADE_URL}/v2/account", headers=headers, timeout=10) as response:
            import json
            account = json.loads(response.read().decode("utf-8"))
        with _request(f"{PAPER_TRADE_URL}/v2/orders?status=open&limit=100", headers=headers, timeout=10) as response:
            orders = json.loads(response.read().decode("utf-8"))
        return {
            "configured": True,
            "connected": True,
            "checked_at": checked,
            "status": account.get("status"),
            "buying_power": account.get("buying_power"),
            "cash": account.get("cash"),
            "portfolio_value": account.get("portfolio_value"),
            "open_orders": len(orders) if isinstance(orders, list) else 0,
            "message": "Alpaca PAPER account responded. Read-only monitoring only.",
        }
    except Exception as exc:
        return {"configured": True, "connected": False, "checked_at": checked, "message": f"Alpaca PAPER monitor error: {exc}"}


def run_vast_cash_sentinel() -> dict:
    web = check_web_app()
    github = check_github()
    paper = check_paper_account()
    if not web["online"]:
        state = "RED"
    elif paper.get("configured") and not paper.get("connected"):
        state = "AMBER"
    elif not github["online"]:
        state = "AMBER"
    else:
        state = "GREEN"
    return {"state": state, "web": web, "github": github, "paper": paper}
