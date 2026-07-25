from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from server.domain.category import KnowledgeCategory
from server.api.deps import get_current_user
from server.domain.user import User

router = APIRouter(prefix="/categories", tags=["categories"])


class CategoryCreate(BaseModel):
    name: str
    parent_id: Optional[str] = None
    description: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None


@router.get("")
async def list_categories(current_user: User = Depends(get_current_user)):
    categories = await KnowledgeCategory.get_all()
    return [c.model_dump() for c in categories]


@router.get("/tree")
async def get_tree(current_user: User = Depends(get_current_user)):
    return await KnowledgeCategory.get_tree()


@router.post("")
async def create_category(data: CategoryCreate, current_user: User = Depends(get_current_user)):
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Permission denied")
    cat = await KnowledgeCategory.create(name=data.name, parent_id=data.parent_id, description=data.description)
    return cat.model_dump()


@router.put("/{category_id}")
async def update_category(category_id: str, data: CategoryUpdate, current_user: User = Depends(get_current_user)):
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Permission denied")
    cat = KnowledgeCategory(id=category_id, name="")
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    await cat.update(**update_data)
    return cat.model_dump()


@router.delete("/{category_id}")
async def delete_category(category_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    cat = KnowledgeCategory(id=category_id, name="")
    await cat.delete()
    return {"message": "Deleted"}
