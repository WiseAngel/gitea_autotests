"""
Database engine and session management.

Provides async database connection pool using SQLAlchemy 2.x + asyncpg.
Supports transaction isolation with auto-rollback for test isolation.
"""

from collections.abc import AsyncGenerator, Callable
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.config.settings import settings


class DatabaseEngine:
    """
    Async database engine manager with connection pooling.

    Usage:
        db = DatabaseEngine()
        await db.connect()
        async with db.session() as session:
            # use session
        await db.disconnect()
    """

    def __init__(self, url: str | None = None):
        """
        Initialize database engine.

        Args:
            url: Override default database URL from settings
        """
        self.url = url or settings.db_url
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def engine(self) -> AsyncEngine:
        """Get or create async engine."""
        if self._engine is None:
            self._engine = create_async_engine(
                self.url,
                poolclass=NullPool,  # Use NullPool for tests to avoid connection leaks
                echo=False,
            )
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get or create session factory."""
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
        return self._session_factory

    async def connect(self) -> None:
        """Initialize engine connection."""
        if self._engine is None:
            _ = self.engine  # Create engine on first access

    async def disconnect(self) -> None:
        """Close engine connections."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Create async session context manager.

        Yields:
            AsyncSession instance for database operations

        Example:
            async with db.session() as session:
                result = await session.execute(query)
        """
        return self.session_factory()  # type: ignore[return-value]

    async def execute_transaction(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Execute function within a database transaction with auto-rollback.

        Useful for test isolation - all changes are rolled back after execution.

        Args:
            func: Async function to execute (receives session as first arg)
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from func execution
        """
        async with self.session_factory() as session:
            try:
                result = await func(session, *args, **kwargs)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise


# Global database instance
db = DatabaseEngine()
