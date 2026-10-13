from typing import Any

from app.models.cv_schema import CandidateProfileSchema
from app.services.llm_extraction_service import LLMServiceUnavailable, llm_extraction_service


class NormalizationService:
    def process_and_normalize(self, raw_text: str) -> CandidateProfileSchema:
        """
        HU-04: Toma la salida de la HU-03, la valida contra el esquema JSON estándar 
        y reintenta hasta 2 veces si el formato falla.
        """
        max_retries = 2
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                # Paso 1 (HU-03): Extracción cruda con LLM
                raw_extracted_dict = llm_extraction_service.extract_raw_cv_data(raw_text)

                # Paso 2 (HU-04): Validación y normalización estricta mediante Pydantic
                normalized_profile = CandidateProfileSchema(**self._normalize_aliases(raw_extracted_dict))
                return normalized_profile

            except Exception as e:
                if isinstance(e, LLMServiceUnavailable):
                    raise
                last_exception = e
                # Si falla, el ciclo permite reintentar hasta completar los 2 intentos adicionales
                continue

        # Si persisten los fallos tras los reintentos
        raise ValueError(f"HU-04 Error de estructuración: No se pudo normalizar el CV tras {max_retries} reintentos. Detalle: {str(last_exception)}")

    @staticmethod
    def _normalize_aliases(data: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(data)

        if isinstance(normalized.get("ubicacion"), dict):
            location = normalized["ubicacion"]
            normalized["ubicacion"] = ", ".join(
                str(location[field]).strip()
                for field in ("direccion", "ciudad", "municipio", "departamento", "pais")
                if location.get(field)
            ) or None

        for item in normalized.get("experiencia", []):
            if not isinstance(item, dict):
                continue

            if "periodo" in item:
                start, separator, end = str(item.pop("periodo")).partition("-")
                if separator:
                    item.setdefault("fecha_inicio", start.strip())
                    item.setdefault("fecha_fin", end.strip())

            if "tareas" in item and "funciones" not in item:
                tareas = item.pop("tareas")
                item["funciones"] = (
                    [tareas] if isinstance(tareas, str) else tareas or []
                )

        return normalized

normalization_service = NormalizationService()