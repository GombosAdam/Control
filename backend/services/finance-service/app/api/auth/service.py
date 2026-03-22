from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from common.models.user import User, UserRole
from common.utils.security import hash_password, verify_password, create_access_token
from common.exceptions import AuthenticationError, DuplicateError, ValidationError
from app.api.auth.schemas import LoginRequest, RegisterRequest, UserResponse, TokenResponse

class AuthService:
    @staticmethod
    async def login(db: AsyncSession, data: LoginRequest) -> TokenResponse:
        result = await db.execute(select(User).where(User.email == data.email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(data.password, user.password_hash):
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("Account is disabled")

        user.last_login = datetime.utcnow()
        await db.commit()

        token = create_access_token({"sub": user.id, "role": user.role.value})
        return TokenResponse(token=token, user=UserResponse.from_user(user))

    @staticmethod
    async def register(db: AsyncSession, data: RegisterRequest) -> UserResponse:
        result = await db.execute(select(User).where(User.email == data.email))
        if result.scalar_one_or_none():
            raise DuplicateError("email", data.email)

        try:
            role = UserRole(data.role)
        except ValueError:
            raise ValidationError(f"Invalid role: {data.role}")

        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            role=role,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        return UserResponse.from_user(user)

    @staticmethod
    async def refresh_token(user: User) -> TokenResponse:
        token = create_access_token({"sub": user.id, "role": user.role.value})
        return TokenResponse(token=token, user=UserResponse.from_user(user))
