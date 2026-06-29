from dataclasses import dataclass
from enum import Enum
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.core.config import Settings, get_settings
from app.core.jwt_verify import verify_supabase_token
from app.core.supabase_client import get_supabase_admin


class UserRole(str, Enum):
    ADMIN = "admin"
    LOAN_OFFICER = "loan_officer"


@dataclass
class AuthUser:
    id: str
    email: str | None
    institution_id: str
    role: UserRole
    full_name: str | None


security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    settings: Settings = Depends(get_settings),
) -> AuthUser:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    token = credentials.credentials
    try:
        payload: dict[str, Any] = verify_supabase_token(token, settings)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except HTTPException:
        raise
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    sb = get_supabase_admin()
    profile_resp = (
        sb.table("profiles")
        .select("institution_id, role, full_name")
        .eq("id", user_id)
        .single()
        .execute()
    )
    if not profile_resp.data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User profile not found. Complete institution registration first.",
        )

    profile = profile_resp.data if isinstance(profile_resp.data, dict) else profile_resp.data[0]
    email = payload.get("email")

    return AuthUser(
        id=user_id,
        email=email,
        institution_id=profile["institution_id"],
        role=UserRole(profile["role"]),
        full_name=profile.get("full_name"),
    )


def require_admin(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    return user
