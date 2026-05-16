from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.assignment import AssignmentSolver
from app.embedding_client import EmbeddingClient
from app.models import (
    AssignmentRequest,
    AssignmentResponse,
    CandidateProfile,
    CandidateProfileCreate,
    CompatibilityRequest,
    CompatibilityResponse,
    JobProfile,
    JobProfileCreate,
)
from app.scoring import CompatibilityScorer
from app.storage import JsonRepository


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"

candidate_repository = JsonRepository(DATA_DIR / "candidates.json", CandidateProfile)
job_repository = JsonRepository(DATA_DIR / "jobs.json", JobProfile)
compatibility_scorer = CompatibilityScorer(EmbeddingClient())
assignment_solver = AssignmentSolver(compatibility_scorer)

app = FastAPI(
    title="Candidate Orientation Collector",
    version="0.1.0",
    description="Structured collection of candidate and job profiles for scoring and constraint-based matching.",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/candidates", response_model=list[CandidateProfile])
def list_candidates() -> list[CandidateProfile]:
    return candidate_repository.list()


@app.post("/api/candidates", response_model=CandidateProfile, status_code=201)
def create_candidate(candidate: CandidateProfileCreate) -> CandidateProfile:
    return candidate_repository.create(candidate)


@app.get("/api/jobs", response_model=list[JobProfile])
def list_jobs() -> list[JobProfile]:
    return job_repository.list()


@app.post("/api/jobs", response_model=JobProfile, status_code=201)
def create_job(job: JobProfileCreate) -> JobProfile:
    return job_repository.create(job)


@app.post("/api/compatibility", response_model=CompatibilityResponse)
def compute_compatibility(request: CompatibilityRequest) -> CompatibilityResponse:
    candidates, jobs = _resolve_filtered_entities(request.candidate_ids, request.job_ids)

    return compatibility_scorer.score_all(
        candidates,
        jobs,
        request.top_k_per_candidate,
        request.criterion_weights,
    )


@app.post("/api/assignment", response_model=AssignmentResponse)
def compute_assignment(request: AssignmentRequest) -> AssignmentResponse:
    candidates, jobs = _resolve_filtered_entities(request.candidate_ids, request.job_ids)
    return assignment_solver.solve(candidates, jobs, request)


def _resolve_filtered_entities(
    candidate_ids: list[str],
    job_ids: list[str],
) -> tuple[list[CandidateProfile], list[JobProfile]]:
    candidates = candidate_repository.list()
    jobs = job_repository.list()

    if candidate_ids:
        candidate_lookup = {candidate.id: candidate for candidate in candidates}
        missing_ids = [candidate_id for candidate_id in candidate_ids if candidate_id not in candidate_lookup]
        if missing_ids:
            raise HTTPException(status_code=404, detail=f"Candidats introuvables: {', '.join(missing_ids)}")
        candidates = [candidate_lookup[candidate_id] for candidate_id in candidate_ids]

    if job_ids:
        job_lookup = {job.id: job for job in jobs}
        missing_ids = [job_id for job_id in job_ids if job_id not in job_lookup]
        if missing_ids:
            raise HTTPException(status_code=404, detail=f"Postes introuvables: {', '.join(missing_ids)}")
        jobs = [job_lookup[job_id] for job_id in job_ids]

    if not candidates:
        raise HTTPException(status_code=400, detail="Aucun candidat disponible pour le calcul.")
    if not jobs:
        raise HTTPException(status_code=400, detail="Aucun poste disponible pour le calcul.")

    return candidates, jobs


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
