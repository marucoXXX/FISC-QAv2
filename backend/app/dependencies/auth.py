import base64
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings
from app.schemas.user import User

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証が必要です"
        )

    try:
        # トークンからメールアドレスをデコード
        email = base64.b64decode(credentials.credentials).decode()

        # ALLOWED_EMAILSで再検証
        allowed = settings.get_allowed_emails_list()
        if allowed and email.lower() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="このメールアドレスはログインが許可されていません"
            )

        return User(
            id=email,
            email=email,
            first_name=email.split("@")[0],
            last_name=""
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なトークンです"
        )
