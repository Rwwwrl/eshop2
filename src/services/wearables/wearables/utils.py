from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def init_sqlmodel_engine(db_url: str) -> AsyncEngine:
    return create_async_engine(
        db_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_pre_ping=True,
        connect_args={
            "command_timeout": 15,
            # NOTE @sosov: Both caches must be disabled for transaction-mode poolers (PgCat/PgBouncer).
            # statement_cache_size=0 disables asyncpg's client-side named statement cache.
            # prepared_statement_cache_size=0 disables SQLAlchemy's prepared statement cache.
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        },
    )
