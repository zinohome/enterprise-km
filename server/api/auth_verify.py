from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from server.core.security import decode_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/verify")
async def verify_token(request: Request):
    """Nginx auth_request endpoint. Returns 200 with X-User-ID header if valid, 401 otherwise."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = auth_header[7:]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub", "unknown")
    response = JSONResponse({"status": "ok", "user_id": user_id})
    response.headers["X-User-ID"] = user_id
    return response
