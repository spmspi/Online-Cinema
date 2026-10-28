from fastapi import Depends

from src.security.interface_token import JWTAuthManagerInterface
from src.security.token_manager import JWTAuthManager
from src.settings import Settings, get_settings


def get_jwt_auth_manager(settings: Settings = Depends(get_settings)) -> JWTAuthManagerInterface:

    return JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM
    )
