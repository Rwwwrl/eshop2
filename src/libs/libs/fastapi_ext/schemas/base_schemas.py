from libs.common.schemas.dto import DTO


class BaseRequestSchema(DTO):
    """Schema for what an API endpoint accepts as input.

    Example::

        class CreateUserPayload(BaseRequestSchema):
            name: str
            email: str

        @router.post("/users")
        async def create_user(payload: CreateUserPayload) -> ...:
            ...
    """


class BaseResponseSchema(DTO):
    """Schema for what an API endpoint returns to the client.

    Example::

        class UserResponseSchema(BaseResponseSchema):
            id: int
            name: str

        @router.get("/users/{user_id}", response_model=response_schemas.UserResponseSchema)
        async def get_user(user_id: int) -> response_schemas.UserResponseSchema:
            ...
    """
