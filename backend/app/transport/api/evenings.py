from uuid import UUID
from fastapi import APIRouter, Depends

from ...service.commands import EveningQuery
from ...service.entities import User
from ...service.facade import Services
from .dependencies import current_user, get_services
from .schemas import EveningInput, EveningOut, EveningGenerationOut

router = APIRouter(prefix="/api/v1/evenings", tags=["evenings"])


async def response(plan, services):
    return EveningOut(
        **plan.snapshot,
        id=plan.id,
        saved=plan.saved,
        created_at=plan.created_at,
        warnings=await services.evenings.warnings(plan),
    )


@router.post("/generate", response_model=EveningGenerationOut)
async def generate(
    body: EveningInput,
    user: User = Depends(current_user),
    services: Services = Depends(get_services),
):
    plan, reason = await services.evenings.generate(
        user,
        EveningQuery(
            body.vibe,
            body.duration_hours,
            body.budget_max,
            tuple(body.excluded_plan_ids),
        ),
    )
    return EveningGenerationOut(
        plan=await response(plan, services) if plan else None, reason=reason
    )


@router.get("", response_model=list[EveningOut])
async def saved(
    user: User = Depends(current_user), services: Services = Depends(get_services)
):
    return [
        await response(plan, services) for plan in await services.evenings.saved(user)
    ]


@router.get("/{plan_id}", response_model=EveningOut)
async def get(
    plan_id: UUID,
    user: User = Depends(current_user),
    services: Services = Depends(get_services),
):
    return await response(await services.evenings.get(user, plan_id), services)


@router.post("/{plan_id}/save", response_model=EveningOut)
async def save(
    plan_id: UUID,
    user: User = Depends(current_user),
    services: Services = Depends(get_services),
):
    return await response(await services.evenings.save(user, plan_id), services)
