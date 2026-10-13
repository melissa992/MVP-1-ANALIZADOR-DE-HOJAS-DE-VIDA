import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.schemas.matching import MatchBreakdown, MatchResponse

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

_MISSING_EVIDENCE = "Sin evidencia en el CV."
_CATEGORY_MAXIMA = {
    "habilidades": 40,
    "experiencia": 40,
    "educacion": 10,
    "idiomas": 10,
}

_EVALUATOR_SYSTEM_PROMPT = """Eres un evaluador objetivo de compatibilidad laboral.
Evalúa únicamente requisitos de la vacante usando datos presentes en el perfil del candidato.
No inventes experiencia, formación, habilidades, idiomas ni evidencias. No presentes una
inferencia como un hecho. Para cada requisito, usa una sola de estas categorías:
- "habilidades": habilidades_clave de la vacante.
- "experiencia": cargo y años de experiencia requeridos.
- "educacion": nivel_estudios requerido.
- "idiomas": idiomas requeridos.

Incluye cada requisito de la vacante exactamente una vez en una de estas listas:
- requirements_met: evidencia suficiente y explícita.
- requirements_partial: evidencia explícita que solo cubre parcialmente el requisito.
- requirements_missing: no hay evidencia suficiente en el CV.

En "requirement" copia exactamente el texto del requisito de la vacante. Para años de
experiencia usa el formato "<n> años de experiencia"; para el cargo usa "Cargo: <texto>".
En "evidence", cita literalmente un fragmento breve del JSON del candidato para requisitos
cumplidos o parciales. Si falta evidencia, escribe exactamente "Sin evidencia en el CV.".
No uses la descripción de la vacante como evidencia del candidato.

Escribe una justificación breve en español, de máximo cinco líneas. Cada afirmación sobre
el candidato debe estar respaldada por datos del CV. No devuelvas puntajes: los calculará
el sistema a partir del estado de los requisitos.

Responde ÚNICAMENTE en formato JSON, sin texto adicional ni markdown, con esta estructura:
{
  "justification": "<máximo cinco líneas>",
  "requirements_met": [{"category": "<categoría>", "requirement": "<texto exacto>", "evidence": "<cita del CV>"}],
  "requirements_partial": [{"category": "<categoría>", "requirement": "<texto exacto>", "evidence": "<cita del CV>"}],
  "requirements_missing": [{"category": "<categoría>", "requirement": "<texto exacto>", "evidence": "Sin evidencia en el CV."}]
}"""


