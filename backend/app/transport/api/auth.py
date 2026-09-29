from fastapi import APIRouter, Depends

from ...service.facade import Services
from ..mappers import auth_to_response
from .dependencies import get_services
from .openapi import error_responses
from .schemas import AuthInput, AuthOut

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/max",
    response_model=AuthOut,
    summary="Войти через MAX",
    description="Проверяет подпись и срок действия initData и возвращает JWT на 24 часа.",
    responses=error_responses(401, 422),
)
async def auth(body: AuthInput, services: Services = Depends(get_services)):
    return auth_to_response(await services.auth.max(body.init_data))


@router.post(
    "/demo",
    response_model=AuthOut,
    summary="Войти в демонстрационный профиль",
    description="Доступно только при включённом DEMO_MODE.",
    responses=error_responses(404),
)
async def demo_auth(services: Services = Depends(get_services)):
    return auth_to_response(await services.auth.demo())
