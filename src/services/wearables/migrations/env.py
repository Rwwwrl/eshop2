import libs.faststream_ext.models  # noqa: F401
import libs.taskiq_ext.models  # noqa: F401
import wearables.models  # noqa: F401
from libs.alembic_ext.env_helpers import run_alembic
from libs.sqlmodel_ext import BaseSqlModel
from wearables.settings import settings

run_alembic(settings_url=settings.postgres_direct_db_url, target_metadata=BaseSqlModel.metadata)
