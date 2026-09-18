from fastapi import APIRouter, Depends

from ...service.entities import User
from ...service.facade import Services
from ..mappers import preferences_to_command, preferences_to_response, user_to_response
from .dependencies import current_user, get_services
from .schemas import PreferencesInput, PreferencesOut, UserOut

router = APIRouter(prefix='/api/v1/users/me')


@router.get('', response_model=UserOut)
async def me(user: User = Depends(current_user)):
    return user_to_response(user)


@router.get('/preferences', response_model=PreferencesOut | None)
async def preferences(user: User = Depends(current_user), services: Services = Depends(get_services)):
    result = await services.preferences.get(user)
    return preferences_to_response(result) if result else None


@router.put('/preferences', response_model=UserOut)
async def save_preferences(body: PreferencesInput, user: User = Depends(current_user),
                           services: Services = Depends(get_services)):
    return user_to_response(await services.preferences.save(user, preferences_to_command(body)))
