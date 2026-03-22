from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from common.dependencies import get_db, get_current_user
from app.api.auth.schemas import LoginRequest, RegisterRequest, UserResponse, TokenResponse
from app.api.auth.service import AuthService
from common.models.user import User

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await AuthService.login(db, data)

@router.post("/register", response_model=UserResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    return await AuthService.register(db, data)

@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return UserResponse.from_user(current_user)

@router.post("/refresh", response_model=TokenResponse)
async def refresh(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await AuthService.refresh_token(current_user)
