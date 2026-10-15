import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Generator

import jwt
from dotenv import load_dotenv
from passlib.context import CryptContext
from app.storage import STORAGE_DIR

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

_PASSWORD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")
_TOKEN_ALGORITHM = "HS256"
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_BOOTSTRAP_EMAIL = os.getenv("INITIAL_RECRUITER_EMAIL", "").strip().casefold()
_BOOTSTRAP_PASSWORD = os.getenv("INITIAL_RECRUITER_PASSWORD", "")
_TOKEN_SECRET = os.getenv("JWT_SECRET_KEY", "")
_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
_DATABASE_PATH = Path(
    os.getenv(
        "AUTH_DATABASE_PATH",
        str(Path(__file__).resolve().parents[2] / "auth.sqlite3"),
    )
)


@dataclass(frozen=True)
class ActiveUser:
    id: str
    email: str


class AuthService:
    def __init__(
        self,
        database_path: Path = _DATABASE_PATH,
        token_secret: str = _TOKEN_SECRET,
        bootstrap_email: str = _BOOTSTRAP_EMAIL,
        bootstrap_password: str = _BOOTSTRAP_PASSWORD,
        token_expire_minutes: int = _TOKEN_EXPIRE_MINUTES,
    ) -> None:
        if not _EMAIL_PATTERN.fullmatch(bootstrap_email):
            raise RuntimeError(
                "Configura INITIAL_RECRUITER_EMAIL con un correo válido antes de iniciar la API."
            )
        if not 12 <= len(bootstrap_password.encode("utf-8")) <= 72:
            raise RuntimeError(
                "INITIAL_RECRUITER_PASSWORD debe tener entre 12 y 72 bytes UTF-8."
            )
        if len(token_secret.encode("utf-8")) < 32:
            raise RuntimeError(
                "JWT_SECRET_KEY debe tener al menos 32 bytes aleatorios."
            )
        if token_expire_minutes < 1:
            raise RuntimeError("JWT_ACCESS_TOKEN_EXPIRE_MINUTES debe ser positivo.")

        self.database_path = Path(database_path)
        self.token_secret = token_secret
        self.bootstrap_email = bootstrap_email
        self.token_expire_minutes = token_expire_minutes
        self.bootstrap_user_id = str(
            uuid.uuid5(uuid.NAMESPACE_URL, f"cv-match-user:{bootstrap_email}")
        )
        self.initialize(bootstrap_password)

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self, bootstrap_password: str) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id),
                    expires_at INTEGER NOT NULL,
                    revoked INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS resource_owners (
                    resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    user_id TEXT NOT NULL REFERENCES users(id),
                    PRIMARY KEY (resource_type, resource_id)
                );
                """
            )
            existing_user = connection.execute(
                "SELECT id, password_hash FROM users WHERE email = ?",
                (self.bootstrap_email,),
            ).fetchone()
            if existing_user is None:
                connection.execute(
                    """
                    INSERT INTO users (id, email, password_hash)
                    VALUES (?, ?, ?)
                    """,
                    (
                        self.bootstrap_user_id,
                        self.bootstrap_email,
                        self.hash_password(bootstrap_password),
                    ),
                )
            elif not _PASSWORD_CONTEXT.verify(
                bootstrap_password, existing_user["password_hash"]
            ):
                connection.execute(
                    "UPDATE users SET password_hash = ? WHERE id = ?",
                    (self.hash_password(bootstrap_password), existing_user["id"]),
                )
                connection.execute(
                    "UPDATE sessions SET revoked = 1 WHERE user_id = ?",
                    (existing_user["id"],),
                )

    @staticmethod
    def hash_password(password: str) -> str:
        if not 12 <= len(password.encode("utf-8")) <= 72:
            raise ValueError("La contraseña debe tener entre 12 y 72 bytes UTF-8.")
        return _PASSWORD_CONTEXT.hash(password)

    @staticmethod
    def _user_from_row(row: sqlite3.Row | None) -> ActiveUser | None:
        if row is None:
            return None
        return ActiveUser(id=row["id"], email=row["email"])

    def authenticate(self, email: str, password: str) -> ActiveUser | None:
        normalized_email = email.strip().casefold()
        if (
            not _EMAIL_PATTERN.fullmatch(normalized_email)
            or len(password.encode("utf-8")) > 72
        ):
            return None
        with self._connection() as connection:
            row = connection.execute(
                "SELECT id, email, password_hash, is_active FROM users WHERE email = ?",
                (normalized_email,),
            ).fetchone()
        if (
            row is None
            or not row["is_active"]
            or not _PASSWORD_CONTEXT.verify(password, row["password_hash"])
        ):
            return None
        return self._user_from_row(row)

    def create_access_token(self, user: ActiveUser) -> tuple[str, str, int]:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=self.token_expire_minutes)
        token_id = str(uuid.uuid4())
        token = jwt.encode(
            {
                "sub": user.id,
                "email": user.email,
                "jti": token_id,
                "iat": now,
                "exp": expires_at,
            },
            self.token_secret,
            algorithm=_TOKEN_ALGORITHM,
        )
        with self._connection() as connection:
            connection.execute(
                "DELETE FROM sessions WHERE expires_at <= ? OR revoked = 1",
                (int(now.timestamp()),),
            )
            connection.execute(
                "INSERT INTO sessions (token_id, user_id, expires_at) VALUES (?, ?, ?)",
                (token_id, user.id, int(expires_at.timestamp())),
            )
        return token, token_id, int(expires_at.timestamp())

    def get_session_user(self, token: str) -> ActiveUser | None:
        try:
            payload = jwt.decode(
                token,
                self.token_secret,
                algorithms=[_TOKEN_ALGORITHM],
                options={"require": ["exp", "iat", "sub", "jti"]},
            )
        except jwt.InvalidTokenError:
            return None

        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT users.id, users.email
                FROM sessions
                JOIN users ON users.id = sessions.user_id
                WHERE sessions.token_id = ?
                  AND sessions.user_id = ?
                  AND sessions.revoked = 0
                  AND sessions.expires_at > ?
                  AND users.is_active = 1
                """,
                (payload["jti"], payload["sub"], int(datetime.now(timezone.utc).timestamp())),
            ).fetchone()
        return self._user_from_row(row)

    def revoke_session(self, token_id: str, user_id: str) -> None:
        with self._connection() as connection:
            connection.execute(
                "UPDATE sessions SET revoked = 1 WHERE token_id = ? AND user_id = ?",
                (token_id, user_id),
            )

    def get_token_id(self, token: str) -> str | None:
        try:
            payload = jwt.decode(
                token,
                self.token_secret,
                algorithms=[_TOKEN_ALGORITHM],
                options={"verify_exp": False, "require": ["jti"]},
            )
        except jwt.InvalidTokenError:
            return None
        token_id = payload.get("jti")
        return token_id if isinstance(token_id, str) else None

    def assign_resource(self, resource_type: str, resource_id: str, user_id: str) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO resource_owners (resource_type, resource_id, user_id)
                VALUES (?, ?, ?)
                ON CONFLICT (resource_type, resource_id) DO NOTHING
                """,
                (resource_type, resource_id, user_id),
            )

    def owns_resource(self, resource_type: str, resource_id: str, user_id: str) -> bool:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT 1 FROM resource_owners
                WHERE resource_type = ? AND resource_id = ? AND user_id = ?
                """,
                (resource_type, resource_id, user_id),
            ).fetchone()
        return row is not None

    def list_owned_resource_ids(self, resource_type: str, user_id: str) -> set[str]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT resource_id FROM resource_owners
                WHERE resource_type = ? AND user_id = ?
                """,
                (resource_type, user_id),
            ).fetchall()
        return {row["resource_id"] for row in rows}

    def assign_legacy_resources(self, storage_directories: set[Path]) -> None:
        for directory in storage_directories:
            if not directory.is_dir():
                continue
            for file_path in directory.iterdir():
                if file_path.suffix.lower() == ".pdf":
                    resource_type, resource_id = "cv", file_path.stem
                elif file_path.name.startswith("vacancy_") and file_path.suffix == ".json":
                    resource_type, resource_id = "vacancy", file_path.stem.removeprefix("vacancy_")
                elif file_path.name.startswith("ranking_") and file_path.suffix == ".json":
                    resource_type, resource_id = "ranking", file_path.stem
                else:
                    continue
                self.assign_resource(resource_type, resource_id, self.bootstrap_user_id)


auth_service = AuthService()
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_REPOSITORY_DIR = _BACKEND_DIR.parent
auth_service.assign_legacy_resources(
    {
        Path.cwd() / "temp_storage",
        _BACKEND_DIR / "temp_storage",
        _REPOSITORY_DIR / "temp_storage",
        STORAGE_DIR,
    }
)
