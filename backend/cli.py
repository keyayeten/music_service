import asyncio
from contextlib import asynccontextmanager
import json
from typing import Annotated

import typer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.identity.security import hash_password
from backend.application.identity.use_cases.auth import IdentityAuthUseCases
from backend.config.settings import get_settings
from backend.domain.common.exceptions import ValidationError
from backend.infrastructure.persistence.database import get_session, init_database
from backend.infrastructure.persistence.models.identity import User
from backend.infrastructure.persistence.repositories.identity_auth import SqlAlchemyIdentityAuthRepository
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


@app.command("create-superuser")
def create_superuser(
    email: Annotated[str | None, typer.Option("--email", "-e", help="Superuser email.")] = None,
    username: Annotated[str | None, typer.Option("--username", "-u", help="Superuser username.")] = None,
    password: Annotated[str | None, typer.Option("--password", "-p", help="Password (min 8 chars).")] = None,
    no_input: Annotated[
        bool,
        typer.Option("--no-input", help="Fail if email/username/password are not passed (non-interactive)."),
    ] = False,
) -> None:
    """Create a new user with is_superuser=True and admin role (Django createsuperuser)."""
    resolved_email, resolved_username, resolved_password = _resolve_superuser_credentials(
        email=email,
        username=username,
        password=password,
        no_input=no_input,
    )
    asyncio.run(
        _create_superuser_async(
            email=resolved_email,
            username=resolved_username,
            password=resolved_password,
        )
    )


@app.command("promote-superuser")
def promote_superuser(
    email: str = typer.Option(..., "--email", "-e", help="Email of the user to promote."),
) -> None:
    """Grant is_superuser=True for an existing user (admin panel access)."""
    asyncio.run(_promote_superuser_async(email.strip().lower()))


def _resolve_superuser_credentials(
    *,
    email: str | None,
    username: str | None,
    password: str | None,
    no_input: bool,
) -> tuple[str, str, str]:
    if no_input and (not email or not username or not password):
        typer.echo("With --no-input you must pass --email, --username and --password.", err=True)
        raise typer.Exit(code=1)

    resolved_email = (email or "").strip().lower()
    if not resolved_email:
        resolved_email = typer.prompt("Email").strip().lower()

    resolved_username = (username or "").strip()
    if not resolved_username:
        resolved_username = typer.prompt("Username").strip()

    resolved_password = password or ""
    if not resolved_password:
        while True:
            resolved_password = typer.prompt("Password", hide_input=True)
            confirm = typer.prompt("Password (again)", hide_input=True)
            if resolved_password == confirm:
                break
            typer.echo("Passwords do not match. Try again.", err=True)

    try:
        IdentityAuthUseCases._validate_signup_fields(resolved_email, resolved_username, resolved_password)
    except ValidationError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    return resolved_email, resolved_username, resolved_password


async def _create_superuser_async(*, email: str, username: str, password: str) -> None:
    init_database()
    async with _session_scope() as session:
        repository = SqlAlchemyIdentityAuthRepository(session)
        if await repository.get_user_by_email(email):
            typer.echo(f"User with email {email} already exists.", err=True)
            raise typer.Exit(code=1)
        if await repository.get_user_by_username(username):
            typer.echo(f"User with username {username} already exists.", err=True)
            raise typer.Exit(code=1)

        await repository.ensure_roles_seeded()
        user = User(
            email=email,
            username=username,
            password_hash=hash_password(password),
            is_superuser=True,
            status="active",
        )
        session.add(user)
        await session.flush()

        for role_code in ("user", "admin"):
            role_id = await repository.get_role_id_by_code(role_code)
            if role_id is None:
                typer.echo(f"Role {role_code!r} is not configured.", err=True)
                raise typer.Exit(code=1)
            await repository.assign_role(user.id, role_id)

        await session.commit()
        typer.echo(f"Superuser created: email={email} username={username} id={user.id}")


async def _promote_superuser_async(email: str) -> None:
    init_database()
    async with _session_scope() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if user is None:
            typer.echo(f"User not found: {email}", err=True)
            raise typer.Exit(code=1)
        if user.is_superuser:
            typer.echo(f"User {email} is already a superuser (id={user.id}).")
            return
        user.is_superuser = True
        await session.commit()
        typer.echo(f"Promoted {email} to superuser (id={user.id}).")


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
