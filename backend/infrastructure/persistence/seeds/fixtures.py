from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
import random
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from backend.application.identity.security import hash_password
from backend.infrastructure.persistence.models.catalog import (
    ALBUM_STATUSES,
    ENTITY_TYPES,
    MUSIC_SERVICES,
    TRACK_STATUSES,
    Album,
    AlbumTrack,
    EntityTag,
    ExternalLink,
    Genre,
    Tag,
    Track,
    TrackAuthor,
    TrackGenre,
)
from backend.infrastructure.persistence.models.discovery import TRACK_EVENT_TYPES, ExternalLinkClick, UserTrackEvent
from backend.infrastructure.persistence.models.identity import ComposerProfile, Role, User, UserRole, UserRoleProfile
from backend.infrastructure.persistence.models.library import LIBRARY_SECTIONS, PLAYLIST_VISIBILITIES, LibraryItem, Playlist, PlaylistTrack
from backend.infrastructure.persistence.models.moderation import REPORT_STATUSES, ModerationAction, Report
from backend.infrastructure.persistence.models.social import Comment, Like, SOCIAL_TARGET_TYPES
from backend.infrastructure.persistence.seeds.identity_roles import seed_identity_roles

GENRE_PAIRS: tuple[tuple[str, str], ...] = (
    ("pop", "Pop"),
    ("rock", "Rock"),
    ("hiphop", "Hip-Hop"),
    ("jazz", "Jazz"),
    ("electronic", "Electronic"),
    ("classical", "Classical"),
    ("folk", "Folk"),
    ("metal", "Metal"),
)
TAG_PAIRS: tuple[tuple[str, str], ...] = (
    ("mood-happy", "Happy"),
    ("mood-chill", "Chill"),
    ("mood-dark", "Dark"),
    ("workout", "Workout"),
    ("focus", "Focus"),
    ("party", "Party"),
    ("night", "Night"),
    ("acoustic", "Acoustic"),
)


@dataclass(frozen=True)
class FixtureSeedOptions:
    users: int = 1000
    tracks: int = 10000
    albums: int = 100
    playlists: int = 1000
    batch_size: int = 500


@dataclass(frozen=True)
class FixtureSeedResult:
    users_created: int
    tracks_created: int
    albums_created: int
    playlists_created: int
    likes_created: int
    comments_created: int
    events_created: int
    reports_created: int
    moderation_actions_created: int


def seed_fixtures(session: Session, options: FixtureSeedOptions) -> FixtureSeedResult:
    rng = random.Random()
    role_map = _seed_identity_phase(session, options.users, options.batch_size, rng)
    catalog_state = _seed_catalog_phase(session, options.tracks, options.albums, options.batch_size, rng, role_map)
    playlist_state = _seed_library_phase(
        session,
        options.playlists,
        options.batch_size,
        rng,
        role_map["all_user_ids"],
        catalog_state,
    )
    social_state = _seed_social_phase(
        session,
        options.batch_size,
        rng,
        role_map["all_user_ids"],
        catalog_state,
        playlist_state,
    )
    discovery_events = _seed_discovery_phase(session, options.batch_size, rng, role_map["all_user_ids"], catalog_state)
    moderation_state = _seed_moderation_phase(
        session,
        options.batch_size,
        rng,
        role_map["all_user_ids"],
        role_map["staff_user_ids"],
        catalog_state,
        playlist_state,
        social_state["comment_ids"],
    )
    session.commit()
    return FixtureSeedResult(
        users_created=len(role_map["created_user_ids"]),
        tracks_created=len(catalog_state["created_track_ids"]),
        albums_created=len(catalog_state["created_album_ids"]),
        playlists_created=len(playlist_state["created_playlist_ids"]),
        likes_created=social_state["likes_created"],
        comments_created=social_state["comments_created"],
        events_created=discovery_events,
        reports_created=moderation_state["reports_created"],
        moderation_actions_created=moderation_state["actions_created"],
    )


