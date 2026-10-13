from datetime import datetime, timezone
import json
import os
from typing import Dict, List, Optional, Union
import uuid
from uuid import UUID

from app.schemas.vacancy import VacancyCreate, VacancyResponse

DEFAULT_STORAGE_DIR = "temp_storage"


class VacancyService:
    """
    Servicio de lógica de negocio para la gestión de vacantes.
    Almacena las vacantes en memoria y las persiste como archivos JSON en 'temp_storage'.
    """

    def __init__(self, storage_dir: str = DEFAULT_STORAGE_DIR) -> None:
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self._db: Dict[str, VacancyResponse] = {}
        self._load_existing_vacancies()

    def _load_existing_vacancies(self) -> None:
        """
        Lee y sincroniza en memoria cualquier vacante registrada previamente en disco.
        """
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

        # 1. Guardar en memoria para acceso rápido
        self._db[str(vacancy_id)] = new_vacancy

        # 2. Guardar en disco en la carpeta temp_storage
        file_path = os.path.join(self.storage_dir, f"vacancy_{vacancy_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_vacancy.model_dump_json(indent=2))

        return new_vacancy

    def process_vacancy_requirements(self, vacancy_id: Union[UUID, str]) -> None:
        """
        Procesa y analiza los requisitos de la vacante utilizando LLM.
        """
        # TODO: Implementar en HU-06 con LLM
        pass

    def get_vacancy(self, vacancy_id: Union[UUID, str]) -> Optional[VacancyResponse]:
        """
        Consulta una vacante por su ID (desde memoria o cargando el archivo en disco).
        """
        vac_id_str = str(vacancy_id)
        if vac_id_str in self._db:
            return self._db[vac_id_str]

        # Si no estuviera en memoria, intentar leer directamente del archivo en temp_storage
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
        """
        Retorna todas las vacantes almacenadas.
        """
        return list(self._db.values())


# Instancia única del servicio
vacancy_service = VacancyService()
