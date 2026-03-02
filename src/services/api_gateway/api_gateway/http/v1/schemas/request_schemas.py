from libs.fastapi_ext.schemas.base_schemas import BaseRequestSchema


class OpenHealthResultWebhookPayload(BaseRequestSchema):
    result_id: int
