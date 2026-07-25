from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from server.domain.user import User
from server.core.security import create_access_token
from server.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    display_name: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    user = await User.get_by_username(req.username)
    if not user or not await user.verify_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token({"sub": user.id})
    return TokenResponse(
        access_token=token,
        user={"id": user.id, "username": user.username, "email": user.email, "display_name": user.display_name, "role": user.role}
    )


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    existing = await User.get_by_username(req.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    user = await User.create(username=req.username, email=req.email, password=req.password, display_name=req.display_name)
    token = create_access_token({"sub": user.id})
    return TokenResponse(
        access_token=token,
        user={"id": user.id, "username": user.username, "email": user.email, "display_name": user.display_name, "role": user.role}
    )


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username, "email": current_user.email, "display_name": current_user.display_name, "role": current_user.role}
