from pydantic import BaseModel
from typing import Any, Optional

class ApiResponse(BaseModel):
    ok: bool = True
    data: Any | None = None
    message: str | None = None

class JobCreated(BaseModel):
    job_id: str
    status: str
