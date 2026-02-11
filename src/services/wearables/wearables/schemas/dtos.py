from datetime import datetime
from typing import Self

from libs.common.schemas.dto import DTO

from wearables.models import WearableEvent


class BaseWearableEventDTO(DTO):
    id: int | None
    user_id: int
    biomarker_name: str
    value: float
    timestamp: datetime

    @classmethod
    def from_sqlmodel(cls, model: WearableEvent) -> Self:
        return cls(**model.model_dump())
