# CV-Match AI - Sistema Inteligente de Selección

Plataforma modular para la ingesta y extracción de texto de hojas de vida en PDF, con el objetivo de apoyar el análisis y la selección de candidatos.

## Equipo de desarrollo

- **Brayan Jurado:** Ingesta (HU-01), extracción de texto (HU-02), resiliencia de estados (HU-11), autenticación JWT (HU-12) e innovaciones AI Interviewer & Radar Chart (HU-13).
- **Nicolás Granada:** Procesamiento con LLM y normalización (HU-03 / HU-04).
- **Camilo López:** Gestión de vacantes y parametrización (HU-05 / HU-06 / HU-07).
- **Melissa Ocoró:** Motor de matching, scoring y dashboard (HU-08 a HU-10).

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
$env:ELEVENLABS_API_KEY = "tu-clave-de-elevenlabs"
```

También puedes copiar [.env.example](.env.example) como referencia. No agregues la
clave real al repositorio.

La API requiere credenciales del reclutador inicial y un secreto JWT. Genera
un secreto aleatorio de al menos 32 bytes (por ejemplo, en PowerShell:
`[Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(48))`)
y configura estas variables en `.env` o en el entorno del servidor:

```env
INITIAL_RECRUITER_EMAIL=reclutador@empresa.com
INITIAL_RECRUITER_PASSWORD=una-frase-secreta-de-al-menos-12-caracteres
JWT_SECRET_KEY=pega-aqui-el-secreto-aleatorio-generado
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
```

La contraseña debe tener al menos 12 caracteres y no más de 72 bytes UTF-8. La cuenta
se aprovisiona automáticamente; no hay registro público. Su hash bcrypt y las sesiones
se guardan en `backend/auth.sqlite3`, fuera del repositorio. Al cambiar la contraseña
configurada y reiniciar el backend, el hash se actualiza y las sesiones anteriores se
revocan. La primera inicialización asigna los CV, vacantes y rankings existentes a esta
cuenta.

### Despliegue en Vercel y Render

El frontend se despliega en Vercel y la API FastAPI en Render. El backend usa un disco
persistente de Render para conservar la base SQLite de autenticación y los archivos
subidos. El servicio de Render debe permanecer en una sola instancia al usar ese disco.

1. Sube los cambios a GitHub y crea un proyecto Vercel desde el repositorio. Configura
   `frontend` como **Root Directory**; Vercel detecta Vite y usa `npm run build` con
   `dist` como salida.
2. Despliega primero el frontend para obtener su dominio, por ejemplo
   `https://mi-proyecto.vercel.app`.
3. En Render, crea un **Blueprint** desde el mismo repositorio y selecciona
   `render.yaml`. En la configuración del servicio completa las variables que el Blueprint
   solicita:
   - `INITIAL_RECRUITER_EMAIL`: el correo que usarás para iniciar sesión.
   - `INITIAL_RECRUITER_PASSWORD`: una contraseña de 12 a 72 bytes UTF-8.
   - `JWT_SECRET_KEY`: un secreto aleatorio de al menos 32 bytes; no reutilices una clave
     de ejemplo.
   - `GEMINI_API_KEY`: tu clave de Gemini para las funciones de análisis.
   - `ELEVENLABS_API_KEY`: tu clave de ElevenLabs para la voz del entrevistador.
   El Blueprint configura `CORS_ALLOWED_ORIGINS` para el dominio de Vercel del proyecto.
   Si usas un dominio personalizado o cambias el dominio de Vercel, actualiza esa variable
   en Render con los orígenes permitidos, separados por comas y sin barras finales.
4. Cuando Render muestre la URL pública de la API, en Vercel agrega la variable
   `VITE_API_BASE_URL` con esa URL (sin barra final) y vuelve a desplegar el frontend.
5. Abre el dominio de Vercel e inicia sesión con el correo y contraseña que configuraste
   en Render.

No uses un plan de Render sin disco persistente para este backend: la base SQLite contiene
usuarios y sesiones, y el sistema guarda archivos en `APP_STORAGE_DIR`. El Blueprint monta
el disco en `/var/data`; no escales el servicio a varias instancias con este almacenamiento
local. Si cambias el dominio del frontend, actualiza `CORS_ALLOWED_ORIGINS` en Render y
reinicia o vuelve a desplegar el servicio.

