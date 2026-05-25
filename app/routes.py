from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas import (
    LoginRequest,
    PostCreate,
    PostRead,
    TokenResponse,
    UserCreate,
    UserRead,
)
from app.security import create_access_token, get_current_user
from app.services import (
    authenticate_user,
    create_post,
    create_user,
    follow_user,
    get_feed,
    unfollow_user,
)

router = APIRouter()


@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Users"],
)
async def register_user(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    return await create_user(db, payload)


@router.post("/login", response_model=TokenResponse, tags=["Auth"])
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = await authenticate_user(db, payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return TokenResponse(access_token=create_access_token(user))


@router.post(
    "/posts",
    response_model=PostRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Posts"],
)
async def add_post(
    payload: PostCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_post(db, current_user, payload)


@router.get("/posts", response_model=list[PostRead], tags=["Posts"])
async def list_posts(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_feed(db, current_user, limit, offset)


@router.post("/users/follow/{username}", response_model=UserRead, tags=["Follows"])
async def follow(
    username: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await follow_user(db, current_user, username)


@router.delete(
    "/users/follow/{username}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Follows"],
)
async def unfollow(
    username: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await unfollow_user(db, current_user, username)
