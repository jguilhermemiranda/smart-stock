from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

class DeviceError(RuntimeError):
    pass

class DeviceClient:
    def __init__(self, host: str, port: int = 80, timeout: float = 5.0) -> None:
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout

    def request(self, method: str, path: str, payload: dict | None = None) -> dict:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(self.base_url + path, data=body, method=method, headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as exc:
            raise DeviceError(str(exc)) from exc

    def health(self) -> dict: return self.request("GET", "/health")
    def status(self) -> dict: return self.request("GET", "/status")
    def sync(self, payload: dict) -> dict: return self.request("POST", "/sync", payload)
    def move(self, drawer_id: int) -> dict: return self.request("POST", "/move", {"drawer_id": drawer_id})
    def home(self) -> dict: return self.request("POST", "/home", {})