### Credenciales, tokens y datos locales

- `.env` contiene secretos locales y está excluido por `.gitignore`. El archivo
  `.env.example` solo incluye nombres de variables y valores vacíos/de ejemplo: nunca
  pegues credenciales reales en el README, en incidencias, capturas o commits.
- `.gitignore` evita agregar archivos locales nuevos, pero no deja de versionar archivos
  que ya estaban en Git; los artefactos ya rastreados deben retirarse del índice antes
  de que la regla los excluya de los próximos commits.
- Si una clave de Gemini, contraseña o secreto JWT llega a Git o se comparte por error,
  considérala comprometida y rótala de inmediato. Borrar el archivo en un commit posterior
  no elimina el secreto del historial de Git.
- Las contraseñas no se guardan en texto plano: se almacena su hash bcrypt. El JWT de
  acceso tiene una duración configurable mediante `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`;
  las rutas protegidas lo reciben en la cabecera HTTP `Authorization`.
- El frontend conserva el token en `localStorage`. Cerrar sesión solicita la revocación
  al backend y elimina el token local. No compartas el token: equivale temporalmente a
  las credenciales de la sesión. En producción usa HTTPS y protege la aplicación frente
  a XSS, ya que el almacenamiento local es accesible desde JavaScript del mismo origen.
- En local, los registros de reclutador, hashes y sesiones permanecen en
  `backend/auth.sqlite3`; los PDF, vacantes, perfiles y resultados se guardan en
  `temp_storage/`. En Render, `AUTH_DATABASE_PATH` y `APP_STORAGE_DIR` apuntan al disco
  persistente montado en `/var/data`. Estos datos no están cifrados ni respaldados por
  defecto: define retención y copias seguras antes de operar con información real.
- Los recursos se asocian a su reclutador y los endpoints verifican su propiedad. En
  producción configura un secreto JWT único, HTTPS/TLS, orígenes CORS explícitos y
  credenciales fuertes; no uses los ejemplos de este documento como credenciales reales.

En producción configura `APP_ENV=production`, define `CORS_ALLOWED_ORIGINS` con los
orígenes HTTPS reales y sirve la API detrás de HTTPS (TLS 1.2 o superior). Si TLS termina
en un proxy, configura Uvicorn para confiar únicamente en la IP de ese proxy y este debe
establecer `X-Forwarded-Proto: https`; la API redirige HTTP a HTTPS y agrega HSTS a las
respuestas seguras. Nunca uses el secreto de ejemplo ni HTTP en producción.

Las rutas de CV, vacantes, matching, ranking y estado requieren la cabecera
`Authorization` con un token de acceso.
El frontend conserva el token en `localStorage`, valida la sesión al abrir la aplicación
y ofrece **Cerrar sesión**; el backend valida expiración y revocación en cada petición.

## Simulador de entrevista por voz (HU-13)

Desde **Ranking de candidatos**, abre **Ver detalle** en un perfil evaluado y selecciona
**Iniciar Simulación de Entrevista por Voz**. Gemini genera preguntas técnicas y
comportamentales basadas en el perfil y las brechas de la vacante; ElevenLabs sintetiza
las preguntas y el feedback. La respuesta se transcribe con Web Speech API en navegadores
compatibles (Chrome/Edge); también se puede escribir. Cada respuesta se evalúa con Gemini
y al finalizar se presenta el puntaje promedio, el radar de evaluación y la transcripción.

Configura `GEMINI_API_KEY` y `ELEVENLABS_API_KEY` en el entorno del backend. La voz se
puede personalizar con `ELEVENLABS_VOICE_ID` y `ELEVENLABS_MODEL`; el identificador de voz
por defecto es una voz multilingüe de ElevenLabs. La transcripción de voz se ejecuta en el
navegador; la aplicación envía el texto reconocido al backend para evaluación, no el audio
del micrófono. Web Speech puede requerir conexión y permiso de micrófono del navegador.

