from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, field_validator
from server.core.database import db_query
from server.core.security import hash_password, verify_password


def _normalize_record(record: dict) -> dict:
    """Convert SurrealDB RecordID objects to strings."""
    if not isinstance(record, dict):
        return {}
    normalized = {}
    for k, v in record.items():
        if hasattr(v, 'table_name') and hasattr(v, 'id'):
            normalized[k] = str(v)
        else:
            normalized[k] = v
    return normalized


class User(BaseModel):
    id: Optional[str] = None
    username: str
    password_hash: Optional[str] = None
    email: str
    display_name: str
    role: str = "viewer"
    department: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    async def create(cls, username: str, email: str, password: str, display_name: str) -> "User":
        password_hash = hash_password(password)
        result = await db_query(
            "CREATE user CONTENT { username: $username, email: $email, password_hash: $password_hash, display_name: $display_name, role: 'viewer' } RETURN AFTER;",
            {"username": username, "email": email, "password_hash": password_hash, "display_name": display_name}
        )
        return cls(**_normalize_record(result[0]))

    @classmethod
    async def get_by_username(cls, username: str) -> Optional["User"]:
        result = await db_query(
            "SELECT * FROM user WHERE username = $username LIMIT 1;",
            {"username": username}
        )
        return cls(**_normalize_record(result[0])) if result else None

    @classmethod
    async def get_by_id(cls, user_id: str) -> Optional["User"]:
        result = await db_query("SELECT * FROM $id;", {"id": user_id})
        if not result:
            return None
        record = result[0]
        if isinstance(record, str):
            # SurrealDB sometimes returns just the id string for single-record queries
            # Re-query with full SELECT
            result = await db_query(f"SELECT * FROM {record};")
            record = result[0] if result else None
            if not record:
                return None
        return cls(**_normalize_record(record))

    @classmethod
    async def get_all(cls) -> list["User"]:
        result = await db_query("SELECT * FROM user ORDER BY created_at DESC;")
        return [cls(**_normalize_record(r)) for r in result]

    async def verify_password(self, password: str) -> bool:
        return verify_password(password, self.password_hash or "")

    async def update(self, **kwargs) -> "User":
        kwargs["updated_at"] = datetime.now()
        result = await db_query(
            "UPDATE $id MERGE $data RETURN AFTER;",
            {"id": self.id, "data": kwargs}
        )
        for k, v in _normalize_record(result[0]).items():
            setattr(self, k, v)
        return self

    async def delete(self) -> bool:
        await db_query("DELETE $id;", {"id": self.id})
        return True
