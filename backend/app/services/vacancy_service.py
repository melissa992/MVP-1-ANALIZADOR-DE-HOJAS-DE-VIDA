from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
from typing import Dict, List, Optional, Union
import uuid
from uuid import UUID

from dotenv import load_dotenv
from google import genai
from google.genai import types
from app.storage import STORAGE_DIR

from app.schemas.vacancy import (
    VacancyCreate,
    VacancyRequirements,
    VacancyResponse,
)

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DEFAULT_STORAGE_DIR = str(STORAGE_DIR)


class VacancyService:
    """
    Servicio de lógica de negocio para la gestión de vacantes y
    procesamiento de requisitos con Google Gemini (HU-05 / HU-06).
    """

    def __init__(self, storage_dir: str = DEFAULT_STORAGE_DIR) -> None:
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self._db: Dict[str, VacancyResponse] = {}
        self._load_existing_vacancies()

        self._client: Optional[genai.Client] = None
        self.model = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
        self.max_attempts = int(os.getenv("GEMINI_MAX_ATTEMPTS", "3"))
        self.retry_delay_seconds = float(os.getenv("GEMINI_RETRY_DELAY_SECONDS", "2"))

    @property
    def client(self) -> genai.Client:
        """Inicializa o retorna la instancia de cliente Gemini usando la variable de entorno."""
        if self._client is None:
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "Falta la variable de entorno GEMINI_API_KEY. Configúrala en el archivo .env."
                )
            self._client = genai.Client(api_key=api_key)
        return self._client

    @client.setter
    def client(self, value: genai.Client) -> None:
        self._client = value

    def _load_existing_vacancies(self) -> None:
        """Lee y sincroniza en memoria las vacantes previamente guardadas en temp_storage."""
        if not os.path.exists(self.storage_dir):
            return

        for filename in os.listdir(self.storage_dir):
            if filename.startswith("vacancy_") and filename.endswith(".json"):
                file_path = os.path.join(self.storage_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        vacancy = VacancyResponse(**data)
                        self._db[str(vacancy.id)] = vacancy
                except Exception:
                    continue

    def create_vacancy(self, data: VacancyCreate) -> VacancyResponse:
        """
        HU-05: Registra una nueva vacante con estado 'pending_processing'.
        Almacena la entidad en memoria y guarda el archivo JSON en 'temp_storage'.
        """
        vacancy_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        new_vacancy = VacancyResponse(
            id=vacancy_id,
            title=data.title.strip(),
            raw_description=data.raw_description.strip(),
            status="pending_processing",
            created_at=now,
        )

        self._db[str(vacancy_id)] = new_vacancy

        file_path = os.path.join(self.storage_dir, f"vacancy_{vacancy_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_vacancy.model_dump_json(indent=2))

        return new_vacancy

    def process_vacancy_requirements(self, raw_description: str) -> VacancyRequirements:
        """
        HU-06: Analiza la descripción libre de la vacante utilizando Google Gemini
        para extraer requisitos estructurados conforme al esquema VacancyRequirements.
        """
        if not raw_description or not raw_description.strip():
            raise ValueError("La descripción de la vacante no puede estar vacía.")

        system_prompt = (
            "Eres un reclutador técnico senior y experto en recursos humanos (HU-06). "
            "Tu objetivo es analizar la descripción textual de una oferta de empleo y "
            "extraer los requisitos clave de manera objetiva y estrictamente apegada al texto.\n\n"
            "Debes devolver EXCLUSIVAMENTE un objeto JSON válido que cumpla exactamente este esquema:\n"
            f"{json.dumps(VacancyRequirements.model_json_schema(), ensure_ascii=False)}\n\n"
            "Instrucciones de extracción:\n"
            "- cargo: Título estandarizado del puesto (string).\n"
            "- anios_experiencia_requeridos: Número entero de años mínimos de experiencia requeridos (int). "
            "Si no se especifica, deduce un valor prudente o usa 0.\n"
            "- habilidades_clave: Lista de tecnologías, herramientas, conocimientos y competencias indispensables (array de strings).\n"
            "- idiomas: Lista de idiomas requeridos o deseables (array de strings, ej. ['inglés', 'español']).\n"
            "- nivel_estudios: Grado educativo requerido (string, ej. 'Profesional universitario', 'Tecnólogo', 'No especificado').\n"
            "No incluyas explicaciones, saludos ni formato Markdown fuera del JSON."
        )

        for attempt in range(self.max_attempts):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=f"Analiza la siguiente oferta laboral y extrae los requisitos estructurados:\n\n{raw_description}",
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json",
                        temperature=0,
                    ),
                )

                content = response.text
                if not content:
                    raise ValueError("La respuesta recibida del modelo Gemini está vacía.")

                content_clean = content.strip()
                if content_clean.startswith("```"):
                    content_clean = content_clean.strip("`")
                    if content_clean.startswith("json"):
                        content_clean = content_clean[4:].strip()

                parsed_data = json.loads(content_clean)
                if not isinstance(parsed_data, dict):
                    raise ValueError("La salida del modelo Gemini no es un objeto JSON.")

                return VacancyRequirements(**parsed_data)

            except Exception as e:
                if not self._is_transient_error(e) or attempt == self.max_attempts - 1:
                    raise RuntimeError(f"HU-06 Error al procesar los requisitos con Gemini: {str(e)}") from e

                time.sleep(self.retry_delay_seconds * (2**attempt))

        raise RuntimeError("HU-06 Error inesperado al procesar los requisitos con Gemini.")

    @staticmethod
    def _is_transient_error(error: Exception) -> bool:
        error_text = str(error).upper()
        status_code = getattr(error, "code", None) or getattr(error, "status_code", None)
        return status_code == 503 or "503" in error_text or "UNAVAILABLE" in error_text

    def update_vacancy(
        self,
        vacancy_id: Union[UUID, str],
        structured_requirements: VacancyRequirements,
        status: str = "processed",
    ) -> VacancyResponse:
        """
        Actualiza el estado y los requisitos estructurados de una vacante existente,
        sincronizando los cambios en memoria y en temp_storage.
        """
        vac_id_str = str(vacancy_id)
        vacancy = self.get_vacancy(vac_id_str)
        if not vacancy:
            raise ValueError(f"No se encontró la vacante con ID {vacancy_id}.")

        vacancy.structured_requirements = structured_requirements
        vacancy.status = status

        self._db[vac_id_str] = vacancy

        file_path = os.path.join(self.storage_dir, f"vacancy_{vac_id_str}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(vacancy.model_dump_json(indent=2))

        return vacancy

    def get_vacancy(self, vacancy_id: Union[UUID, str]) -> Optional[VacancyResponse]:
        """Consulta una vacante por su ID (en memoria o cargando desde disco)."""
        vac_id_str = str(vacancy_id)
        if vac_id_str in self._db:
            return self._db[vac_id_str]

        file_path = os.path.join(self.storage_dir, f"vacancy_{vac_id_str}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    vacancy = VacancyResponse(**data)
                    self._db[vac_id_str] = vacancy
                    return vacancy
            except Exception:
                return None

        return None

    def list_vacancies(self) -> List[VacancyResponse]:
        """Retorna todas las vacantes almacenadas."""
        return list(self._db.values())


# Instancia única del servicio
vacancy_service = VacancyService()
