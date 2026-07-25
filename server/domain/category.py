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


class KnowledgeCategory(BaseModel):
    id: Optional[str] = None
    name: str
    parent_id: Optional[str] = None
    description: Optional[str] = None
    sort_order: int = 0
    created_at: Optional[datetime] = None

    @classmethod
    async def create(cls, name: str, parent_id: str = None, description: str = None) -> "KnowledgeCategory":
        result = await db_query(
            "CREATE knowledge_category CONTENT { name: $name, parent_id: $parent_id, description: $description } RETURN AFTER;",
            {"name": name, "parent_id": parent_id, "description": description},
        )
        return cls(**_normalize(result[0]))

    @classmethod
    async def get_all(cls) -> list["KnowledgeCategory"]:
        result = await db_query("SELECT * FROM knowledge_category ORDER BY sort_order ASC;")
        return [cls(**_normalize(r)) for r in result]

    @classmethod
    async def get_tree(cls) -> list[dict]:
        all_cats = await cls.get_all()
        cat_map = {c.id: {**c.model_dump(), "children": []} for c in all_cats}
        roots = []
        for c in all_cats:
            if c.parent_id and c.parent_id in cat_map:
                cat_map[c.parent_id]["children"].append(cat_map[c.id])
            else:
                roots.append(cat_map[c.id])
        return roots

    async def update(self, **kwargs):
        result = await db_query("UPDATE $id MERGE $data RETURN AFTER;", {"id": self.id, "data": kwargs})
        for k, v in _normalize(result[0]).items():
            setattr(self, k, v)
        return self

    async def delete(self):
        await db_query("DELETE $id;", {"id": self.id})
