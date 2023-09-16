from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, PositiveInt, field_validator


class CreateOrderRequest(BaseModel):
    customer_name: Annotated[str, Field(min_length=1, max_length=20)]
    order_item_count: PositiveInt

class DeleteOrderRequest(BaseModel):
    order_id: str

    @field_validator('order_id')
    def valid_uuid(cls, v):
        try:
            UUID(v, version=4)
        except Exception as exc:
            raise ValueError(str(exc))
        return v

class GetOrderRequest(DeleteOrderRequest):
    ... # pragma: no cover
