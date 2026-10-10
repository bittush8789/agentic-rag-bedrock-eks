import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import setup_logging, logger, correlation_id_ctx
from app.db.session import init_db
from app.api.v1.router import api_v1_router
from app.api.v1.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging(settings.LOG_LEVEL)
    logger.info("Starting Enterprise Agentic RAG Application on AWS EKS...")
    await init_db()
    yield
    # Shutdown
    logger.info("Shutting down Agentic RAG Application...")


app = FastAPI(
    title="Production-Ready Agentic RAG Platform",
    description="Multi-tenant Agentic Document Intelligence on AWS EKS with Bedrock and pgvector",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """
    Attaches correlation ID to every incoming request for distributed trace tracking.
    """
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    token = correlation_id_ctx.set(req_id)
    start_time = time.time()

    try:
        response: Response = await call_next(request)
        duration_ms = int((time.time() - start_time) * 1000)
        response.headers["X-Request-ID"] = req_id

        # Skip logging high-frequency health probes
        if not request.url.path.endswith(("/health", "/ready")):
            logger.info(
                f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms)"
            )
        return response
    except Exception as exc:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc} ({duration_ms}ms)")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "detail": "An unexpected server error occurred. Please contact system administrator.",
                "correlation_id": req_id
            },
            headers={"X-Request-ID": req_id}
        )
    finally:
        correlation_id_ctx.reset(token)


# Exception handler for HTTPException
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    req_id = correlation_id_ctx.get() or "unknown"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HttpException",
            "detail": exc.detail,
            "correlation_id": req_id
        },
        headers={"X-Request-ID": req_id}
    )


# Root level health probes for Kubernetes
app.include_router(health_router)

# Mount API v1 router
app.include_router(api_v1_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
