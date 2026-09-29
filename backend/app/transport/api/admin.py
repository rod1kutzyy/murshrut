from fastapi import APIRouter, Depends, Query, Security

from ...service.facade import Services
from ..mappers import sync_to_response
from .dependencies import admin_token, get_services
from .openapi import error_responses
from .schemas import SyncOut

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post(
    "/events/sync",
    response_model=SyncOut,
    summary="Принудительно синхронизировать события",
    description="Обновляет события выбранного города, игнорируя обычный интервал синхронизации.",
    responses=error_responses(403, 422, 502),
)
async def admin_sync(
    city: str = Query(
        "Москва",
        min_length=2,
        max_length=200,
        description="Город для принудительного обновления.",
    ),
    x_admin_token: str | None = Security(admin_token),
    services: Services = Depends(get_services),
):
    return sync_to_response(await services.system.admin_sync(city, x_admin_token or ""))
