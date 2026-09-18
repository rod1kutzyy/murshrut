from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ...service.facade import Services

bearer = HTTPBearer(auto_error=False)


async def get_services(request: Request):
    async with request.app.state.runtime.services() as services:
        yield services


async def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
                       services: Services = Depends(get_services)):
    return await services.auth.current_user(credentials.credentials if credentials else None)
