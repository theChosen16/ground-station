# Copyright (c) 2025 Efstratios Goudelis
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.


import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from common.arguments import arguments
from typing import Any


def _build_database_url(db_path: str) -> str:
    """Build an async database URL.

    Priority:
      1. DATABASE_URL env var (set by Railway when PostgreSQL is linked)
      2. SQLite path from CLI arguments (local development)
    """
    env_url = os.environ.get("DATABASE_URL")
    if env_url:
        # Railway provides postgresql:// — convert to async driver
        if env_url.startswith("postgresql://"):
            return env_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if env_url.startswith("postgres://"):
            return env_url.replace("postgres://", "postgresql+asyncpg://", 1)
        # Already an async URL or other dialect
        return env_url

    # Fallback: local SQLite
    if os.path.isabs(db_path):
        return f"sqlite+aiosqlite:///{os.path.abspath(db_path)}"
    # The db path from arguments already includes data/db/ prefix
    return f"sqlite+aiosqlite:///./{db_path}"


DATABASE_URL = _build_database_url(arguments.db)
_is_sqlite = DATABASE_URL.startswith("sqlite")

_engine_kwargs: dict[str, Any] = dict(
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
)
if _is_sqlite:
    _engine_kwargs["connect_args"] = {
        "check_same_thread": False,
        "timeout": 30,  # 30 second timeout for database locks
    }

engine = create_async_engine(DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


def create_subprocess_engine():
    """
    Create a new database engine specifically for subprocess use.

    This is necessary because database engines cannot be safely shared across
    process boundaries (e.g., in multiprocessing scenarios). Each subprocess
    should create its own engine to avoid connection pool conflicts.

    Returns:
        A new AsyncEngine instance with the same configuration as the main engine
    """
    kwargs: dict[str, Any] = dict(
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_recycle=3600,
    )
    if _is_sqlite:
        kwargs["connect_args"] = {
            "check_same_thread": False,
            "timeout": 30,
        }
    return create_async_engine(DATABASE_URL, **kwargs)
