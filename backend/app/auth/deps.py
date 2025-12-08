from fastapi import Depends, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError


security = HTTPBearer(auto_error=False)


def get_current_tenant(creds: HTTPAuthorizationCredentials | None = Security(security)) -> str:
    if creds is None:
        raise UnauthorizedError(detail="Authorization header missing")

    token = creds.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise UnauthorizedError(detail="Invalid token")

    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise UnauthorizedError(detail="tenant_id missing in token")

    return str(tenant_id)
