from dotenv import load_dotenv
# Cargar las variables del archivo .env al inicio
load_dotenv()

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.openapi.utils import get_openapi
from app.api.endpoints import router as api_router

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app = FastAPI(
    title="CV-Match AI - API",
    description="Sistema Inteligente de Extracción, Clasificación y Screening de Hojas de Vida",
    version="0.1.0"
)

# Habilitar CORS para permitir peticiones desde el Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.getenv("APP_ENV", "development").casefold() == "production":
    app.add_middleware(HTTPSRedirectMiddleware)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store"
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Registrar todas las rutas agrupadas en el router modular
app.include_router(api_router)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        openapi_version="3.0.3",
    )
    body_schema = openapi_schema["paths"]["/upload-cv/"]["post"]["requestBody"]["content"]["multipart/form-data"]["schema"]
    if "$ref" in body_schema:
        schema_name = body_schema["$ref"].rsplit("/", 1)[-1]
        body_schema = openapi_schema["components"]["schemas"][schema_name]
    files_schema = body_schema["properties"]["files"]
    files_schema["items"] = {"type": "string", "format": "binary"}
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de CV-Match AI 🚀"}