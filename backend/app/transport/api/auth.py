from fastapi import APIRouter, Depends

from ...service.facade import Services
from ..mappers import auth_to_response
from .dependencies import get_services
from .schemas import AuthInput, AuthOut

router = APIRouter(prefix='/api/v1/auth')


@router.post('/max', response_model=AuthOut)
async def auth(body: AuthInput, services: Services = Depends(get_services)):
    return auth_to_response(await services.auth.max(body.init_data))


@router.post('/demo', response_model=AuthOut)
async def demo_auth(services: Services = Depends(get_services)):
    return auth_to_response(await services.auth.demo())
