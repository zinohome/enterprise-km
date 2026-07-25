from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from server.core.database import db_query


def _normalize(record: dict) -> dict:
    if not isinstance(record, dict):
        return {}
    normalized = {}
    for k, v in record.items():
        if hasattr(v, "table_name") and hasattr(v, "id"):
            normalized[k] = str(v)
        else:
            normalized[k] = v
    return normalized


class Approval(BaseModel):
    id: Optional[str] = None
    source_id: str
    submitter_id: str
    reviewer_id: Optional[str] = None
    status: str = "pending"
    comment: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    async def create(cls, source_id: str, submitter_id: str) -> "Approval":
        result = await db_query(
            "CREATE approval CONTENT { source_id: $source_id, submitter_id: $submitter_id, status: 'pending' } RETURN AFTER;",
            {"source_id": source_id, "submitter_id": submitter_id},
        )
        return cls(**_normalize(result[0]))

    @classmethod
    async def get_pending(cls) -> list["Approval"]:
        result = await db_query("SELECT * FROM approval WHERE status = 'pending' ORDER BY created_at DESC;")
        return [cls(**_normalize(r)) for r in result]

    async def approve(self, reviewer_id: str, comment: str = None):
        result = await db_query(
            f"UPDATE {self.id} MERGE {{ status: 'approved', reviewer_id: $reviewer_id, comment: $comment, updated_at: time::now() }} RETURN AFTER;",
            {"reviewer_id": reviewer_id, "comment": comment},
        )
        for k, v in _normalize(result[0]).items():
            setattr(self, k, v)
        return self

    async def reject(self, reviewer_id: str, comment: str):
        result = await db_query(
            f"UPDATE {self.id} MERGE {{ status: 'rejected', reviewer_id: $reviewer_id, comment: $comment, updated_at: time::now() }} RETURN AFTER;",
            {"reviewer_id": reviewer_id, "comment": comment},
        )
        for k, v in _normalize(result[0]).items():
            setattr(self, k, v)
        return self
