import uuid
from datetime import datetime, timezone
from app.db.supabase_client import supabase
from app.core.config import settings


class JobService:
    def create_job(self, job_type: str, payload: dict, company_code: str | None = None) -> str:
        job_id = str(uuid.uuid4())
        supabase.table("job_runs").insert({
            "id": job_id,
            "job_type": job_type,
            "company_code": company_code or settings.DEFAULT_COMPANY_CODE,
            "status": "pending",
            "payload": payload,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        return job_id

    def update_job(self, job_id: str, status: str, message: str | None = None) -> None:
        supabase.table("job_runs").update({"status": status, "message": message}).eq("id", job_id).execute()

job_service = JobService()
