from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, literal, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.social.repositories import CommentReadModel, SocialRepository, SocialTargetReadModel
from backend.infrastructure.persistence.models.catalog import Album, Track
from backend.infrastructure.persistence.models.library import LibraryItem, Playlist
from backend.infrastructure.persistence.models.social import Comment, Like


class SqlAlchemySocialRepository(SocialRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_target(self, target_type: str, target_id: UUID) -> SocialTargetReadModel | None:
        row = (await self._session.execute(_target_select_stmt(target_type, target_id))).one_or_none()
        if row is None:
            return None
        return SocialTargetReadModel(
            target_type=target_type,
            target_id=target_id,
            likes_count=row.likes_count,
            comments_count=row.comments_count,
        )

    async def add_like(self, *, user_id: UUID, target_type: str, target_id: UUID) -> bool:
        statement = (
            insert(Like)
            .values(user_id=user_id, target_type=target_type, target_id=target_id)
            .on_conflict_do_nothing(index_elements=["user_id", "target_type", "target_id"])
            .returning(Like.id)
        )
        result = await self._session.execute(statement)
        await self._session.flush()
        return result.scalar_one_or_none() is not None

    async def remove_like(self, *, user_id: UUID, target_type: str, target_id: UUID) -> bool:
        result = await self._session.execute(
            delete(Like).where(
                Like.user_id == user_id,
                Like.target_type == target_type,
                Like.target_id == target_id,
            )
        )
        await self._session.flush()
        return bool(result.rowcount)

    async def create_comment(
        self,
        *,
        user_id: UUID,
        target_type: str,
        target_id: UUID,
        parent_comment_id: UUID | None,
        body: str,
        status: str,
    ) -> CommentReadModel:
        entity = Comment(
            user_id=user_id,
            target_type=target_type,
            target_id=target_id,
            parent_comment_id=parent_comment_id,
            body=body,
            status=status,
        )
        self._session.add(entity)
        await self._session.flush()
        return _to_comment_read_model(entity)

    async def get_comment_by_id(self, comment_id: UUID) -> CommentReadModel | None:
        entity = await self._session.get(Comment, comment_id)
        if entity is None:
            return None
        return _to_comment_read_model(entity)

    async def list_comments(
        self,
        *,
        target_type: str,
        target_id: UUID,
        limit: int,
        offset: int,
    ) -> list[CommentReadModel]:
        rows = (await self._session.execute(
            select(Comment)
            .where(
                Comment.target_type == target_type,
                Comment.target_id == target_id,
                Comment.status == "visible",
            )
            .order_by(Comment.created_at.desc())
            .limit(limit)
            .offset(offset)
        )).scalars()
        return [_to_comment_read_model(item) for item in rows]

    async def update_target_counters(
        self,
        *,
        target_type: str,
        target_id: UUID,
        likes_delta: int = 0,
        comments_delta: int = 0,
    ) -> SocialTargetReadModel | None:
        if likes_delta == 0 and comments_delta == 0:
            return await self.get_target(target_type, target_id)
        statement = _target_update_stmt(
            target_type=target_type,
            target_id=target_id,
            likes_delta=likes_delta,
            comments_delta=comments_delta,
        )
        result = await self._session.execute(statement)
        await self._session.flush()
        if result.rowcount == 0:
            return None
        return await self.get_target(target_type, target_id)

    async def add_library_item_for_like(self, *, user_id: UUID, target_type: str, target_id: UUID) -> None:
        statement = (
            insert(LibraryItem)
            .values(
                user_id=user_id,
                item_type=target_type,
                item_id=target_id,
                section=_section_for_target_type(target_type),
            )
            .on_conflict_do_nothing(index_elements=["user_id", "item_type", "item_id"])
        )
        await self._session.execute(statement)
        await self._session.flush()

    async def remove_library_item_for_like(self, *, user_id: UUID, target_type: str, target_id: UUID) -> None:
        await self._session.execute(
            delete(LibraryItem).where(
                LibraryItem.user_id == user_id,
                LibraryItem.item_type == target_type,
                LibraryItem.item_id == target_id,
            )
        )
        await self._session.flush()


def _target_select_stmt(target_type: str, target_id: UUID):
    if target_type == "track":
        return (
            select(Track.likes_count.label("likes_count"), Track.comments_count.label("comments_count"))
            .where(Track.id == target_id, Track.status == "published")
            .limit(1)
        )
    if target_type == "album":
        return (
            select(Album.likes_count.label("likes_count"), Album.comments_count.label("comments_count"))
            .where(Album.id == target_id, Album.status == "published")
            .limit(1)
        )
    return (
        select(Playlist.likes_count.label("likes_count"), Playlist.comments_count.label("comments_count"))
        .where(Playlist.id == target_id, Playlist.visibility.in_(("public", "unlisted")))
        .limit(1)
    )


def _target_update_stmt(
    *,
    target_type: str,
    target_id: UUID,
    likes_delta: int,
    comments_delta: int,
):
    likes_expr = func.greatest(literal(0), literal(likes_delta) + _target_likes_column(target_type))
    comments_expr = func.greatest(literal(0), literal(comments_delta) + _target_comments_column(target_type))
    table = _target_table(target_type)
    filters = _target_filters(target_type, target_id)
    return (
        update(table)
        .where(*filters)
        .values(
            likes_count=likes_expr,
            comments_count=comments_expr,
        )
    )


def _target_table(target_type: str):
    if target_type == "track":
        return Track
    if target_type == "album":
        return Album
    return Playlist


def _target_likes_column(target_type: str):
    if target_type == "track":
        return Track.likes_count
    if target_type == "album":
        return Album.likes_count
    return Playlist.likes_count


def _target_comments_column(target_type: str):
    if target_type == "track":
        return Track.comments_count
    if target_type == "album":
        return Album.comments_count
    return Playlist.comments_count


def _target_filters(target_type: str, target_id: UUID):
    if target_type == "track":
        return (Track.id == target_id, Track.status == "published")
    if target_type == "album":
        return (Album.id == target_id, Album.status == "published")
    return (Playlist.id == target_id, Playlist.visibility.in_(("public", "unlisted")))


def _to_comment_read_model(entity: Comment) -> CommentReadModel:
    return CommentReadModel(
        id=entity.id,
        user_id=entity.user_id,
        target_type=entity.target_type,
        target_id=entity.target_id,
        parent_comment_id=entity.parent_comment_id,
        body=entity.body,
        status=entity.status,
        created_at=entity.created_at,
    )


def _section_for_target_type(target_type: str) -> str:
    if target_type == "track":
        return "favorites"
    if target_type == "album":
        return "albums"
    return "playlists"
