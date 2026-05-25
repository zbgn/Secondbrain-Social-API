from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Post, User
from app.schemas import PostCreate, UserCreate
from app.security import hash_password, verify_password


async def create_user(db: AsyncSession, payload: UserCreate) -> User:
    existing = await db.scalar(
        select(User).where(or_(User.username == payload.username, User.email == payload.email))
    )
    if existing:
        raise HTTPException(status_code=409, detail="Username or email already registered")

    user = User(
        username=payload.username,
        email=str(payload.email),
        password_hash=hash_password(payload.password.get_secret_value()),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    user = await db.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


async def create_post(db: AsyncSession, author: User, payload: PostCreate) -> Post:
    post = Post(content=payload.content, author=author)
    db.add(post)
    await db.commit()
    saved_post = await db.scalar(
        select(Post).options(selectinload(Post.author)).where(Post.id == post.id)
    )
    if saved_post is None:
        raise HTTPException(status_code=500, detail="Post could not be created")
    return saved_post


async def get_feed(db: AsyncSession, user: User, limit: int, offset: int) -> list[Post]:
    author_ids = [user.id, *(followed.id for followed in user.following)]
    return list(
        await db.scalars(
            select(Post)
            .options(selectinload(Post.author))
            .where(Post.author_id.in_(author_ids))
            .order_by(Post.created_at.desc(), Post.id.desc())
            .limit(limit)
            .offset(offset)
        )
    )


async def follow_user(db: AsyncSession, current_user: User, username: str) -> User:
    user_to_follow = await db.scalar(select(User).where(User.username == username))
    if user_to_follow is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user_to_follow.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    if user_to_follow in current_user.following:
        raise HTTPException(status_code=409, detail="Already following user")

    current_user.following.append(user_to_follow)
    await db.commit()
    return user_to_follow


async def unfollow_user(db: AsyncSession, current_user: User, username: str) -> None:
    user_to_unfollow = await db.scalar(select(User).where(User.username == username))
    if user_to_unfollow is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user_to_unfollow not in current_user.following:
        raise HTTPException(status_code=404, detail="Not following user")

    current_user.following.remove(user_to_unfollow)
    await db.commit()
