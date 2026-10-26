from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.admin_access import router as admin_access_router
from app.api.v1.admin_pipeline import router as admin_pipeline_router
from app.api.v1.admin_system import router as admin_system_router
from app.api.v1.admin_tags import router as admin_tags_router
from app.api.v1.admin_users import router as admin_users_router
from app.api.v1.auth import router as auth_router
from app.api.v1.book_details import router as book_details_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.courses import router as courses_router
from app.api.v1.engagement import router as engagement_router
from app.api.v1.evaluations import router as evaluations_router
from app.api.v1.health import router as health_router
from app.api.v1.learning_paths import router as learning_paths_router
from app.api.v1.profile import router as profile_router
from app.api.v1.recommendations import router as recommendations_router
from app.api.v1.reservations import router as reservations_router
from app.core.config import get_settings
from app.core.errors import install_exception_handlers
from app.core.rate_limit import SlidingWindowRateLimiter, client_key, rule_for_request
from app.db.session import SessionLocal
from app.services.admin_seed import bootstrap_admin
from app.services.system_config_service import SystemConfigService


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    Path(settings.chroma_persist_directory).mkdir(parents=True, exist_ok=True)
    Path(settings.import_upload_directory).mkdir(parents=True, exist_ok=True)
    with SessionLocal() as session:
        bootstrap_admin(session, settings)
        SystemConfigService(session).get_ai_provider_status()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="BookPath AI API",
        version="2.0.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app_frontend_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-File-Name"],
    )
    install_exception_handlers(application)
    limiter = SlidingWindowRateLimiter()

    @application.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        rule = rule_for_request(request, settings)
        if rule is not None:
            allowed, retry_after = limiter.check(client_key(request, rule), rule.limit)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "请求过于频繁，请稍后重试",
                            "details": {"retry_after_seconds": retry_after},
                        },
                        "request_id": request_id,
                    },
                    headers={"Retry-After": str(retry_after), "X-Request-ID": request_id},
                )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(admin_access_router)
    application.include_router(conversations_router)
    application.include_router(recommendations_router)
    application.include_router(book_details_router)
    application.include_router(courses_router)
    application.include_router(profile_router)
    application.include_router(engagement_router)
    application.include_router(learning_paths_router)
    application.include_router(admin_pipeline_router)
    application.include_router(admin_tags_router)
    application.include_router(admin_users_router)
    application.include_router(reservations_router)
    application.include_router(admin_system_router)
    application.include_router(evaluations_router)
    return application


app = create_app()
