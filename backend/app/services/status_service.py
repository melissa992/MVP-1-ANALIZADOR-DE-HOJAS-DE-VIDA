from dataclasses import dataclass
from enum import Enum
from threading import Lock


class ProcessingStatus(str, Enum):
    PENDING = "PENDING"
    EXTRACTING = "EXTRACTING"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class FileStatus:
    file_id: str
    status: ProcessingStatus
    error_message: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "file_id": self.file_id,
            "status": self.status.value,
            "error_message": self.error_message,
        }


class StatusService:
    def __init__(self) -> None:
        self._statuses: dict[str, FileStatus] = {}
        self._lock = Lock()

    def register_file(self, file_id: str) -> FileStatus:
        file_status = FileStatus(file_id=file_id, status=ProcessingStatus.PENDING)
        with self._lock:
            self._statuses[file_id] = file_status
        return file_status

    def update_status(
        self,
        file_id: str,
        status: ProcessingStatus,
        error_message: str | None = None,
    ) -> FileStatus:
        file_status = FileStatus(
            file_id=file_id,
            status=status,
            error_message=error_message if status == ProcessingStatus.FAILED else None,
        )
        with self._lock:
            self._statuses[file_id] = file_status
        return file_status

    def get_status(self, file_id: str) -> FileStatus | None:
        with self._lock:
            return self._statuses.get(file_id)


status_service = StatusService()
