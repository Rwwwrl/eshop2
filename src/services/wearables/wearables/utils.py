from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def init_sqlmodel_engine(db_url: str) -> AsyncEngine:
    return create_async_engine(
        db_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        connect_args={
            "command_timeout": 15,
            # NOTE @sosov: Required when using a connection pooler in transaction mode — prepared statements
            # break across pooled connections because each transaction may use a different backend connection.
            "statement_cache_size": 0,
        },
    )
