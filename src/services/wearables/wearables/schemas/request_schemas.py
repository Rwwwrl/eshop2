from typing import Any

from libs.fastapi_ext.schemas.base_schemas import BaseRequestSchema


class JunctionWebhookPayload(BaseRequestSchema):
    event_type: str
    client_user_id: str
    user_id: str
    data: dict[str, Any]
