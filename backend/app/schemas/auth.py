from pydantic import ConfigDict, EmailStr, Field

from app.schemas.base import CamelModel


class RegisterRequest(CamelModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(CamelModel):
    username: str = Field(max_length=50)
    password: str = Field(max_length=128)
    remember_me: bool = False


class ForgotPasswordRequest(CamelModel):
    email: EmailStr


class ResetPasswordRequest(CamelModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class UserOut(CamelModel):
    id: int
    username: str
    email: str
    is_admin: bool

    model_config = ConfigDict(from_attributes=True)
