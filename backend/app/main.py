from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings
from app.db.base import Base, engine
from app.routers import auth, donations, donors, meetings, ngo_settings, receipts

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="SVMSS Donation Receipt Generator API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": {"code": "validation_error", "message": exc.errors()}})


@app.on_event("startup")
def on_startup() -> None:
    # For local/dev convenience; production applies migrations via `alembic upgrade head` instead.
    Base.metadata.create_all(bind=engine)


app.include_router(donations.router)
app.include_router(receipts.router)
app.include_router(auth.router)
app.include_router(donors.router)
app.include_router(ngo_settings.router)
app.include_router(meetings.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}