from typing import Any

from pydantic import BaseModel


class ApiResponse[DataT](BaseModel):
    success: bool = True
    data: DataT
    request_id: str


def success_response(request_id: str, data: Any) -> dict[str, Any]:
    return {"success": True, "data": data, "request_id": request_id}
