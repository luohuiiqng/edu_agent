from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


from app.routes.chat import router as chat_router
from app.routes.experiments import router as experiments_router

app = FastAPI(title="edu_agent Chat API", version="0.1.0")
# CORS(app)
# Development CORS config for local frontend. Tighten origins in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, __: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "BAD_REQUEST",
                "message": "请求参数格式错误",
            }
        },
    )


@app.exception_handler(HTTPException)
# Preserve structured business errors; wrap unknown HTTPException detail into standard contract.
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail

    if isinstance(detail, dict) and "error" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "HTTP_ERROR", "message": str(detail)}},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, __: Exception) -> JSONResponse:
    # Keep error contract consistent for frontend handling.
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "服务暂不可用，请稍后再试",
            }
        },
    )


app.include_router(chat_router, prefix="/agent_api")
app.include_router(experiments_router, prefix="/agent_api")


