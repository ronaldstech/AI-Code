from fastapi import APIRouter, Header, HTTPException

from app.models.auth import Credentials
from app.services.auth import AuthService


router = APIRouter()
auth = AuthService()


@router.post("/auth/signup")
async def signup(credentials: Credentials):
    session, error = auth.signup(credentials.email, credentials.password)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return session


@router.post("/auth/login")
async def login(credentials: Credentials):
    session, error = auth.login(credentials.email, credentials.password)
    if error:
        raise HTTPException(status_code=401, detail=error)
    return session


@router.get("/auth/me")
async def me(authorization: str | None = Header(default=None)):
    user = auth.get_user(_token(authorization))
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return {"user": user}


@router.post("/auth/logout")
async def logout(authorization: str | None = Header(default=None)):
    auth.logout(_token(authorization))
    return {"success": True}


async def current_user(authorization: str | None = Header(default=None)):
    user = auth.get_user(_token(authorization))
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def _token(authorization):
    if not authorization or not authorization.lower().startswith("bearer "):
        return ""
    return authorization[7:].strip()
