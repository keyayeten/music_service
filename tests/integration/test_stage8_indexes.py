import pytest
from sqlalchemy import text


def _index_definition(db_session, table_name: str, index_name: str) -> str | None:
    return db_session.execute(
        text(
            """
            SELECT indexdef
            FROM pg_indexes
            WHERE schemaname = current_schema()
              AND tablename = :table_name
              AND indexname = :index_name
            """
        ),
        {"table_name": table_name, "index_name": index_name},
    ).scalar_one_or_none()


@pytest.mark.integration
def test_stage8_indexes_and_trgm_extension_exist(db_session) -> None:
    trgm_exists = db_session.execute(
        text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm')")
    ).scalar_one()
    assert trgm_exists is True

    users_index = _index_definition(db_session, "users", "ix_users_status_created_at")
    assert users_index is not None

    playlists_index = _index_definition(db_session, "playlists", "ix_playlists_visibility_created")
    assert playlists_index is not None

    comments_partial_index = _index_definition(db_session, "comments", "ix_comments_visible_target_created")
    assert comments_partial_index is not None
    assert "WHERE ((status)::text = 'visible'::text)" in comments_partial_index

    track_trgm_index = _index_definition(db_session, "tracks", "ix_tracks_title_trgm")
    assert track_trgm_index is not None
    assert "gin_trgm_ops" in track_trgm_index

    composer_trgm_index = _index_definition(db_session, "composer_profiles", "ix_composer_profiles_display_name_trgm")
    assert composer_trgm_index is not None
    assert "gin_trgm_ops" in composer_trgm_index
