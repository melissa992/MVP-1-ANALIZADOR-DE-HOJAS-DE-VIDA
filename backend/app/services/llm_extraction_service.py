import json
import os
import time
from pathlib import Path

from google import genai
from google.genai import types
from dotenv import load_dotenv

from app.models.cv_schema import CandidateProfileSchema

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class LLMServiceUnavailable(RuntimeError):
    """Indica que el proveedor LLM no está disponible temporalmente."""


class LLMExtractionService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "Falta la variable de entorno GEMINI_API_KEY. Añádela al archivo .env o al entorno antes de usar el servicio LLM."
            )

        self.client = genai.Client(api_key=self.api_key)
        self.model = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
        self.max_attempts = int(os.getenv("GEMINI_MAX_ATTEMPTS", "3"))
        self.retry_delay_seconds = float(os.getenv("GEMINI_RETRY_DELAY_SECONDS", "2"))

    def extract_raw_cv_data(self, raw_text: str) -> dict:
        """
        HU-03: Utiliza el LLM para extraer la información clave del texto plano
        de la hoja de vida, asegurando que no se invente información.
        """
        system_prompt = (
            "Eres un experto extractor de datos de hojas de vida y analista de recursos humanos. "
            "Tu objetivo es analizar el texto plano de un CV heterogéneo y extraer la información clave "
            "estrictamente basada en el documento (nombre, correo, teléfono, ubicación, resumen, experiencia, educación, habilidades e idiomas). "
            "Devuelve exclusivamente un objeto JSON que cumpla exactamente este esquema: "
            f"{json.dumps(CandidateProfileSchema.model_json_schema(), ensure_ascii=False)}. "
            "Usa exactamente los nombres de las propiedades del esquema. "
            "En experiencia usa fecha_inicio, fecha_fin y funciones; no uses periodo ni tareas. "
            "Si un dato no está presente, asigna un valor null o una lista vacía. No inventes información."
        )

        for attempt in range(self.max_attempts):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=f"Analiza el siguiente texto de hoja de vida:\n\n{raw_text}",
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json",
                        temperature=0,
                    ),
                )

                content = response.text
                if not content:
                    raise ValueError("La respuesta del modelo está vacía.")

                if content.startswith("```"):
                    content = content.strip("`")
                    if content.startswith("json"):
                        content = content[4:]

                extracted_data = json.loads(content)
                if not isinstance(extracted_data, dict):
                    raise ValueError("La respuesta del modelo no es un objeto JSON válido.")

                return extracted_data

            except Exception as e:
                if not self._is_transient_error(e) or attempt == self.max_attempts - 1:
                    if self._is_transient_error(e):
                        raise LLMServiceUnavailable(
                            "HU-03 Gemini no está disponible temporalmente después de "
                            f"{self.max_attempts} intentos. Intenta nuevamente en unos minutos."
                        ) from e
                    raise RuntimeError(f"HU-03 Error al extraer información con el LLM: {str(e)}") from e

                time.sleep(self.retry_delay_seconds * (2**attempt))

        raise RuntimeError("HU-03 Error inesperado al extraer información con el LLM.")

    @staticmethod
    def _is_transient_error(error: Exception) -> bool:
        error_text = str(error).upper()
        status_code = getattr(error, "code", None) or getattr(error, "status_code", None)
        return status_code == 503 or "503" in error_text or "UNAVAILABLE" in error_text


llm_extraction_service = LLMExtractionService()