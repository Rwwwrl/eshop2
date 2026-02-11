from datetime import datetime

from libs.fastapi_ext.schemas.base_schemas import BaseRequestSchema


class WebhookEventPayload(BaseRequestSchema):
    user_id: int
    biomarker_name: str
    value: float
    timestamp: datetime
