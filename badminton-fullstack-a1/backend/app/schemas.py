from pydantic import BaseModel
from typing import Any, Optional, Dict, List

class CreateJobResponse(BaseModel):
    job_id: str
    run_id: str

class JobStatusResponse(BaseModel):
    job_id: str
    run_id: str
    status: str
    progress: int
    error: Optional[str] = None
    updated_at: str

class RunInfoResponse(BaseModel):
    run_id: str
    status: str
    created_at: str
    updated_at: str
    artifacts: Dict[str, str]
    metrics: Dict[str, Any]
    params: Dict[str, Any]

class RunSummaryResponse(BaseModel):
    run_id: str
    status: str
    created_at: str
    updated_at: str

class AnalyticsResponse(BaseModel):
    run_id: str
    fps: float
    trajectory: Dict[str, Any]
    timeline: Dict[str, Any]
    meta: Dict[str, Any]

class DeleteRunResponse(BaseModel):
    ok: bool
    run_id: str

class DeleteAllRunsResponse(BaseModel):
    ok: bool
    deleted: List[str]
    skipped: List[str]
    failed: Dict[str, str]