Los endpoints `POST /interview/start`, `POST /interview/respond` y `POST /interview/tts`
requieren sesión autenticada. Inicio y evaluación verifican que el usuario sea propietario
de la vacante y recuperan el perfil almacenado; el servicio TTS devuelve audio `audio/mpeg`.
La guía de preguntas tradicional permanece disponible mediante **Generar Guía de Entrevista
con IA** y se puede copiar desde la ficha.

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

Cada PDF cargado tiene un estado en memoria consultable con `GET /status/{file_id}`:
`PENDING`, `EXTRACTING`, `ANALYZING`, `COMPLETED` o `FAILED` (con `error_message`).
La interfaz actualiza los estados mientras se analiza y permite reintentar un fallo con
`POST /retry/{file_id}`. El reintento usa el PDF ya almacenado y responde `202 Accepted`
mientras ejecuta extracción y análisis en segundo plano. El registro es temporal: se pierde
al reiniciar el backend, aunque los PDF almacenados se conserven.

## Detalle del candidato (HU-10)

Los resultados asociados a una vacante desde `POST /match/` guardan el perfil estructurado
y la evaluación de matching en `temp_storage/`. En el dashboard, **Ver Detalle** solicita
`GET /candidates/{candidate_id}/detail?vacancy_id={vacancy_id}` y muestra la experiencia,
habilidades, estudios, idiomas, fortalezas, brechas y resumen ejecutivo. El análisis también
incluye un gráfico radar de hard skills, experiencia, educación e idiomas: cada eje se expresa
como porcentaje de los puntos máximos de esa categoría, a partir del desglose ya calculado por
el motor de matching. No se generan puntuaciones inferidas para dimensiones que el motor no evalúa.
Los rankings guardados antes de esta funcionalidad no contienen la ficha completa; vuelve
a calcular el matching asociado a la vacante para generar el detalle.

## Comandos útiles del frontend

Desde `frontend/`:

```bash
npm run lint
npm run build
npm run preview
```

## Estructura del proyecto