def collect_fixture_stats(session: Session) -> dict[str, Any]:
    return {
        "totals": {
            "users": _count_rows(session, User),
            "composer_profiles": _count_rows(session, ComposerProfile),
            "tracks": _count_rows(session, Track),
            "albums": _count_rows(session, Album),
            "playlists": _count_rows(session, Playlist),
            "likes": _count_rows(session, Like),
            "comments": _count_rows(session, Comment),
            "user_track_events": _count_rows(session, UserTrackEvent),
            "reports": _count_rows(session, Report),
            "moderation_actions": _count_rows(session, ModerationAction),
        },
        "tracks_by_status": _count_group(session, Track.status),
        "albums_by_status": _count_group(session, Album.status),
        "playlists_by_visibility": _count_group(session, Playlist.visibility),
        "reports_by_status": _count_group(session, Report.status),
        "events_by_type": _count_group(session, UserTrackEvent.event_type),
        "users_by_status": _count_group(session, User.status),
    }


def _seed_identity_phase(session: Session, users_count: int, batch_size: int, rng: random.Random) -> dict[str, list[UUID]]:
    seed_identity_roles(session)
    session.flush()
    role_map = {
        code: role_id
        for code, role_id in session.execute(select(Role.code, Role.id)).all()
    }
    required_roles = {"user", "composer", "moderator", "admin"}
    missing_roles = required_roles - set(role_map)
    if missing_roles:
        raise RuntimeError(f"Required roles are missing: {sorted(missing_roles)}")

    password_hash = hash_password("FixturePassword123!")
    user_payloads: list[dict[str, Any]] = []
    role_codes_by_index: list[list[str]] = []
    for index in range(users_count):
        unique_tail = f"{datetime.now(tz=UTC).strftime('%Y%m%d%H%M%S')}{index:05d}{rng.randint(0, 9999):04d}"
        status = _pick_weighted(rng, [("active", 0.92), ("blocked", 0.05), ("deleted", 0.03)])
        roles = ["user"]
        if index < max(1, users_count // 5):
            roles.append("composer")
        if index < max(1, users_count // 25):
            roles.append("moderator")
        if index < max(1, users_count // 100):
            roles.append("admin")

        user_payloads.append(
            {
                "email": f"fixture_{unique_tail}@example.com",
                "username": f"fixture_{unique_tail}",
                "password_hash": password_hash,
                "is_superuser": "admin" in roles,
                "status": status,
            }
        )
        role_codes_by_index.append(roles)

    created_user_ids: list[UUID] = []
    user_roles_rows: list[dict[str, Any]] = []
    composer_user_ids: list[UUID] = []
    for chunk_start in range(0, len(user_payloads), batch_size):
        chunk_end = min(chunk_start + batch_size, len(user_payloads))
        chunk_payloads = user_payloads[chunk_start:chunk_end]
        chunk_roles = role_codes_by_index[chunk_start:chunk_end]
        inserted_rows = session.execute(
            pg_insert(User).returning(User.id),
            chunk_payloads,
        ).all()
        inserted_ids = [row.id for row in inserted_rows]
        created_user_ids.extend(inserted_ids)
        for user_id, role_codes in zip(inserted_ids, chunk_roles, strict=True):
            for role_code in role_codes:
                user_roles_rows.append({"user_id": user_id, "role_id": role_map[role_code]})
            if "composer" in role_codes:
                composer_user_ids.append(user_id)
        session.flush()

    _bulk_insert_with_conflict(session, UserRole, user_roles_rows, batch_size, ["user_id", "role_id"])

    profile_rows = []
    for composer_user_id in composer_user_ids:
        profile_rows.append(
            {
                "user_id": composer_user_id,
                "display_name": f"Composer {str(composer_user_id)[:8]}",
                "bio": "Generated fixture composer profile.",
                "country_code": _pick_weighted(rng, [("US", 0.35), ("GB", 0.2), ("DE", 0.15), ("FR", 0.15), ("UA", 0.15)]),
                "verified": rng.random() < 0.08,
            }
        )

    composer_profiles: list[tuple[UUID, UUID]] = []
    for chunk_start in range(0, len(profile_rows), batch_size):
        chunk = profile_rows[chunk_start : chunk_start + batch_size]
        profile_records = session.execute(
            pg_insert(ComposerProfile).returning(ComposerProfile.id, ComposerProfile.user_id),
            chunk,
        ).all()
        composer_profiles.extend([(row.id, row.user_id) for row in profile_records])
        session.flush()

    user_role_profiles_rows = [
        {
            "user_id": user_id,
            "role_id": role_map["composer"],
            "profile_type": "composer_profile",
            "profile_id": profile_id,
        }
        for profile_id, user_id in composer_profiles
    ]
    _bulk_insert_with_conflict(
        session,
        UserRoleProfile,
        user_role_profiles_rows,
        batch_size,
        ["user_id", "role_id", "profile_type"],
    )
    session.commit()

    staff_user_ids = [
        row.user_id
        for row in session.execute(
            select(UserRole.user_id).where(UserRole.role_id.in_((role_map["moderator"], role_map["admin"])))
        ).all()
    ]
    composer_profile_ids = [profile_id for profile_id, _ in composer_profiles]
    return {
        "created_user_ids": created_user_ids,
        "all_user_ids": created_user_ids,
        "composer_user_ids": composer_user_ids,
        "composer_profile_ids": composer_profile_ids,
        "staff_user_ids": staff_user_ids,
    }


def _seed_catalog_phase(
    session: Session,
    tracks_count: int,
    albums_count: int,
    batch_size: int,
    rng: random.Random,
    role_state: dict[str, list[UUID]],
) -> dict[str, Any]:
    composer_profile_ids = role_state["composer_profile_ids"]
    if not composer_profile_ids:
        composer_profile_ids = list(session.execute(select(ComposerProfile.id)).scalars())
    if not composer_profile_ids:
        raise RuntimeError("At least one composer profile is required for fixtures seeding.")

    genre_ids = _ensure_genres(session)
    tag_ids = _ensure_tags(session)

    created_track_ids: list[UUID] = []
    published_track_ids: list[UUID] = []
    track_rows: list[dict[str, Any]] = []
    now = datetime.now(tz=UTC)
    for index in range(tracks_count):
        status = _pick_weighted(
            rng,
            [
                ("published", 0.5),
                ("draft", 0.2),
                ("pending_review", 0.15),
                ("rejected", 0.1),
                ("hidden", 0.05),
            ],
        )
        published_at = now - timedelta(days=rng.randint(0, 365)) if status == "published" else None
        track_rows.append(
            {
                "title": f"Fixture Track {index + 1}",
                "description": "Generated fixture track.",
                "status": status,
                "duration_seconds": rng.randint(90, 420),
                "published_at": published_at,
            }
        )

    track_authors_rows: list[dict[str, Any]] = []
    track_genres_rows: list[dict[str, Any]] = []
    entity_tags_rows: list[dict[str, Any]] = []
    external_links_rows: list[dict[str, Any]] = []

    for chunk_start in range(0, len(track_rows), batch_size):
        chunk = track_rows[chunk_start : chunk_start + batch_size]
        created_rows = session.execute(
            pg_insert(Track).returning(Track.id, Track.status),
            chunk,
        ).all()
        for row in created_rows:
            created_track_ids.append(row.id)
            if row.status == "published":
                published_track_ids.append(row.id)
            composer_profile_id = rng.choice(composer_profile_ids)
            track_authors_rows.append(
                {
                    "track_id": row.id,
                    "composer_profile_id": composer_profile_id,
                    "contribution_role": "composer",
                    "position": 1,
                }
            )
            for genre_id in rng.sample(genre_ids, k=min(len(genre_ids), rng.randint(1, 3))):
                track_genres_rows.append({"track_id": row.id, "genre_id": genre_id})
            for tag_id in rng.sample(tag_ids, k=min(len(tag_ids), rng.randint(0, 2))):
                entity_tags_rows.append({"tag_id": tag_id, "entity_type": "track", "entity_id": row.id})
            if rng.random() < 0.6:
                service = rng.choice(MUSIC_SERVICES)
                external_links_rows.append(
                    {
                        "entity_type": "track",
                        "entity_id": row.id,
                        "service": service,
                        "url": f"https://fixtures.example/{service}/track/{row.id}",
                        "is_primary": rng.random() < 0.3,
                    }
                )
        session.flush()

    _bulk_insert(session, TrackAuthor, track_authors_rows, batch_size)
    _bulk_insert(session, TrackGenre, track_genres_rows, batch_size)
    _bulk_insert_with_conflict(session, EntityTag, entity_tags_rows, batch_size, ["tag_id", "entity_type", "entity_id"])
    _bulk_insert_with_conflict(
        session,
        ExternalLink,
        external_links_rows,
        batch_size,
        ["entity_type", "entity_id", "service", "url"],
    )

    created_album_ids: list[UUID] = []
    published_album_ids: list[UUID] = []
    album_rows: list[dict[str, Any]] = []
    for index in range(albums_count):
        status = _pick_weighted(
            rng,
            [
                ("published", 0.45),
                ("draft", 0.2),
                ("pending_review", 0.15),
                ("rejected", 0.1),
                ("hidden", 0.1),
            ],
        )
        album_rows.append(
            {
                "owner_composer_id": rng.choice(composer_profile_ids),
                "title": f"Fixture Album {index + 1}",
                "description": "Generated fixture album.",
                "status": status,
                "release_date": date.today() - timedelta(days=rng.randint(0, 2400)),
            }
        )

    album_tracks_rows: list[dict[str, Any]] = []
    for chunk_start in range(0, len(album_rows), batch_size):
        chunk = album_rows[chunk_start : chunk_start + batch_size]
        created_rows = session.execute(
            pg_insert(Album).returning(Album.id, Album.status),
            chunk,
        ).all()
        for row in created_rows:
            created_album_ids.append(row.id)
            if row.status == "published":
                published_album_ids.append(row.id)
            track_pool = published_track_ids if published_track_ids else created_track_ids
            for pos, track_id in enumerate(
                rng.sample(track_pool, k=min(len(track_pool), rng.randint(5, 15))),
                start=1,
            ):
                album_tracks_rows.append({"album_id": row.id, "track_id": track_id, "position": pos})
            if rng.random() < 0.8:
                service = rng.choice(MUSIC_SERVICES)
                external_links_rows.append(
                    {
                        "entity_type": "album",
                        "entity_id": row.id,
                        "service": service,
                        "url": f"https://fixtures.example/{service}/album/{row.id}",
                        "is_primary": rng.random() < 0.4,
                    }
                )
            for tag_id in rng.sample(tag_ids, k=min(len(tag_ids), rng.randint(1, 3))):
                entity_tags_rows.append({"tag_id": tag_id, "entity_type": "album", "entity_id": row.id})
        session.flush()

    _bulk_insert(session, AlbumTrack, album_tracks_rows, batch_size)
    _bulk_insert_with_conflict(
        session,
        EntityTag,
        [row for row in entity_tags_rows if row["entity_type"] == "album"],
        batch_size,
        ["tag_id", "entity_type", "entity_id"],
    )
    _bulk_insert_with_conflict(
        session,
        ExternalLink,
        [row for row in external_links_rows if row["entity_type"] in {"track", "album"}],
        batch_size,
        ["entity_type", "entity_id", "service", "url"],
    )
    session.commit()

    return {
        "created_track_ids": created_track_ids,
        "published_track_ids": published_track_ids,
        "created_album_ids": created_album_ids,
        "published_album_ids": published_album_ids,
        "genre_ids": genre_ids,
        "tag_ids": tag_ids,
    }


def _seed_library_phase(
    session: Session,
    playlists_count: int,
    batch_size: int,
    rng: random.Random,
    all_user_ids: list[UUID],
    catalog_state: dict[str, Any],
) -> dict[str, Any]:
    if not all_user_ids:
        all_user_ids = list(session.execute(select(User.id)).scalars())
    if not all_user_ids:
        raise RuntimeError("At least one user is required for playlists fixtures.")

    track_pool = catalog_state["published_track_ids"] or catalog_state["created_track_ids"]
    album_pool = catalog_state["published_album_ids"] or catalog_state["created_album_ids"]

    playlist_rows = []
    for index in range(playlists_count):
        playlist_rows.append(
            {
                "owner_user_id": rng.choice(all_user_ids),
                "title": f"Fixture Playlist {index + 1}",
                "description": "Generated fixture playlist.",
                "visibility": _pick_weighted(rng, [("public", 0.45), ("unlisted", 0.25), ("private", 0.3)]),
            }
        )

    created_playlist_ids: list[UUID] = []
    visible_playlist_ids: list[UUID] = []
    owner_by_playlist_id: dict[UUID, UUID] = {}
    playlist_tracks_rows: list[dict[str, Any]] = []
    external_links_rows: list[dict[str, Any]] = []
    entity_tags_rows: list[dict[str, Any]] = []
    tag_ids = catalog_state["tag_ids"]

    for chunk_start in range(0, len(playlist_rows), batch_size):
        chunk = playlist_rows[chunk_start : chunk_start + batch_size]
        created_rows = session.execute(
            pg_insert(Playlist).returning(Playlist.id, Playlist.owner_user_id, Playlist.visibility),
            chunk,
        ).all()
        for row in created_rows:
            created_playlist_ids.append(row.id)
            owner_by_playlist_id[row.id] = row.owner_user_id
            if row.visibility in ("public", "unlisted"):
                visible_playlist_ids.append(row.id)
            track_count = min(len(track_pool), rng.randint(6, 30))
            for pos, track_id in enumerate(rng.sample(track_pool, k=track_count), start=1):
                playlist_tracks_rows.append(
                    {
                        "playlist_id": row.id,
                        "track_id": track_id,
                        "added_by_user_id": row.owner_user_id,
                        "position": pos,
                    }
                )
            if rng.random() < 0.4:
                service = rng.choice(MUSIC_SERVICES)
                external_links_rows.append(
                    {
                        "entity_type": "playlist",
                        "entity_id": row.id,
                        "service": service,
                        "url": f"https://fixtures.example/{service}/playlist/{row.id}",
                        "is_primary": rng.random() < 0.25,
                    }
                )
            for tag_id in rng.sample(tag_ids, k=min(len(tag_ids), rng.randint(1, 2))):
                entity_tags_rows.append({"tag_id": tag_id, "entity_type": "playlist", "entity_id": row.id})
        session.flush()

    _bulk_insert(session, PlaylistTrack, playlist_tracks_rows, batch_size)
    _bulk_insert_with_conflict(
        session,
        ExternalLink,
        external_links_rows,
        batch_size,
        ["entity_type", "entity_id", "service", "url"],
    )
    _bulk_insert_with_conflict(session, EntityTag, entity_tags_rows, batch_size, ["tag_id", "entity_type", "entity_id"])

    library_rows = []
    visible_playlist_pool = visible_playlist_ids or created_playlist_ids
    for user_id in all_user_ids:
        for track_id in rng.sample(track_pool, k=min(len(track_pool), rng.randint(2, 8))):
            library_rows.append(
                {
                    "user_id": user_id,
                    "item_type": "track",
                    "item_id": track_id,
                    "section": "favorites",
                }
            )
        for album_id in rng.sample(album_pool, k=min(len(album_pool), rng.randint(1, 3))):
            library_rows.append(
                {
                    "user_id": user_id,
                    "item_type": "album",
                    "item_id": album_id,
                    "section": "albums",
                }
            )
        for playlist_id in rng.sample(visible_playlist_pool, k=min(len(visible_playlist_pool), rng.randint(1, 3))):
            library_rows.append(
                {
                    "user_id": user_id,
                    "item_type": "playlist",
                    "item_id": playlist_id,
                    "section": "playlists",
                }
            )

    _bulk_insert_with_conflict(session, LibraryItem, library_rows, batch_size, ["user_id", "item_type", "item_id"])
    session.commit()
    return {
        "created_playlist_ids": created_playlist_ids,
        "visible_playlist_ids": visible_playlist_ids,
        "playlist_owner_map": owner_by_playlist_id,
    }


def _seed_social_phase(
    session: Session,
    batch_size: int,
    rng: random.Random,
    all_user_ids: list[UUID],
    catalog_state: dict[str, Any],
    playlist_state: dict[str, Any],
) -> dict[str, Any]:
    target_pool: dict[str, list[UUID]] = {
        "track": catalog_state["published_track_ids"][:],
        "album": catalog_state["published_album_ids"][:],
        "playlist": playlist_state["visible_playlist_ids"][:],
    }
    if not all(target_pool.values()):
        raise RuntimeError("Published tracks/albums and visible playlists are required for social fixtures.")

    likes_target_count = max(4000, len(all_user_ids) * 8)
    like_rows = []
    seen_like_keys: set[tuple[UUID, str, UUID]] = set()
    like_library_rows = []
    for _ in range(likes_target_count):
        target_type = _pick_weighted(rng, [("track", 0.65), ("album", 0.2), ("playlist", 0.15)])
        target_id = rng.choice(target_pool[target_type])
        user_id = rng.choice(all_user_ids)
        key = (user_id, target_type, target_id)
        if key in seen_like_keys:
            continue
        seen_like_keys.add(key)
        like_rows.append({"user_id": user_id, "target_type": target_type, "target_id": target_id})
        like_library_rows.append(
            {
                "user_id": user_id,
                "item_type": target_type,
                "item_id": target_id,
                "section": _library_section_for_target(target_type),
            }
        )

    inserted_likes = _bulk_insert_with_conflict(
        session,
        Like,
        like_rows,
        batch_size,
        ["user_id", "target_type", "target_id"],
        return_model=Like,
    )
    _bulk_insert_with_conflict(session, LibraryItem, like_library_rows, batch_size, ["user_id", "item_type", "item_id"])

    comments_target_count = max(2500, len(all_user_ids) * 4)
    comment_rows = []
    for _ in range(comments_target_count):
        target_type = _pick_weighted(rng, [("track", 0.6), ("album", 0.25), ("playlist", 0.15)])
        target_id = rng.choice(target_pool[target_type])
        comment_rows.append(
            {
                "user_id": rng.choice(all_user_ids),
                "target_type": target_type,
                "target_id": target_id,
                "parent_comment_id": None,
                "body": "Generated fixture comment.",
                "status": _pick_weighted(rng, [("visible", 0.85), ("hidden", 0.07), ("pending_review", 0.05), ("deleted", 0.03)]),
            }
        )

    created_root_comments = _bulk_insert(session, Comment, comment_rows, batch_size, return_model=Comment)
    reply_rows = []
    reply_source = [row for row in created_root_comments if row.status == "visible"]
    for _ in range(max(300, len(reply_source) // 8)):
        parent = rng.choice(reply_source)
        reply_rows.append(
            {
                "user_id": rng.choice(all_user_ids),
                "target_type": parent.target_type,
                "target_id": parent.target_id,
                "parent_comment_id": parent.id,
                "body": "Generated fixture reply.",
                "status": "visible",
            }
        )
    created_replies = _bulk_insert(session, Comment, reply_rows, batch_size, return_model=Comment)

    _sync_social_counters(
        session,
        catalog_state["published_track_ids"],
        catalog_state["published_album_ids"],
        playlist_state["visible_playlist_ids"],
    )
    session.commit()

    comment_ids = [row.id for row in created_root_comments] + [row.id for row in created_replies]
    return {
        "likes_created": len(inserted_likes),
        "comments_created": len(created_root_comments) + len(created_replies),
        "comment_ids": comment_ids,
    }


def _seed_discovery_phase(
    session: Session,
    batch_size: int,
    rng: random.Random,
    all_user_ids: list[UUID],
    catalog_state: dict[str, Any],
) -> int:
    published_tracks = catalog_state["published_track_ids"]
    if not published_tracks:
        return 0

    track_links = session.execute(
        select(ExternalLink.id, ExternalLink.entity_id).where(ExternalLink.entity_type == "track", ExternalLink.entity_id.in_(published_tracks))
    ).all()
    links_by_track: dict[UUID, list[UUID]] = {}
    for link_id, track_id in track_links:
        links_by_track.setdefault(track_id, []).append(link_id)

    total_events_target = max(8000, len(all_user_ids) * 12)
    event_rows = []
    click_rows = []
    plays_delta: dict[UUID, int] = {}
    event_types = list(TRACK_EVENT_TYPES)
    for _ in range(total_events_target):
        event_type = _pick_weighted(
            rng,
            [
                ("view", 0.45),
                ("like", 0.2),
                ("save", 0.15),
                ("comment", 0.08),
                ("playlist_add", 0.07),
                ("external_click", 0.05),
            ],
        )
        track_id = rng.choice(published_tracks)
        user_id = rng.choice(all_user_ids)
        event_rows.append(
            {
                "user_id": user_id,
                "track_id": track_id,
                "event_type": event_type if event_type in event_types else "view",
                "metadata": {"source": "fixtures"},
            }
        )
        if event_type == "external_click" and links_by_track.get(track_id):
            link_id = rng.choice(links_by_track[track_id])
            click_rows.append(
                {
                    "user_id": user_id,
                    "external_link_id": link_id,
                    "track_id": track_id,
                    "metadata": {"source": "fixtures"},
                }
            )
            plays_delta[track_id] = plays_delta.get(track_id, 0) + 1

    created_events = _bulk_insert(session, UserTrackEvent, event_rows, batch_size)
    _bulk_insert(session, ExternalLinkClick, click_rows, batch_size)

    for track_id, delta in plays_delta.items():
        session.execute(
            update(Track)
            .where(Track.id == track_id)
            .values(plays_count=Track.plays_count + delta)
        )
    session.flush()
    session.commit()
    return created_events


def _seed_moderation_phase(
    session: Session,
    batch_size: int,
    rng: random.Random,
    all_user_ids: list[UUID],
    staff_user_ids: list[UUID],
    catalog_state: dict[str, Any],
    playlist_state: dict[str, Any],
    comment_ids: list[UUID],
) -> dict[str, int]:
    if not staff_user_ids:
        role_ids = session.execute(select(Role.id).where(Role.code.in_(("moderator", "admin")))).scalars().all()
        if role_ids:
            staff_user_ids = session.execute(select(UserRole.user_id).where(UserRole.role_id.in_(role_ids))).scalars().all()
    if not staff_user_ids:
        staff_user_ids = all_user_ids[:]

    report_targets: dict[str, list[UUID]] = {
        "track": catalog_state["published_track_ids"] or catalog_state["created_track_ids"],
        "album": catalog_state["published_album_ids"] or catalog_state["created_album_ids"],
        "playlist": playlist_state["visible_playlist_ids"] or playlist_state["created_playlist_ids"],
        "comment": comment_ids,
    }
    report_count = max(1200, len(all_user_ids))
    report_rows = []
    for _ in range(report_count):
        target_type = _pick_weighted(rng, [("track", 0.45), ("album", 0.2), ("playlist", 0.15), ("comment", 0.2)])
        pool = report_targets[target_type]
        if not pool:
            continue
        report_rows.append(
            {
                "reporter_user_id": rng.choice(all_user_ids),
                "target_type": target_type,
                "target_id": rng.choice(pool),
                "reason": "Generated fixture report.",
                "status": _pick_weighted(
                    rng,
                    [("open", 0.35), ("in_review", 0.25), ("resolved", 0.25), ("rejected", 0.15)],
                ),
            }
        )

    created_reports = _bulk_insert(session, Report, report_rows, batch_size, return_model=Report)

    action_rows = []
    for report in created_reports:
        if report.status == "open":
            continue
        action_rows.append(
            {
                "actor_user_id": rng.choice(staff_user_ids),
                "target_type": "report",
                "target_id": report.id,
                "action": f"set_status_{report.status}",
                "metadata": {"source": "fixtures", "report_status": report.status},
            }
        )
    action_rows.extend(
        {
            "actor_user_id": rng.choice(staff_user_ids),
            "target_type": "track",
            "target_id": target_id,
            "action": "review_content",
            "metadata": {"source": "fixtures"},
        }
        for target_id in rng.sample(report_targets["track"], k=min(120, len(report_targets["track"])))
    )
    created_actions = _bulk_insert(session, ModerationAction, action_rows, batch_size)
    session.commit()
    return {"reports_created": len(created_reports), "actions_created": created_actions}


def _sync_social_counters(
    session: Session,
    track_ids: list[UUID],
    album_ids: list[UUID],
    playlist_ids: list[UUID],
) -> None:
    _sync_target_counter(session, Track, "track", track_ids)
    _sync_target_counter(session, Album, "album", album_ids)
    _sync_target_counter(session, Playlist, "playlist", playlist_ids)
    session.flush()


def _sync_target_counter(session: Session, model, target_type: str, ids: list[UUID]) -> None:
    if not ids:
        return
    likes_count: dict[UUID, int] = {}
    comments_count: dict[UUID, int] = {}
    for chunk_ids in _chunked(ids, 500):
        likes_rows = session.execute(
            select(Like.target_id, func.count())
            .where(Like.target_type == target_type, Like.target_id.in_(chunk_ids))
            .group_by(Like.target_id)
        ).all()
        comments_rows = session.execute(
            select(Comment.target_id, func.count())
            .where(Comment.target_type == target_type, Comment.target_id.in_(chunk_ids), Comment.status == "visible")
            .group_by(Comment.target_id)
        ).all()
        likes_count.update({target_id: count for target_id, count in likes_rows})
        comments_count.update({target_id: count for target_id, count in comments_rows})

    for target_id in ids:
        session.execute(
            update(model)
            .where(model.id == target_id)
            .values(
                likes_count=likes_count.get(target_id, 0),
                comments_count=comments_count.get(target_id, 0),
            )
        )


def _ensure_genres(session: Session) -> list[UUID]:
    existing_codes = set(session.execute(select(Genre.code)).scalars())
    missing_rows = [{"code": code, "name": name} for code, name in GENRE_PAIRS if code not in existing_codes]
    if missing_rows:
        session.execute(pg_insert(Genre), missing_rows)
        session.flush()
    return list(session.execute(select(Genre.id).order_by(Genre.code.asc())).scalars())


def _ensure_tags(session: Session) -> list[UUID]:
    existing_slugs = set(session.execute(select(Tag.slug)).scalars())
    missing_rows = [{"slug": slug, "name": name} for slug, name in TAG_PAIRS if slug not in existing_slugs]
    if missing_rows:
        session.execute(pg_insert(Tag), missing_rows)
        session.flush()
    return list(session.execute(select(Tag.id).order_by(Tag.slug.asc())).scalars())


def _bulk_insert(
    session: Session,
    model,
    rows: list[dict[str, Any]],
    batch_size: int,
    return_model=None,
):
    if not rows:
        return [] if return_model is not None else 0
    if return_model is None:
        inserted = 0
        for chunk in _chunked(rows, batch_size):
            session.execute(pg_insert(model), chunk)
            inserted += len(chunk)
        session.flush()
        return inserted

    records = []
    for chunk in _chunked(rows, batch_size):
        chunk_records = session.execute(pg_insert(model).returning(return_model), chunk).scalars().all()
        records.extend(chunk_records)
    session.flush()
    return records


def _bulk_insert_with_conflict(
    session: Session,
    model,
    rows: list[dict[str, Any]],
    batch_size: int,
    conflict_keys: list[str],
    return_model=None,
):
    if not rows:
        return [] if return_model is not None else 0

    if return_model is None:
        inserted = 0
        for chunk in _chunked(rows, batch_size):
            statement = pg_insert(model).values(chunk).on_conflict_do_nothing(index_elements=conflict_keys)
            result = session.execute(statement)
            inserted += result.rowcount or 0
        session.flush()
        return inserted

    records = []
    for chunk in _chunked(rows, batch_size):
        statement = (
            pg_insert(model)
            .values(chunk)
            .on_conflict_do_nothing(index_elements=conflict_keys)
            .returning(return_model)
        )
        records.extend(session.execute(statement).scalars().all())
    session.flush()
    return records


def _count_rows(session: Session, model) -> int:
    return int(session.execute(select(func.count()).select_from(model)).scalar_one() or 0)


def _count_group(session: Session, column) -> dict[str, int]:
    rows = session.execute(
        select(column, func.count())
        .group_by(column)
        .order_by(column.asc())
    ).all()
    return {str(key): int(count) for key, count in rows}


def _chunked(items: list[Any], chunk_size: int):
    for idx in range(0, len(items), chunk_size):
        yield items[idx : idx + chunk_size]


def _pick_weighted(rng: random.Random, choices: list[tuple[str, float]]) -> str:
    values = [value for value, _ in choices]
    weights = [weight for _, weight in choices]
    return rng.choices(values, weights=weights, k=1)[0]


def _library_section_for_target(target_type: str) -> str:
    if target_type == "track":
        return "favorites"
    if target_type == "album":
        return "albums"
    return "playlists"
