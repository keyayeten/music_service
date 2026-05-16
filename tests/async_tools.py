from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session


def run_async(awaitable):
    return asyncio.run(awaitable)


class AsyncSessionAdapter:
    def __init__(self, session: Session) -> None:
        self._session = session

    async def execute(self, *args: Any, **kwargs: Any):
        return self._session.execute(*args, **kwargs)

    async def get(self, *args: Any, **kwargs: Any):
        return self._session.get(*args, **kwargs)

    async def flush(self) -> None:
        self._session.flush()

    async def refresh(self, instance: Any) -> None:
        self._session.refresh(instance)

    async def run_sync(self, fn: Callable[..., Any], *args: Any, **kwargs: Any):
        return fn(self._session, *args, **kwargs)

    def add(self, *args: Any, **kwargs: Any) -> None:
        self._session.add(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> None:
        self._session.delete(*args, **kwargs)
