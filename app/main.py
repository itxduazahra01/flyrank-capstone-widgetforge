from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import auth, dashboard, public, widgets
from app.core.config import get_settings


def error_response(status_code: int, code: str, message: str, details=None) -> JSONResponse:
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Schema changes are applied by the dedicated Alembic migration service.
    yield


app = FastAPI(title="WidgetForge API", version="0.1.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(widgets.router)
app.include_router(public.router)
app.include_router(dashboard.router)


@app.middleware("http")
async def limit_public_submission_size(request: Request, call_next):
    is_public_widget_request = request.url.path.startswith("/public/v1/")
    origin = request.headers.get("origin")

    def apply_public_cors(response: Response) -> Response:
        if not origin:
            return response
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Idempotency-Key"
        response.headers["Access-Control-Max-Age"] = "600"
        response.headers["Vary"] = "Origin"
        return response

    # A preflight contains no widget ID, so its eligibility cannot be decided
    # per widget. The subsequent POST is always checked against that widget's
    # saved allowed-origins list in app.api.public.
    if is_public_widget_request and request.method == "OPTIONS":
        return apply_public_cors(Response(status_code=200))
    if request.url.path == "/public/v1/submissions":
        length = request.headers.get("content-length")
        if length and int(length) > get_settings().max_submission_bytes:
            return apply_public_cors(error_response(413, "payload_too_large", "Request body is too large"))
    response = await call_next(request)
    if is_public_widget_request:
        response = apply_public_cors(response)
    if request.url.path == "/widget.v1.js":
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    details = [{"field": ".".join(str(item) for item in error["loc"] if item != "body"), "message": error["msg"]} for error in exc.errors()]
    return error_response(422, "validation_error", "Request validation failed", details)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    codes = {401: "unauthorized", 404: "not_found", 413: "payload_too_large", 422: "validation_error", 429: "rate_limited"}
    response = error_response(exc.status_code, codes.get(exc.status_code, "request_error"), str(exc.detail))
    if exc.headers:
        response.headers.update(exc.headers)
    return response


@app.exception_handler(404)
async def route_not_found(_: Request, __):
    return error_response(404, "not_found", "Route not found")


@app.get("/health", tags=["operations"])
def health():
    return {"status": "ok", "service": "widgetforge", "phase": "owner-path"}


app.mount("/", StaticFiles(directory="app/static", html=False), name="static")
