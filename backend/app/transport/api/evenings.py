from uuid import UUID
from fastapi import APIRouter, Depends

from ...service.entities import User
from ...service.facade import Services
from ..mappers import evening_to_query, evening_to_response
from .dependencies import current_user, get_services
from .openapi import error_responses
from .schemas import EveningInput, EveningOut, EveningGenerationOut

router = APIRouter(prefix="/api/v1/evenings", tags=["evenings"])


async def response(plan, services):
    return evening_to_response(plan, await services.evenings.warnings(plan))


@router.post(
    "/generate",
    response_model=EveningGenerationOut,
    summary="Сгенерировать план вечера",
    description="Подбирает новый выполнимый маршрут из двух или трёх событий.",
    responses=error_responses(401, 404, 409, 422, 502),
)
async def generate(
    body: EveningInput,
    user: User = Depends(current_user),
    services: Services = Depends(get_services),
):
    plan, reason = await services.evenings.generate(
        user,
        evening_to_query(body),
    )
    return EveningGenerationOut(
        plan=await response(plan, services) if plan else None, reason=reason
    )


@router.get(
    "",
    response_model=list[EveningOut],
    summary="Получить сохранённые планы",
    responses=error_responses(401),
)
async def saved(
    user: User = Depends(current_user), services: Services = Depends(get_services)
):
    return [
        await response(plan, services) for plan in await services.evenings.saved(user)
    ]


@router.get(
    "/{plan_id}",
    response_model=EveningOut,
    summary="Получить план вечера",
    responses=error_responses(401, 404, 422),
)
async def get(
    plan_id: UUID,
    user: User = Depends(current_user),
    services: Services = Depends(get_services),
):
    return await response(await services.evenings.get(user, plan_id), services)


@router.post(
    "/{plan_id}/save",
    response_model=EveningOut,
    summary="Сохранить план вечера",
    responses=error_responses(401, 404, 422),
)
async def save(
    plan_id: UUID,
    user: User = Depends(current_user),
    services: Services = Depends(get_services),
):
    return await response(await services.evenings.save(user, plan_id), services)


@router.delete(
    "/{plan_id}",
    status_code=204,
    summary="Удалить сохранённый план",
    responses=error_responses(401, 404, 422),
)
async def delete(
    plan_id: UUID,
    user: User = Depends(current_user),
    services: Services = Depends(get_services),
):
    await services.evenings.delete(user, plan_id)
