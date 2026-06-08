from __future__ import annotations

from uuid import UUID

from backend.domain.common.exceptions import ValidationError
from backend.domain.library.repositories import (
    LIBRARY_ITEM_TYPES,
    LIBRARY_SECTIONS,
    LibraryItemReadModel,
    LibraryListFilter,
    LibraryRepository,
)


class LibraryItemUseCases:
    def __init__(self, repository: LibraryRepository) -> None:
        self._repository = repository

    async def add_item(
        self,
        actor_user_id: UUID,
        *,
        item_type: str,
        item_id: UUID,
        section: str,
    ) -> LibraryItemReadModel:
        normalized_item_type = _normalize_item_type(item_type)
        normalized_section = _normalize_section(section)
        if not await self._repository.item_exists(normalized_item_type, item_id):
            raise ValidationError("Library item target is not found.")
        return await self._repository.add_library_item(
            user_id=actor_user_id,
            item_type=normalized_item_type,
            item_id=item_id,
            section=normalized_section,
        )

    async def remove_item(self, actor_user_id: UUID, *, item_type: str, item_id: UUID) -> None:
        normalized_item_type = _normalize_item_type(item_type)
        if not await self._repository.remove_library_item(
            user_id=actor_user_id,
            item_type=normalized_item_type,
            item_id=item_id,
        ):
            raise ValidationError("Library item is not found.")

    async def list_items(
        self,
        actor_user_id: UUID,
        *,
        section: str | None,
        item_type: str | None,
        limit: int,
        offset: int,
    ) -> list[LibraryItemReadModel]:
        if limit < 1 or limit > 100:
            raise ValidationError("Limit should be between 1 and 100.")
        if offset < 0:
            raise ValidationError("Offset should be a non-negative number.")
        normalized_section = _normalize_section(section) if section is not None else None
        normalized_item_type = _normalize_item_type(item_type) if item_type is not None else None
        return await self._repository.list_library_items(
            LibraryListFilter(
                user_id=actor_user_id,
                section=normalized_section,
                item_type=normalized_item_type,
                limit=limit,
                offset=offset,
            )
        )


def _normalize_item_type(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in LIBRARY_ITEM_TYPES:
        raise ValidationError("Unsupported library item type.")
    return normalized


def _normalize_section(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in LIBRARY_SECTIONS:
        raise ValidationError("Unsupported library section.")
    return normalized
