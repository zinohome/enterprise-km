"""权限过滤 — 搜索结果按用户权限过滤"""
from fastapi import Header, HTTPException
from typing import Tuple, List


def get_user_from_token(authorization: str = Header(None)) -> Tuple[str, List[str]]:
    """
    从 JWT token 解析 user_id 和 team_ids。
    简化版：直接解析 payload（生产环境应验证签名）。
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    token = authorization.replace("Bearer ", "")

    try:
        import base64
        import json

        # JWT payload is the second part
        parts = token.split(".")
        if len(parts) != 3:
            raise HTTPException(status_code=401, detail="Invalid token format")

        payload = parts[1]
        # Add padding
        payload += "=" * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        data = json.loads(decoded)

        user_id = data.get("sub", "")
        team_ids = data.get("teams", [])

        return user_id, team_ids

    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_visibility_filter(user_id: str, team_ids: List[str]) -> List[str]:
    """
    构建 Meilisearch 权限过滤条件。
    用户可搜索：自己的文档 + 团队文档 + 公开文档。
    """
    filters = [f"visibility = public"]

    if user_id:
        filters.append(f"owner_id = {user_id}")

    if team_ids:
        team_conditions = " OR ".join([f"team_ids = {t}" for t in team_ids])
        filters.append(f"({team_conditions})")

    return filters
