"""Tastytrade session.

Demo mode never opens a socket and never sends an order. Live mode talks to
the production API. It refuses to start unless a refresh token, a client
secret, and an account number are present. Cert is not a third mode.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

PROD = "https://api.tastyworks.com"


@dataclass
class TastyStatus:
    mode: str
    connected: bool
    account: str | None
    message: str


class TastyClient:
    def __init__(self, mode: str) -> None:
        if mode not in ("demo", "live"):
            raise ValueError("mode must be demo or live")
        self.mode = mode
        self.base = PROD
        self.account = os.environ.get("TASTY_ACCOUNT_NUMBER") or None
        self._token: str | None = None

    def status(self) -> TastyStatus:
        if self.mode == "demo":
            return TastyStatus("demo", True, None, "Demo mode. Orders stay on this machine and are not sent to Tastytrade.")
        missing = [name for name in ("TASTY_CLIENT_SECRET", "TASTY_REFRESH_TOKEN", "TASTY_ACCOUNT_NUMBER") if not os.environ.get(name)]
        if missing:
            return TastyStatus("live", False, None, "Live mode needs " + ", ".join(missing) + ". No order will be sent until they are set.")
        return TastyStatus("live", bool(self._token), self.account, "Live production account." if self._token else "Credentials present. Not signed in yet.")

    def login(self) -> TastyStatus:
        if self.mode == "demo":
            return self.status()
        secret = os.environ.get("TASTY_CLIENT_SECRET", "")
        refresh = os.environ.get("TASTY_REFRESH_TOKEN", "")
        client_id = os.environ.get("TASTY_CLIENT_ID", "")
        if not secret or not refresh:
            return self.status()
        import httpx
        response = httpx.post(
            f"{self.base}/oauth/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh,
                "client_secret": secret,
                "client_id": client_id,
            },
            timeout=20.0,
        )
        response.raise_for_status()
        self._token = response.json().get("access_token")
        return self.status()

    def quote_token(self) -> dict:
        """Production DXLink token. Demo mode does not call this."""
        if self.mode != "live" or not self._token:
            raise RuntimeError("quote stream requires a live signed-in session")
        import httpx
        response = httpx.get(
            f"{self.base}/api-quote-tokens",
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=20.0,
        )
        response.raise_for_status()
        return response.json()
