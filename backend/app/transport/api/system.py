from fastapi import APIRouter, Depends

from ...service.entities import User
from ...service.facade import Services
from ..mappers import category_to_response, configuration_to_response, health_to_response
from .dependencies import current_user, get_services
from .schemas import CategoryOut, ConfigOut, HealthOut

router = APIRouter()


@router.get('/api/health', response_model=HealthOut)
async def health(services: Services = Depends(get_services)):
    return health_to_response(await services.system.health())


@router.get('/api/v1/config', response_model=ConfigOut)
async def config(services: Services = Depends(get_services)):
    return configuration_to_response(services.system.configuration())


@router.get('/api/v1/categories', response_model=list[CategoryOut])
async def categories(user: User = Depends(current_user), services: Services = Depends(get_services)):
    return [category_to_response(category) for category in await services.system.categories()]
