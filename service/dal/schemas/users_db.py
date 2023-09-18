from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    user_id: str  # primary key

    @field_validator('user_id')
    def valid_uuid(cls, v):
        try:
            UUID(v, version=4)
        except Exception as exc:
            raise ValueError(str(exc))
        return v


class UserEntry(UserBase):
    user_name: Annotated[str, Field(min_length=1, max_length=20)]
    email: EmailStr
