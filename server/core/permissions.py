from functools import wraps
from typing import Callable
from fastapi import HTTPException, Depends
from server.domain.user import User
from server.api.deps import get_current_user


def require_role(*roles: str) -> Callable:
    """装饰器：要求用户具有指定角色之一"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            if current_user.role not in roles:
                raise HTTPException(status_code=403, detail=f"Requires one of roles: {roles}")
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator


# 预定义角色快捷方式
require_admin = require_role("admin")
require_manager = require_role("admin", "manager")
require_editor = require_role("admin", "manager", "editor")
