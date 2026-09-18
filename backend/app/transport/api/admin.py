from fastapi import APIRouter, Depends, Header, Query

from ...service.facade import Services
from ..mappers import sync_to_response
from .dependencies import get_services
from .schemas import SyncOut

router = APIRouter(prefix='/api/admin')


@router.post('/events/sync', response_model=SyncOut)
async def admin_sync(city: str = Query('Москва', min_length=2, max_length=200),
                     x_admin_token: str = Header(''), services: Services = Depends(get_services)):
    return sync_to_response(await services.system.admin_sync(city, x_admin_token))
