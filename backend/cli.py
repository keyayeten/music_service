import asyncio
from contextlib import asynccontextmanager
import json

import typer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import get_settings
from backend.infrastructure.persistence.database import get_session, init_database
from backend.infrastructure.persistence.seeds.fixtures import FixtureSeedOptions, collect_fixture_stats, seed_fixtures

app = typer.Typer(help="CLI utilities for music_service.")
fixtures_app = typer.Typer(help="Fixtures generation and inspection commands.")


@app.callback()
def main() -> None:
    """Entry point for CLI commands."""


@app.command("hello")
def hello(
    name: str = typer.Option("Developer", "--name", "-n", help="Name for greeting."),
) -> None:
    """Print a greeting with project context."""
    settings = get_settings()
    typer.echo(f"Hello, {name}! Welcome to {settings.app_name}.")


@fixtures_app.command("seed")
def fixtures_seed(
    users: int = typer.Option(1000, help="Number of users to generate."),
    tracks: int = typer.Option(10000, help="Number of tracks to generate."),
    albums: int = typer.Option(100, help="Number of albums to generate."),
    playlists: int = typer.Option(1000, help="Number of playlists to generate."),
    batch_size: int = typer.Option(500, help="Bulk insert chunk size."),
) -> None:
    """Generate large append-only fixtures for all project stages."""
    asyncio.run(
        _fixtures_seed_async(
            users=users,
            tracks=tracks,
            albums=albums,
            playlists=playlists,
            batch_size=batch_size,
        )
    )


@fixtures_app.command("stats")
def fixtures_stats() -> None:
    """Print fixture-related aggregate statistics."""
    asyncio.run(_fixtures_stats_async())


@asynccontextmanager
async def _session_scope():
    session_gen = get_session()
    session: AsyncSession = await anext(session_gen)
    try:
        yield session
    finally:
        await session_gen.aclose()


async def _fixtures_seed_async(*, users: int, tracks: int, albums: int, playlists: int, batch_size: int) -> None:
    init_database()
    options = FixtureSeedOptions(
        users=users,
        tracks=tracks,
        albums=albums,
        playlists=playlists,
        batch_size=batch_size,
    )
    async with _session_scope() as session:
        result = await session.run_sync(lambda sync_session: seed_fixtures(sync_session, options))
        typer.echo(
            json.dumps(
                {
                    "users_created": result.users_created,
                    "tracks_created": result.tracks_created,
                    "albums_created": result.albums_created,
                    "playlists_created": result.playlists_created,
                    "likes_created": result.likes_created,
                    "comments_created": result.comments_created,
                    "events_created": result.events_created,
                    "reports_created": result.reports_created,
                    "moderation_actions_created": result.moderation_actions_created,
                },
                ensure_ascii=False,
                indent=2,
            )
        )


async def _fixtures_stats_async() -> None:
    init_database()
    async with _session_scope() as session:
        stats = await session.run_sync(collect_fixture_stats)
        typer.echo(json.dumps(stats, ensure_ascii=False, indent=2))


app.add_typer(fixtures_app, name="fixtures")


if __name__ == "__main__":
    app()
