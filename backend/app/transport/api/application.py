from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ...service.errors import (Forbidden, InvalidInput, NotFound, OnboardingRequired,
                               ProviderUnavailable, ServiceError, Unauthorized)
from . import admin, auth, events, system, users

ERROR_CODES = {
    Unauthorized: 401, Forbidden: 403, NotFound: 404,
    OnboardingRequired: 409, InvalidInput: 422, ProviderUnavailable: 502,
}


async def service_error_handler(request: Request, error: ServiceError):
    return JSONResponse(status_code=ERROR_CODES.get(type(error), 500), content={'detail': str(error)})


def create_app(runtime):
    @asynccontextmanager
    async def lifespan(app):
        try:
            await runtime.startup()
            yield
        finally:
            await runtime.shutdown()

    app = FastAPI(title='Муршрут — персональная афиша', lifespan=lifespan)
    app.state.runtime = runtime
    app.add_exception_handler(ServiceError, service_error_handler)
    for router in (system.router, auth.router, users.router, events.router, admin.router):
        app.include_router(router)
    return app
