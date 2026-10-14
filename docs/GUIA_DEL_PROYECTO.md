# Guía del proyecto

Este documento describe la responsabilidad principal de cada archivo fuente,
configuración y documentación del repositorio. No sustituye los comentarios técnicos
ni describe el código línea por línea.

## Raíz

- `.env.example`: nombres de variables para Gemini, reclutador inicial, JWT, entorno y
  CORS. Contiene valores vacíos o de ejemplo; no debe contener secretos reales.
- `.gitignore`: excluye entornos virtuales, cachés, dependencias compiladas, builds,
  bases de datos locales, almacenamiento temporal, logs y archivos de entorno.
- `README.md`: instalación, ejecución, configuración sensible, funcionalidades,
  seguridad, pruebas básicas y árbol del proyecto.
- `package-lock.json`: lockfile npm de la raíz. El frontend administra sus dependencias
  y lockfile en `frontend/`.

## Backend

### Aplicación y API

- `backend/app/main.py`: crea la aplicación FastAPI, configura middleware y políticas
  CORS/HTTPS y registra las rutas.
- `backend/app/api/endpoints.py`: expone autenticación, carga/extracción/análisis de CV,
  seguimiento y reintento, vacantes, matching, ranking, detalle de candidato y generación
  de guía de entrevista.
- `backend/app/api/auth_dependencies.py`: dependencia para resolver y exigir al usuario
  autenticado en rutas protegidas.

### Modelos y contratos

- `backend/app/models/cv_schema.py`: estructuras de perfil de candidato, experiencia y
  educación extraídas del currículum; valida los campos normalizados.
- `backend/app/models/schemas.py`: archivo legado vacío; los contratos vigentes están
  definidos bajo `backend/app/schemas/`.
- `backend/app/schemas/__init__.py`: reexporta algunos esquemas de vacante y matching.
- `backend/app/schemas/auth.py`: cuerpos de login y respuestas públicas de token/usuario.
- `backend/app/schemas/candidate.py`: contrato de detalle del candidato y explicación.
- `backend/app/schemas/interview.py`: entrada y salida tipadas para guías de entrevista.
- `backend/app/schemas/matching.py`: entrada/salida del matching, categorías, pesos,
  evidencias y validación de consistencia del score total.
- `backend/app/schemas/ranking.py`: contratos de candidatos y respuesta del ranking.
- `backend/app/schemas/vacancy.py`: entrada, requisitos estructurados y respuesta de
  vacantes.

### Servicios

- `backend/app/services/auth_service.py`: aprovisiona al reclutador inicial, valida
  contraseñas con bcrypt, emite/verifica/revoca JWT, mantiene sesiones y asigna propiedad
  de recursos en SQLite.
- `backend/app/services/extraction_service.py`: guarda archivos PDF y extrae texto con
  pdfplumber.
- `backend/app/services/interview_service.py`: prepara prompts y obtiene preguntas
  técnicas y comportamentales de Gemini con validación y reintentos.
- `backend/app/services/llm_extraction_service.py`: llama al modelo para convertir el
  texto de un CV en un perfil estructurado.
- `backend/app/services/matching_service.py`: evalúa evidencia de perfil frente a
  requisitos y calcula localmente puntajes por categoría y score total.
- `backend/app/services/normalization_service.py`: normaliza los datos de CV a la
  estructura de perfil usada por la aplicación.
- `backend/app/services/ranking_service.py`: persiste resultados de matching en
  `temp_storage/`, obtiene ranking y construye detalles de candidato.
- `backend/app/services/status_service.py`: administra estados de procesamiento de CV
  y mensajes de fallo durante la ejecución del backend.
- `backend/app/services/vacancy_service.py`: registra, estructura y consulta vacantes,
  incluyendo sus requisitos generados con Gemini.

### Pruebas

- `backend/tests/conftest.py`: configura fixtures y estado aislado para las pruebas.
- `backend/tests/test_auth.py`: login, sesión, autorización y revocación de acceso.
- `backend/tests/test_candidate_detail.py`: endpoint y contenido del detalle del candidato.
- `backend/tests/test_interview.py`: endpoint y respuesta del generador de entrevistas.
- `backend/tests/test_matching.py`: cálculo del score y validación de evidencias.
- `backend/tests/test_normalization.py`: reglas de normalización de perfiles.
- `backend/tests/test_ranking.py`: persistencia, orden/filtros y endpoints del ranking.
- `backend/tests/test_status.py`: estados, extracción/reintento y respuestas asociadas.
- `backend/tests/test_vacancy.py`: registro, estructuración y consulta de vacantes.
- `backend/requirements.txt`: dependencias Python del backend y las pruebas.

