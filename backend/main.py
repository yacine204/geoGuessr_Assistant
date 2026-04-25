from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from routes.auth import router as auth_router
from routes.guess import router as guess_router
from routes.cloudinary import router as cloudinary_router
from routes.conversation import router as conversation_router


def _sanitize_for_json(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {k: _sanitize_for_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_for_json(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_for_json(v) for v in value)
    return value


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
app.include_router(auth_router)
app.include_router(guess_router)
app.include_router(cloudinary_router)
app.include_router(conversation_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    safe_errors = _sanitize_for_json(exc.errors())
    return JSONResponse(status_code=422, content={"detail": safe_errors})

@app.get("/")
def read_root():
    return {"message": "GeoGussr Assistant API"}

