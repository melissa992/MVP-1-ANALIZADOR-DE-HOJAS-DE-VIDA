import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.schemas.matching import MatchRequest, MatchResponse

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# System prompt del evaluador con ponderación estricta (HU-07)
_EVALUATOR_SYSTEM_PROMPT = """Eres un motor de matching algorítmico y objetivo de Recursos Humanos.
Tu tarea es evaluar la compatibilidad entre el perfil JSON de un candidato y los requisitos JSON de una vacante.

Aplica la siguiente ponderación estricta (Total 100%):
- Años de Experiencia y Cargo: 40%  → máximo 40 puntos
- Habilidades Técnicas Clave: 40%   → máximo 40 puntos
- Nivel de Estudios e Idiomas: 20%  → máximo 20 puntos

REGLAS DE EVALUACIÓN:
1. Experiencia/Cargo (0-40 pts): Compara el cargo objetivo del candidato con el cargo requerido, y los años de experiencia del candidato con los requeridos. Proporcional: si cumple exactamente, máximo 40 pts. Si supera, 40 pts. Si no alcanza, resta proporcionalmente.
2. Habilidades Técnicas (0-40 pts): Cuenta cuántas habilidades_clave de la vacante aparecen en las habilidades del candidato (coincidencia exacta o semánticamente equivalente). Proporcional al porcentaje cubierto × 40.
3. Estudios/Idiomas (0-20 pts): 10 pts por nivel de estudios (cumple o no), 10 pts por idiomas (proporcional a los cubiertos).

El score total = suma de los tres subpuntajes. Redondea al entero más cercano.

Responde ÚNICAMENTE en formato JSON con la siguiente estructura exacta (sin texto adicional, sin markdown):
{
  "score": <int 0-100>,
  "justification": "<string con análisis narrativo detallado en español, mencionando los tres ejes>",
  "breakdown": {
    "experiencia_cargo": <int 0-40>,
    "habilidades_tecnicas": <int 0-40>,
    "estudios_idiomas": <int 0-20>
  }
}"""


class MatchingService:
    """
    HU-07: Servicio que calcula el score de idoneidad (fit score)
    entre un candidato y una vacante usando Google Gemini con temperature=0.
    """

    def __init__(self) -> None:
        self._client: genai.Client | None = None
        self.model = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
        self.max_attempts = int(os.getenv("GEMINI_MAX_ATTEMPTS", "3"))
        self.retry_delay_seconds = float(os.getenv("GEMINI_RETRY_DELAY_SECONDS", "2"))

    @property
    def client(self) -> genai.Client:
        """Inicializa o retorna la instancia del cliente Gemini (lazy init)."""
        if self._client is None:
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "Falta la variable de entorno GEMINI_API_KEY. "
                    "Configúrala en el archivo .env antes de usar el Matching Engine."
                )
            self._client = genai.Client(api_key=api_key)
        return self._client

    @client.setter
    def client(self, value: genai.Client) -> None:
        self._client = value

    def calculate_fit_score(
        self, candidate_data: dict, vacancy_data: dict
    ) -> MatchResponse:
        """
        HU-07: Evalúa la compatibilidad candidato-vacante y devuelve
        un score numérico (0-100) con justificación y desglose por eje.

        Args:
            candidate_data: Perfil estructurado del candidato (HU-04).
            vacancy_data: Requisitos estructurados de la vacante (HU-06).

        Returns:
            MatchResponse con score, justification y breakdown.

        Raises:
            RuntimeError: Si el LLM falla después de los reintentos configurados.
            ValueError: Si los datos de entrada son inválidos o vacíos.
        """
        if not candidate_data:
            raise ValueError("El perfil del candidato no puede estar vacío.")
        if not vacancy_data:
            raise ValueError("Los datos de la vacante no pueden estar vacíos.")

        user_message = (
            "Evalúa la compatibilidad entre el siguiente candidato y vacante:\n\n"
            f"=== PERFIL DEL CANDIDATO ===\n{json.dumps(candidate_data, ensure_ascii=False, indent=2)}\n\n"
            f"=== REQUISITOS DE LA VACANTE ===\n{json.dumps(vacancy_data, ensure_ascii=False, indent=2)}\n\n"
            "Responde exclusivamente con el JSON de evaluación."
        )

        for attempt in range(self.max_attempts):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=user_message,
                    config=types.GenerateContentConfig(
                        system_instruction=_EVALUATOR_SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        temperature=0,  # Máxima consistencia / determinismo
                    ),
                )

                content = response.text
                if not content or not content.strip():
                    raise ValueError(
                        "La respuesta del modelo Gemini está vacía."
                    )

                # Limpieza defensiva de bloques markdown que Gemini a veces añade
                content_clean = content.strip()
                if content_clean.startswith("```"):
                    content_clean = content_clean.strip("`")
                    if content_clean.startswith("json"):
                        content_clean = content_clean[4:].strip()

                parsed = json.loads(content_clean)
                if not isinstance(parsed, dict):
                    raise ValueError(
                        "La respuesta del modelo no es un objeto JSON válido."
                    )

                # Normalizar y validar score dentro del rango 0-100
                raw_score = int(parsed.get("score", 0))
                parsed["score"] = max(0, min(100, raw_score))

                # Normalizar breakdown si existe
                breakdown = parsed.get("breakdown", {})
                if breakdown:
                    breakdown["experiencia_cargo"] = max(
                        0, min(40, int(breakdown.get("experiencia_cargo", 0)))
                    )
                    breakdown["habilidades_tecnicas"] = max(
                        0, min(40, int(breakdown.get("habilidades_tecnicas", 0)))
                    )
                    breakdown["estudios_idiomas"] = max(
                        0, min(20, int(breakdown.get("estudios_idiomas", 0)))
                    )
                    parsed["breakdown"] = breakdown

                return MatchResponse(**parsed)

            except Exception as e:
                is_last = attempt == self.max_attempts - 1
                if not self._is_transient_error(e) or is_last:
                    raise RuntimeError(
                        f"HU-07 Error al calcular el score de idoneidad con Gemini: {str(e)}"
                    ) from e
                time.sleep(self.retry_delay_seconds * (2**attempt))

        raise RuntimeError(
            "HU-07 Error inesperado al calcular el score de idoneidad."
        )

    @staticmethod
    def _is_transient_error(error: Exception) -> bool:
        """Identifica errores transitorios que justifican un reintento."""
        error_text = str(error).upper()
        status_code = getattr(error, "code", None) or getattr(error, "status_code", None)
        return (
            status_code == 503
            or "503" in error_text
            or "UNAVAILABLE" in error_text
            or "RATE_LIMIT" in error_text
            or "RESOURCE_EXHAUSTED" in error_text
        )


# Singleton del servicio de matching
matching_service = MatchingService()
