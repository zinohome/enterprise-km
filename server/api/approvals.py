from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from server.domain.approval import Approval
from server.domain.user import User
from server.api.deps import get_current_user

router = APIRouter(prefix="/approvals", tags=["approvals"])


class ApprovalCreate(BaseModel):
    source_id: str


class ApprovalAction(BaseModel):
    comment: Optional[str] = None


@router.post("")
async def create_approval(data: ApprovalCreate, current_user: User = Depends(get_current_user)):
    approval = await Approval.create(source_id=data.source_id, submitter_id=current_user.id)
    return approval.model_dump()


@router.get("")
async def list_approvals(current_user: User = Depends(get_current_user)):
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Permission denied")
    approvals = await Approval.get_pending()
    return [a.model_dump() for a in approvals]


@router.post("/{approval_id}/approve")
async def approve(approval_id: str, data: ApprovalAction, current_user: User = Depends(get_current_user)):
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Permission denied")
    approval = Approval(id=approval_id, source_id="", submitter_id="")
    await approval.approve(reviewer_id=current_user.id, comment=data.comment)
    return approval.model_dump()


@router.post("/{approval_id}/reject")
async def reject(approval_id: str, data: ApprovalAction, current_user: User = Depends(get_current_user)):
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Permission denied")
    approval = Approval(id=approval_id, source_id="", submitter_id="")
    await approval.reject(reviewer_id=current_user.id, comment=data.comment or "")
    return approval.model_dump()