```text
.
├── .env.example                    # Variables de entorno de referencia, sin secretos reales
├── .gitignore                      # Excluye secretos, datos locales, cachés y builds
├── README.md                       # Instalación, uso, seguridad y estructura del proyecto
├── package-lock.json               # Lockfile npm de la raíz
├── backend/                        # API, lógica de negocio y pruebas automatizadas
│   ├── requirements.txt            # Dependencias Python del backend
│   ├── app/                        # Aplicación FastAPI
│   │   ├── main.py                 # Inicializa API, middleware y rutas
│   │   ├── api/                    # Rutas HTTP y dependencias de autorización
│   │   │   ├── auth_dependencies.py # Identifica y protege el acceso del usuario
│   │   │   └── endpoints.py         # Login, CV, estados, vacantes, matching y ranking
│   │   ├── models/                 # Modelos de datos de dominio/compatibilidad
│   │   │   ├── cv_schema.py        # Estructura validada del perfil extraído del CV
│   │   │   └── schemas.py          # Archivo legado vacío; contratos actuales en schemas/
│   │   ├── schemas/                # Contratos Pydantic de entrada y respuesta
│   │   │   ├── __init__.py         # Reexportaciones de esquemas principales
│   │   │   ├── auth.py             # Credenciales y respuestas de autenticación
│   │   │   ├── candidate.py        # Perfil, detalle y explicación del candidato
│   │   │   ├── interview.py         # Solicitud y guía de entrevista generada
│   │   │   ├── matching.py         # Score, desglose y evidencia de matching
│   │   │   ├── ranking.py          # Elementos y respuesta del ranking
│   │   │   └── vacancy.py          # Datos de vacante y requisitos estructurados
│   │   └── services/               # Procesamiento y reglas de negocio
│   │       ├── auth_service.py     # Hash bcrypt, JWT, sesiones y propiedad de recursos
│   │       ├── extraction_service.py # Almacenamiento temporal y extracción PDF
│   │       ├── interview_service.py # Generación de guía con Gemini
│   │       ├── llm_extraction_service.py # Extracción estructurada de perfiles con IA
│   │       ├── matching_service.py # Evidencias y cálculo de puntajes por categoría
│   │       ├── normalization_service.py # Normalización del perfil del candidato
│   │       ├── ranking_service.py  # Persistencia y consulta de rankings/detalles
│   │       ├── status_service.py   # Ciclo de estados del procesamiento de CV
│   │       └── vacancy_service.py  # Registro y estructuración de vacantes
│   └── tests/                      # Pruebas de API y servicios
│       ├── conftest.py             # Configuración compartida y fixtures de pruebas
│       ├── test_auth.py            # Autenticación, sesiones y autorización
│       ├── test_candidate_detail.py # Consulta del detalle del candidato
│       ├── test_interview.py       # Generación de guías de entrevista
│       ├── test_matching.py        # Puntajes y validación de evidencias
│       ├── test_normalization.py   # Normalización de perfiles
│       ├── test_ranking.py         # Ranking, filtros y persistencia
│       ├── test_status.py          # Estados, extracción y reintentos
│       └── test_vacancy.py         # Registro y consulta de vacantes
├── docs/                           # Guía funcional y documentos de referencia
│   ├── GUIA_DEL_PROYECTO.md        # Descripción ampliada de los archivos y módulos
│   ├── MVP 1 - ANALIZADOR DE HOJAS DE VIDA.pdf # Documento base del MVP
│   └── PROMPT ELABORADO MVP1.pdf   # Prompts de referencia del proyecto
└── frontend/                       # Aplicación web React con Vite
    ├── .gitignore                  # Exclusiones locales del frontend
    ├── package.json                # Dependencias y comandos npm
    ├── package-lock.json           # Versiones exactas de dependencias frontend
    ├── index.html                  # Documento HTML de entrada de Vite
    ├── vite.config.js              # Configuración de Vite y React
    ├── eslint.config.js            # Reglas de lint del frontend
    ├── postcss.config.js           # Integración de PostCSS/Tailwind
    ├── tailwind.config.js          # Configuración de Tailwind CSS
    ├── README.md                   # README inicial de la plantilla Vite
    ├── public/                     # Recursos estáticos servidos sin transformación
    │   ├── favicon.svg              # Icono del sitio
    │   └── icons.svg                # Iconos SVG compartidos
    └── src/                        # Código de interfaz y comunicación con la API
        ├── App.jsx                 # Sesión, navegación y composición de pestañas
        ├── App.css                 # Estilos de módulos y controles principales
        ├── index.css               # Estilos globales y base visual
        ├── main.jsx                # Montaje de React en el documento HTML
        ├── assets/                 # Imágenes y recursos gráficos importados
        │   ├── hero.png             # Recurso gráfico incluido en el proyecto
        │   ├── react.svg            # Recurso de plantilla React
        │   └── vite.svg             # Recurso de plantilla Vite
        ├── components/             # Vistas y componentes reutilizables
        │   ├── VacancyForm.jsx     # Registro de vacantes y requisitos generados
        │   ├── auth/               # Interfaz de inicio de sesión
        │   │   ├── Login.jsx       # Formulario de acceso
        │   │   └── Login.css       # Estilos de acceso
        │   ├── candidate/          # Detalle del candidato y visualizaciones
        │   │   ├── CandidateDetailModal.jsx # Perfil, análisis y guía de entrevista
        │   │   ├── CandidateDetailModal.css # Estilos del detalle del candidato
        │   │   ├── RadarMatchChart.jsx # Radar SVG de competencias del matching
        │   │   └── RadarMatchChart.css # Estilos responsive del radar
        │   ├── matching/            # Evaluación de compatibilidad candidato-vacante
        │   │   ├── MatchingPanel.jsx # Entrada, cálculo y resultado del matching
        │   │   └── MatchingPanel.css # Estilos del motor de matching
        │   └── ranking/             # Búsqueda y comparación de candidatos
        │       ├── RankingDashboard.jsx # Filtros, orden y tabla de candidatos
        │       └── RankingDashboard.css # Estilos del ranking
        └── services/
            └── api.js               # Peticiones HTTP y gestión local del token
```

El backend genera `temp_storage/` para PDFs y registros JSON, y `backend/auth.sqlite3`
para usuarios, sesiones y propiedad de recursos. Son datos locales excluidos de Git;
consulta [docs/GUIA_DEL_PROYECTO.md](docs/GUIA_DEL_PROYECTO.md) para más detalle por módulo.
