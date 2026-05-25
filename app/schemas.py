import string
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr
    password: SecretStr = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, password: SecretStr) -> SecretStr:
        value = password.get_secret_value()
        if not any(char.isupper() for char in value):
            raise ValueError("Password must include an uppercase letter")
        if not any(char.islower() for char in value):
            raise ValueError("Password must include a lowercase letter")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must include a number")
        if not any(char in string.punctuation for char in value):
            raise ValueError("Password must include a special character")
        return password


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    created_at: datetime


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PostCreate(BaseModel):
    content: str = Field(min_length=1, max_length=280)


class PostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    created_at: datetime
    author: UserRead
