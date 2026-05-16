import json
import time
from urllib.request import urlopen


URLS = (
    "http://127.0.0.1:8000/health",
    "http://127.0.0.1:8000/api/v1/health",
)


def main() -> None:
    for url in URLS:
        payload = None
        last_error: Exception | None = None
        for _ in range(30):
            try:
                with urlopen(url, timeout=10) as response:  # noqa: S310
                    payload = json.loads(response.read().decode("utf-8"))
                break
            except Exception as exc:  # pragma: no cover - best effort readiness
                last_error = exc
                time.sleep(1)
        if payload is None:
            raise RuntimeError(f"Endpoint is unavailable: {url}, error={last_error}")
        assert payload.get("status") == "ok", f"{url} status={payload.get('status')}"
        assert payload.get("database") == "ok", f"{url} database={payload.get('database')}"
        assert payload.get("redis") == "ok", f"{url} redis={payload.get('redis')}"
        print(f"{url} OK")


if __name__ == "__main__":
    main()
