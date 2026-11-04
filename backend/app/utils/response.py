from typing import Any, Optional


def success(data: Any = None, message: str = "success", code: int = 200) -> dict:
    return {"code": code, "message": message, "data": data}


def error(message: str = "error", code: int = 400, data: Optional[Any] = None) -> dict:
    return {"code": code, "message": message, "data": data}
