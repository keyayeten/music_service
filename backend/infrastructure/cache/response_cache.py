from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from redis import Redis

from backend.config.settings import Settings


@dataclass(slots=True)
class ApiResponseCache:
    redis_client: Redis
    settings: Settings

    def build_key(self, namespace: str, **params: object) -> str:
        normalized_parts = [
            f"{name}={self._normalize_key_part(value)}"
            for name, value in sorted(params.items(), key=lambda item: item[0])
        ]
        suffix = "|".join(normalized_parts) if normalized_parts else "all"
        return f"{self.settings.redis_key_prefix}:http:{namespace}:{suffix}"

    def get_json(self, key: str) -> dict | None:
        raw_value = self.redis_client.get(key)
        if raw_value is None:
            return None
        return json.loads(raw_value)

    def set_json(self, key: str, payload: dict, ttl_seconds: int) -> None:
        self.redis_client.setex(key, ttl_seconds, json.dumps(payload, separators=(",", ":"), ensure_ascii=True))

    def ttl_for_catalog_reads(self) -> int:
        return self.settings.redis_ttl_catalog_reads_seconds

    def ttl_for_public_playlist_reads(self) -> int:
        return self.settings.redis_ttl_public_playlist_reads_seconds

    @staticmethod
    def _normalize_key_part(value: object) -> str:
        if value is None:
            return "none"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (str, int)):
            return str(value)
        if isinstance(value, (UUID, Decimal)):
            return str(value)
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return str(value)
