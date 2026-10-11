import json
import os

from openai import OpenAI


class LLMExtractionService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "Falta la variable de entorno OPENAI_API_KEY. Añádela al archivo .env o al entorno antes de usar el servicio LLM."
            )

        self.client = OpenAI(api_key=self.api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def extract_raw_cv_data(self, raw_text: str) -> dict:
        """
        HU-03: Utiliza el LLM para extraer la información clave del texto plano
        de la hoja de vida, asegurando que no se invente información.
        """
        system_prompt = (
            "Eres un experto extractor de datos de hojas de vida y analista de recursos humanos. "
            "Tu objetivo es analizar el texto plano de un CV heterogéneo y extraer la información clave "
            "estrictamente basada en el documento (datos de contacto, resumen, experiencia, educación, habilidades e idiomas). "
            "Si un dato no está presente, asigna un valor null o una lista vacía. No inventes información."
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analiza el siguiente texto de hoja de vida:\n\n{raw_text}"},
                ],
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("La respuesta del modelo está vacía.")

            extracted_data = json.loads(content)
            if not isinstance(extracted_data, dict):
                raise ValueError("La respuesta del modelo no es un objeto JSON válido.")

            return extracted_data

        except Exception as e:
            raise RuntimeError(f"HU-03 Error al extraer información con el LLM: {str(e)}") from e


llm_extraction_service = LLMExtractionService()