class MatchingService:
    """HU-07 / HU-08: calcula el score y presenta desglose y evidencia del matching."""

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
        """Evalúa el ajuste y devuelve puntajes parciales, estados y evidencia."""
        if not candidate_data:
            raise ValueError("El perfil del candidato no puede estar vacío.")
        if not vacancy_data:
            raise ValueError("Los datos de la vacante no pueden estar vacíos.")

        expected_requirements = self._expected_requirements(vacancy_data)
        user_message = (
            "Evalúa la compatibilidad entre el siguiente candidato y vacante:\n\n"
            f"=== PERFIL DEL CANDIDATO ===\n{json.dumps(candidate_data, ensure_ascii=False, indent=2)}\n\n"
            f"=== REQUISITOS DE LA VACANTE ===\n{json.dumps(vacancy_data, ensure_ascii=False, indent=2)}\n\n"
            "Responde exclusivamente con el JSON indicado."
        )

        for attempt in range(self.max_attempts):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=user_message,
                    config=types.GenerateContentConfig(
                        system_instruction=_EVALUATOR_SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        temperature=0,
                    ),
                )

                content = response.text
                if not content or not content.strip():
                    raise ValueError("La respuesta del modelo Gemini está vacía.")

                content_clean = content.strip()
                if content_clean.startswith("```"):
                    content_clean = content_clean.strip("`")
                    if content_clean.startswith("json"):
                        content_clean = content_clean[4:].strip()

                parsed = json.loads(content_clean)
                if not isinstance(parsed, dict):
                    raise ValueError("La respuesta del modelo no es un objeto JSON válido.")

                self._validate_requirement_evidence(
                    parsed, expected_requirements, candidate_data
                )
                breakdown = self._calculate_breakdown(parsed)
                parsed["breakdown"] = breakdown
                parsed["score"] = sum(
                    getattr(breakdown, category).score
                    for category in _CATEGORY_MAXIMA
                )
                return MatchResponse(**parsed)

            except Exception as error:
                is_last = attempt == self.max_attempts - 1
                if not self._is_transient_error(error) or is_last:
                    raise RuntimeError(
                        "HU-08 Error al generar un resultado verificable del matching: "
                        f"{error}"
                    ) from error
                time.sleep(self.retry_delay_seconds * (2**attempt))

        raise RuntimeError("HU-08 Error inesperado al calcular el score de idoneidad.")

    @staticmethod
    def _expected_requirements(vacancy_data: dict) -> set[tuple[str, str]]:
        expected: set[tuple[str, str]] = set()

        skills = vacancy_data.get("habilidades_clave", [])
        if isinstance(skills, list):
            expected.update(
                ("habilidades", str(skill).strip())
                for skill in skills
                if skill is not None and str(skill).strip()
            )

        cargo = vacancy_data.get("cargo")
        if isinstance(cargo, str) and cargo.strip():
            expected.add(("experiencia", f"Cargo: {cargo.strip()}"))

        years = vacancy_data.get("anios_experiencia_requeridos", 0)
        try:
            years = float(years)
        except (TypeError, ValueError):
            years = 0
        if years > 0:
            years_label = int(years) if years.is_integer() else years
            expected.add(("experiencia", f"{years_label} años de experiencia"))

        education = vacancy_data.get("nivel_estudios")
        if (
            isinstance(education, str)
            and education.strip()
            and education.strip().casefold() != "no especificado"
        ):
            expected.add(("educacion", education.strip()))

        languages = vacancy_data.get("idiomas", [])
        if isinstance(languages, list):
            expected.update(
                ("idiomas", str(language).strip())
                for language in languages
                if language is not None and str(language).strip()
            )

        return expected

    @staticmethod
    def _candidate_text_values(candidate_data: dict) -> list[str]:
        values: list[str] = []

        def collect(value) -> None:
            if isinstance(value, dict):
                for nested_value in value.values():
                    collect(nested_value)
            elif isinstance(value, list):
                for nested_value in value:
                    collect(nested_value)
            elif isinstance(value, (str, int, float)) and not isinstance(value, bool):
                text = str(value).strip()
                if text:
                    values.append(text)

        collect(candidate_data)
        return values

    @classmethod
    def _validate_requirement_evidence(
        cls,
        parsed: dict,
        expected_requirements: set[tuple[str, str]],
        candidate_data: dict,
    ) -> None:
        matched_requirements: set[tuple[str, str]] = set()
        candidate_text = "\n".join(cls._candidate_text_values(candidate_data)).casefold()

        for status in (
            "requirements_met",
            "requirements_partial",
            "requirements_missing",
        ):
            items = parsed.get(status)
            if not isinstance(items, list):
                raise ValueError(f"{status} debe ser una lista.")

            for item in items:
                if not isinstance(item, dict):
                    raise ValueError(f"Cada elemento de {status} debe ser un objeto.")
                key = (item.get("category"), item.get("requirement"))
                if key not in expected_requirements:
                    raise ValueError(
                        f"El modelo devolvió un requisito que no está en la vacante: {key}."
                    )
                if key in matched_requirements:
                    raise ValueError(f"El requisito {key} aparece más de una vez.")
                matched_requirements.add(key)

                evidence = item.get("evidence")
                if not isinstance(evidence, str) or not evidence.strip():
                    raise ValueError(f"Falta evidencia para el requisito {key}.")
                if status == "requirements_missing":
                    if evidence.strip() != _MISSING_EVIDENCE:
                        raise ValueError(
                            f"Un requisito faltante debe usar la evidencia "
                            f"'{_MISSING_EVIDENCE}'."
                        )
                elif evidence.strip().casefold() not in candidate_text:
                    raise ValueError(
                        f"La evidencia del requisito {key} no aparece literalmente "
                        "en el perfil del candidato."
                    )

        if matched_requirements != expected_requirements:
            missing = expected_requirements - matched_requirements
            raise ValueError(f"El modelo omitió requisitos de la vacante: {sorted(missing)}.")

    @staticmethod
    def _calculate_breakdown(parsed: dict) -> MatchBreakdown:
        entries_by_category = {
            category: {"met": 0, "partial": 0}
            for category in _CATEGORY_MAXIMA
        }
        totals_by_category = {category: 0 for category in _CATEGORY_MAXIMA}

        for status, weight in (("requirements_met", 1), ("requirements_partial", 0.5)):
            for item in parsed[status]:
                category = item["category"]
                entries_by_category[category][
                    "met" if weight == 1 else "partial"
                ] += 1
                totals_by_category[category] += 1

        for item in parsed["requirements_missing"]:
            totals_by_category[item["category"]] += 1

        category_scores = {}
        for category, maximum in _CATEGORY_MAXIMA.items():
            total = totals_by_category[category]
            earned = (
                entries_by_category[category]["met"]
                + 0.5 * entries_by_category[category]["partial"]
            )
            score = maximum if total == 0 else int(maximum * earned / total + 0.5)
            category_scores[category] = {"score": score, "max_score": maximum}

        return MatchBreakdown(**category_scores)

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


matching_service = MatchingService()
