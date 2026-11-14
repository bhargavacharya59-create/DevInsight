"""SQLAlchemy async engine and session factory."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


class Base(DeclarativeBase):
    pass


# SQLite uses NullPool by default and does not accept QueuePool sizing options.
# Keep the larger pool only for database drivers that support it (e.g. PostgreSQL).
engine_options = {"echo": False}
if not settings.DATABASE_URL.startswith("sqlite"):
    engine_options.update(
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )

engine = create_async_engine(settings.DATABASE_URL, **engine_options)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """Create all tables (used in development / tests)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
