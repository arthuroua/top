import os
import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.db import init_db

app = FastAPI(title="Car Import MVP API", version="0.1.0")

_rate_buckets: dict[str, deque[float]] = defaultdict(deque)


def _cors_allow_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return max(minimum, int(raw))
    except ValueError:
        return default


def _client_key(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _rate_limit_for_path(path: str) -> int:
    if path.startswith("/api/v1/media/"):
        return _env_int("PUBLIC_MEDIA_RATE_LIMIT_PER_MINUTE", 240, minimum=1)
    if path.startswith("/api/v1/health"):
        return 0
    return _env_int("PUBLIC_API_RATE_LIMIT_PER_MINUTE", 120, minimum=1)


@app.middleware("http")
async def anti_scrape_headers_and_rate_limit(request: Request, call_next):
    path = request.url.path
    limit = _rate_limit_for_path(path)

    if path.startswith("/api/") and limit > 0:
        now = time.monotonic()
        window_start = now - 60
        bucket_key = f"{_client_key(request)}:{path.rsplit('/', 1)[0]}"
        bucket = _rate_buckets[bucket_key]
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        if len(bucket) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
                headers={"Retry-After": "60", "X-Robots-Tag": "noindex, nofollow, noarchive"},
            )
        bucket.append(now)

    response = await call_next(request)
    if path.startswith("/api/"):
        response.headers.setdefault("X-Robots-Tag", "noindex, nofollow, noarchive")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(),
    allow_credentials=_env_bool("CORS_ALLOW_CREDENTIALS", False),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


app.include_router(api_router)
