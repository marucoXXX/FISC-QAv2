from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.config import settings
from app.dependencies.auth import get_current_user
from app.schemas.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str


class LoginResponse(BaseModel):
    user: User
    token: str


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, response: Response):
    email = request.email.lower()
    allowed = settings.get_allowed_emails_list()

    # ALLOWED_EMAILSが空の場合は全員許可（開発用）
    if allowed and email not in allowed:
        raise HTTPException(status_code=403, detail="このメールアドレスはログインが許可されていません")

    # 簡易トークン（メールアドレスをBase64エンコード）
    import base64
    token = base64.b64encode(email.encode()).decode()

    user = User(
        id=email,
        email=email,
        first_name=email.split("@")[0],
        last_name=""
    )

    return LoginResponse(user=user, token=token)


@router.get("/me", response_model=User)
async def get_me(user: User = Depends(get_current_user)):
    return user
