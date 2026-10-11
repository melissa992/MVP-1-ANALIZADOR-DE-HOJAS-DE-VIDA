from app.models.cv_schema import CandidateProfileSchema
from app.services.llm_extraction_service import llm_extraction_service

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
                normalized_profile = CandidateProfileSchema(**raw_extracted_dict)
                return normalized_profile

            except Exception as e:
                last_exception = e
                # Si falla, el ciclo permite reintentar hasta completar los 2 intentos adicionales
                continue

        # Si persisten los fallos tras los reintentos
        raise ValueError(f"HU-04 Error de estructuración: No se pudo normalizar el CV tras {max_retries} reintentos. Detalle: {str(last_exception)}")

normalization_service = NormalizationService()