## Frontend

### Aplicación, estilos y recursos

- `frontend/src/main.jsx`: punto de entrada React; monta la aplicación y estilos base.
- `frontend/src/App.jsx`: valida sesión, muestra login o espacio de trabajo, conserva el
  estado de las pestañas visitadas y organiza carga de CV, vacantes, matching y ranking.
- `frontend/src/App.css`: estilos compartidos de la aplicación, carga de archivos,
  resultados, estados y elementos de navegación.
- `frontend/src/index.css`: estilos globales y reglas base de la interfaz.
- `frontend/src/assets/hero.png`: recurso gráfico incluido en el proyecto; no forma parte
  del flujo de datos ni de la lógica de autenticación.
- `frontend/src/assets/react.svg` y `frontend/src/assets/vite.svg`: recursos de plantilla
  de Vite/React, conservados en el repositorio.
- `frontend/public/favicon.svg` y `frontend/public/icons.svg`: iconos públicos servidos
  directamente por Vite.

### Componentes

- `frontend/src/components/VacancyForm.jsx`: formulario de vacante, estados de envío,
  errores, limpieza explícita y vista de requisitos estructurados.
- `frontend/src/components/auth/Login.jsx` y `Login.css`: acceso con correo y contraseña
  y presentación de errores/carga.
- `frontend/src/components/candidate/CandidateDetailModal.jsx`: ficha del candidato,
  desglose, resumen, experiencia/formación y generación/copia de entrevista.
- `frontend/src/components/candidate/CandidateDetailModal.css`: estilos de la ficha,
  historial y guía de entrevista.
- `frontend/src/components/candidate/RadarMatchChart.jsx` y `RadarMatchChart.css`:
  visualización SVG de los puntajes normalizados de habilidades, experiencia, educación
  e idiomas; no inventa métricas ausentes.
- `frontend/src/components/matching/MatchingPanel.jsx` y `MatchingPanel.css`: entrada de
  perfil/requisitos, selección opcional de vacante y presentación del score/evidencias.
- `frontend/src/components/ranking/RankingDashboard.jsx` y `RankingDashboard.css`:
  selección de vacante, filtros/orden y listado con apertura de detalle de candidato.

### API y configuración web

- `frontend/src/services/api.js`: cliente HTTP, token Bearer, login/logout y funciones
  para llamar a los endpoints de la aplicación.
- `frontend/package.json`: dependencias y comandos `dev`, `lint`, `build` y `preview`.
- `frontend/package-lock.json`: versiones exactas resueltas para reproducir la instalación.
- `frontend/index.html`: documento HTML de entrada de Vite.
- `frontend/vite.config.js`: configuración de Vite y plugin React.
- `frontend/eslint.config.js`: reglas de ESLint para el código frontend.
- `frontend/postcss.config.js`: integración de PostCSS y Tailwind.
- `frontend/tailwind.config.js`: configuración del framework de estilos utilizado.
- `frontend/.gitignore`: exclusiones de dependencias, compilaciones, logs y archivos de
  editor en el subproyecto frontend.
- `frontend/README.md`: documentación inicial de la plantilla Vite/React; el procedimiento
  propio del producto está en el README de la raíz.

## Documentación y persistencia

- `docs/MVP 1 - ANALIZADOR DE HOJAS DE VIDA.pdf`: documento original del MVP.
- `docs/PROMPT ELABORADO MVP1.pdf`: documento de prompts de referencia.
- `temp_storage/` (generado): PDFs y registros JSON temporales de vacantes y matching.
  Se excluye del repositorio y no constituye almacenamiento cifrado ni copia de seguridad.
- `backend/auth.sqlite3` (generado): usuarios, hashes, sesiones y asignaciones de recursos.
  Se excluye del repositorio y debe protegerse/respaldarse según la política operativa.

## Configuración de seguridad

Los secretos reales deben residir en variables de entorno o en un gestor de secretos del
entorno desplegado; nunca en Git. Entre ellos están `GEMINI_API_KEY`,
`INITIAL_RECRUITER_PASSWORD` y `JWT_SECRET_KEY`. Usa un JWT secret aleatorio de al menos
32 bytes, limita CORS a los orígenes requeridos y exige HTTPS en producción. Las
contraseñas de reclutador se almacenan como hash bcrypt, no como texto plano. El frontend
conserva el token JWT en `localStorage`, lo envía en la cabecera `Authorization` y elimina
el token local al cerrar sesión; el backend valida expiración y revocación.
