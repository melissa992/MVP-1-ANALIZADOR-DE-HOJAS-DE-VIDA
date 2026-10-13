# CV-Match AI - Sistema Inteligente de Selección

Plataforma modular para la ingesta y extracción de texto de hojas de vida en PDF, con el objetivo de apoyar el análisis y la selección de candidatos.

## Equipo de desarrollo

- **Brayan Jurado:** Ingesta (HU-01) y extracción de texto (HU-02).
- **Nicolás Granada:** Procesamiento con LLM y normalización (HU-03 / HU-04).
- **Camilo:** Gestión de vacantes y parametrización (HU-05 / HU-06).
- **Melissa:** Motor de matching, scoring y dashboard (HU-07 a HU-10).

## Requisitos previos

- Python 3.10 o superior.
- Node.js 20.19 o superior, o 22.12 o superior, y npm. Estas versiones son compatibles con Vite 8.
- Git, si vas a clonar el repositorio.

## Instalación y ejecución

El backend y el frontend se ejecutan al mismo tiempo en terminales separadas.

### Backend

Desde la carpeta raíz del repositorio, ejecuta:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

El análisis de hojas de vida utiliza Gemini. Antes de iniciar el backend, configura tu
clave de API en el entorno:

```powershell
$env:GEMINI_API_KEY = "tu-clave-de-gemini"
$env:GEMINI_MODEL = "gemini-3-flash-preview" # opcional
```

También puedes copiar [.env.example](.env.example) como referencia. No agregues la
clave real al repositorio.

En Windows, si usas el Símbolo del sistema en lugar de PowerShell, activa el entorno con:

```bat
venv\Scripts\activate.bat
```

En macOS o Linux, activa el entorno con:

```bash
source venv/bin/activate
```

Al iniciar, la API queda disponible en `http://127.0.0.1:8000`. Los archivos cargados se almacenan temporalmente en `temp_storage/`, relativo a la carpeta desde la que se inicia el backend.

### Frontend

Abre una segunda terminal en la raíz del repositorio y ejecuta:

```powershell
cd frontend
npm install
npm run dev
```

Vite mostrará en la terminal la dirección local del frontend, normalmente `http://localhost:5173/`.

## Documentación y prueba de la API

Con el backend en ejecución, abre Swagger UI en [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs). El esquema OpenAPI también está disponible en [`http://127.0.0.1:8000/openapi.json`](http://127.0.0.1:8000/openapi.json).

Para probar la extracción desde Swagger:

1. Ejecuta `POST /upload-cv/` y selecciona uno o varios PDF.
2. Copia el `file_id` de un archivo cargado correctamente.
3. Ejecuta `POST /extract-text/{file_id}` y pega el identificador.
4. Revisa el texto extraído, el número de páginas y el resumen de caracteres por página.

La interfaz web ofrece el mismo flujo: carga un PDF y selecciona **Ver texto extraído** en el resultado del archivo.

## Comandos útiles del frontend

Desde `frontend/`:

```bash
npm run lint
npm run build
npm run preview
```

## Estructura del proyecto

cv-match-ai/
├── backend/
│   ├── app/
│   │   ├── api/          # Endpoints de FastAPI
│   │   ├── services/     # Lógica de extracción, LLMs y matching
│   │   ├── models/       # Esquemas de Pydantic
│   │   └── main.py       # Archivo principal de FastAPI
│   ├── tests/            # Pruebas unitarias con pytest
│   └── requirements.txt  # Dependencias de Python
├── frontend/             # Interfaz web (Next.js / HTML-JS)
├── docs/                 # Documentación y Bitácora
│   ├── PRODUCT_BACKLOG.md
│   └── BITACORA_MVP.md
├── .gitignore            # Archivos a ignorar por Git
└── README.md             # Descripción general del proyecto
