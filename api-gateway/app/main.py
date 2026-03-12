from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import configure_logging
from app.core.rate_limit import InMemoryRateLimiter
from app.core.security import decode_access_token
from app.schemas import HealthLiveResponse, HealthReadyResponse, RootResponse

PUBLIC_ENDPOINTS: set[tuple[str, str]] = {
    ("GET", "/"),
    ("GET", "/health/live"),
    ("GET", "/health/ready"),
    ("POST", "/auth/login"),
    ("POST", "/auth/register"),
    ("POST", "/auth/refresh"),
}

# En-tetes HTTP geres par le proxy et qui ne doivent pas etre relayes.
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}

rate_limiter = InMemoryRateLimiter(
    requests_per_window=settings.rate_limit_requests_per_minute,
    window_seconds=60,
)


def _is_docs_path(path: str) -> bool:
    """Retourne True si le chemin cible la documentation OpenAPI."""
    return path == "/openapi.json" or path.startswith("/docs") or path.startswith("/redoc")


def _is_public_endpoint(path: str, method: str) -> bool:
    """Retourne True si l'endpoint est public (pas de JWT requis)."""
    if _is_docs_path(path):
        return True
    return (method.upper(), path) in PUBLIC_ENDPOINTS


def _requires_auth(path: str, method: str) -> bool:
    """Indique si l'endpoint doit etre protege par authentification."""
    return not _is_public_endpoint(path, method)


def _resolve_upstream(path: str, method: str) -> str | None:
    """Determine vers quel microservice relayer la requete."""
    upper_method = method.upper()
    if path.startswith("/auth") or path in {"/roles", "/permissions"}:
        return settings.identity_service_url
    if path.startswith("/analytics"):
        return settings.query_service_url
    if path == "/tasks" and upper_method == "GET":
        return settings.query_service_url
    if path.startswith("/tasks"):
        return settings.task_service_url
    return None


def _prepare_forward_headers(request: Request, correlation_id: str) -> dict[str, str]:
    """Construit les en-tetes sortants vers le service cible."""
    headers = {}
    for key, value in request.headers.items():
        lower_key = key.lower()
        if lower_key in HOP_BY_HOP_HEADERS or lower_key in {"host", "content-length"}:
            continue
        headers[key] = value
    headers["X-Correlation-Id"] = correlation_id
    return headers


def _build_forward_response(upstream_response: httpx.Response) -> Response:
    """Reconstruit la reponse HTTP renvoyee par le service cible."""
    response = Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
    )
    for key, value in upstream_response.headers.items():
        lower_key = key.lower()
        if lower_key in HOP_BY_HOP_HEADERS or lower_key == "content-length":
            continue
        response.headers[key] = value
    return response


async def _proxy_request(
    target_base_url: str,
    request: Request,
    correlation_id: str,
) -> Response:
    """Envoie la requete au service cible et retourne sa reponse."""
    target_url = f"{target_base_url.rstrip('/')}{request.url.path}"
    headers = _prepare_forward_headers(request, correlation_id)
    body = await request.body()

    timeout = httpx.Timeout(settings.upstream_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout) as client:
        upstream_response = await client.request(
            method=request.method,
            url=target_url,
            params=request.query_params,
            content=body,
            headers=headers,
        )
    return _build_forward_response(upstream_response)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialise puis libere les ressources partagees du service."""
    configure_logging()
    yield


app = FastAPI(title=settings.service_name, version=settings.service_version, lifespan=lifespan)


@app.middleware("http")
async def gateway_middleware(request: Request, call_next):
    """Applique les regles transverses: correlation ID, rate limiting et auth JWT."""
    method = request.method.upper()
    path = request.url.path
    correlation_id = request.headers.get("X-Correlation-Id") or str(uuid4())
    request.state.correlation_id = correlation_id

    # Le healthcheck ne doit pas etre bloque par le rate limiting.
    if path not in {"/health/live", "/health/ready"}:
        client_host = request.client.host if request.client is not None else "unknown"
        allowed, retry_after = rate_limiter.allow(client_host)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={
                    "X-Correlation-Id": correlation_id,
                    "Retry-After": str(retry_after),
                },
            )

    # Les routes privees exigent un Bearer token valide.
    if _requires_auth(path, method):
        auth_header = request.headers.get("Authorization")
        if auth_header is None or not auth_header.lower().startswith("bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid authentication credentials"},
                headers={
                    "X-Correlation-Id": correlation_id,
                    "WWW-Authenticate": "Bearer",
                },
            )

        token = auth_header.split(" ", maxsplit=1)[1].strip()
        try:
            decode_access_token(token)
        except ValueError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid authentication credentials"},
                headers={
                    "X-Correlation-Id": correlation_id,
                    "WWW-Authenticate": "Bearer",
                },
            )

    # La correlation est renvoyee au client pour tracer toute la chaine d'appel.
    response = await call_next(request)
    response.headers["X-Correlation-Id"] = correlation_id
    return response


@app.get("/", response_model=RootResponse)
def root() -> RootResponse:
    """Retourne les informations de base du service."""
    return RootResponse(
        service=settings.service_name,
        version=settings.service_version,
        status="ok",
    )


@app.get("/health/live", response_model=HealthLiveResponse)
def health_live() -> HealthLiveResponse:
    """Retourne l'etat de liveness du service."""
    return HealthLiveResponse(service=settings.service_name, status="alive")


@app.get("/health/ready", response_model=HealthReadyResponse)
def health_ready() -> HealthReadyResponse:
    """Retourne l'etat de readiness du service."""
    return HealthReadyResponse(
        service=settings.service_name,
        status="ready",
        checked_at=datetime.now(timezone.utc).isoformat(),
    )


@app.api_route(
    "/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy(full_path: str, request: Request) -> Response:
    """Relaye la requete vers le microservice cible en conservant le contexte utile."""
    del full_path
    target_base_url = _resolve_upstream(request.url.path, request.method)
    if target_base_url is None:
        return JSONResponse(status_code=404, content={"detail": "Route not found"})

    correlation_id = getattr(request.state, "correlation_id", str(uuid4()))
    try:
        return await _proxy_request(target_base_url, request, correlation_id)
    except httpx.RequestError:
        return JSONResponse(status_code=502, content={"detail": "Upstream service unavailable"})
