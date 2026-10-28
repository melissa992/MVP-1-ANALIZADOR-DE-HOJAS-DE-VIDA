import os

import httpx


class ElevenLabsServiceUnavailable(RuntimeError):
    """El proveedor ElevenLabs no está disponible o no está configurado."""


class ElevenLabsService:
    def __init__(self) -> None:
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
        self.model = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")

    def synthesize(self, text: str) -> bytes:
        api_key = os.getenv("ELEVENLABS_API_KEY") or self.api_key
        if not api_key:
            raise ElevenLabsServiceUnavailable(
                "Falta la variable de entorno ELEVENLABS_API_KEY para sintetizar voz."
            )

        try:
            response = httpx.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}",
                params={"output_format": "mp3_44100_128"},
                headers={
                    "xi-api-key": api_key,
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": self.model,
                    "voice_settings": {
                        "stability": 0.48,
                        "similarity_boost": 0.78,
                    },
                },
                timeout=30.0,
            )
        except httpx.HTTPError as error:
            raise ElevenLabsServiceUnavailable(
                "No fue posible conectar con ElevenLabs. Intenta nuevamente."
            ) from error

        if response.is_error:
            raise ElevenLabsServiceUnavailable(
                f"ElevenLabs rechazó la solicitud de voz (HTTP {response.status_code})."
            )
        if not response.content:
            raise ElevenLabsServiceUnavailable(
                "ElevenLabs devolvió una respuesta de audio vacía."
            )
        return response.content


elevenlabs_service = ElevenLabsService()
