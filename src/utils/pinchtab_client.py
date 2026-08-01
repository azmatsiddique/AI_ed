"""
pinchtab_client.py
Python client wrapper for interacting with the PinchTab browser automation daemon.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
import urllib.request
import urllib.parse
import urllib.error


class PinchtabClient:
    """
    Client interface for controlling PinchTab browser automation daemon.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:9867", token: Optional[str] = None):
        self.base_url = os.environ.get("PINCHTAB_URL", base_url).rstrip("/")
        self.token = token or os.environ.get("PINCHTAB_TOKEN")

        # Fallback to reading token from ~/.pinchtab/config.json if available
        if not self.token:
            config_path = Path.home() / ".pinchtab" / "config.json"
            if config_path.is_file():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                        self.token = cfg.get("server", {}).get("token")
                except Exception:
                    pass

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(self, endpoint: str, method: str = "GET", data: Optional[Dict[str, Any]] = None, timeout: int = 15) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._headers()

        payload = json.dumps(data).encode("utf-8") if data else None
        req = urllib.request.Request(url, data=payload, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8")
                return json.loads(err_body)
            except Exception:
                return {"error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"error": str(e)}

    def is_healthy(self) -> bool:
        """Check if PinchTab daemon is running and healthy."""
        res = self._request("/health", method="GET", timeout=5)
        return res.get("status") == "ok"

    def get_status(self) -> Dict[str, Any]:
        """Get full PinchTab server status."""
        return self._request("/health", method="GET", timeout=5)

    def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate Chrome to a specific URL."""
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"
        return self._request("/navigate", method="POST", data={"url": url}, timeout=30)

    def get_text(self) -> Dict[str, Any]:
        """Extract main text content from currently active tab."""
        return self._request("/text", method="GET", timeout=15)

    def get_snapshot(self, filter_mode: str = "interactive") -> Dict[str, Any]:
        """Get token-efficient accessibility snapshot of active tab."""
        endpoint = f"/snapshot?filter={filter_mode}"
        return self._request(endpoint, method="GET", timeout=15)

    def browse_and_extract(self, url: str) -> Dict[str, Any]:
        """Convenience method: navigate to URL and return extracted text content."""
        nav_res = self.navigate(url)
        if "error" in nav_res and nav_res.get("code") != "already_at_url":
            return nav_res

        text_res = self.get_text()
        return {
            "url": nav_res.get("url", url),
            "title": nav_res.get("title", text_res.get("title", "")),
            "text": text_res.get("text", ""),
            "status": "success"
        }
