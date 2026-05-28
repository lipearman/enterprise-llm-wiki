from fastapi import APIRouter, BackgroundTasks
from app.db.supabase_client import supabase
from app.jobs.runner import run_pending_jobs_once

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

@router.get("")
def list_jobs(limit: int = 50):
    res = supabase.table("job_runs").select("*").order("created_at", desc=True).limit(limit).execute()
    return {"items": res.data or []}

@router.post("/run-pending")
async def run_pending(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_pending_jobs_once, 10)
    return {"ok": True, "message": "pending jobs scheduled"}
