from pathlib import Path
from typing import Any, Dict, Optional

from diet.api import benchmark_weekly, solve_weekly
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

# Autoriser les requêtes depuis l'application React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir les fichiers statiques (data)
data_dir = Path(__file__).parent / "data"
if data_dir.exists():
    app.mount("/data", StaticFiles(directory=str(data_dir)), name="data")


class SolveRequest(BaseModel):
    dishes: list
    bounds: dict
    season: str
    budget: Optional[float] = None
    preferences: Optional[dict] = None
    days: int = 7
    solver: str = "cpsat"

@app.post("/api/solve_weekly")
def api_solve_weekly(req: SolveRequest):
    try:
        result = solve_weekly({
            "dishes": req.dishes,
            "bounds": req.bounds,
            "season": req.season,
            "budget": req.budget,
            "preferences": req.preferences,
            "days": req.days,
            "solver": req.solver
        })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/benchmark_weekly")
def api_benchmark_weekly(req: SolveRequest):
    try:
        result = benchmark_weekly({
            "dishes": req.dishes,
            "bounds": req.bounds,
            "season": req.season,
            "budget": req.budget,
            "preferences": req.preferences,
            "days": req.days,
        })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    # Lance le serveur sur le port 8000
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
