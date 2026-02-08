from libs.alembic_ext.env_helpers import run_async_alembic
from libs.sqlmodel_ext import BaseSqlModel
from wearables.settings import settings

run_async_alembic(settings_url=settings.postgres_db_url, target_metadata=BaseSqlModel.metadata)
