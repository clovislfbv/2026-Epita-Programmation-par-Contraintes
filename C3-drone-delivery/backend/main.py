from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Tuple
from drone_delivery_solver import DroneInstance, DroneRoutingSolver
import os

app = FastAPI(title="Drone Delivery CP-SAT")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


class MissionRequest(BaseModel):
    depot: Tuple[float, float, float]
    clients: List[Tuple[float, float, float]]
    demands: List[int]
    volumes: List[int]
    notam_zones: List[List[Tuple[float, float]]]
    num_drones: int
    battery_capacity: int
    max_load: int
    max_volume: int
    grid_res: int


@app.get("/")
async def root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.post("/solve")
async def solve_mission(req: MissionRequest):
    instance = DroneInstance(
        depot=req.depot,
        clients=req.clients,
        demands=req.demands,
        volumes=req.volumes,
        notam_zones=req.notam_zones,
        num_drones=req.num_drones,
        battery_capacity=req.battery_capacity,
        max_load=req.max_load,
        max_volume=req.max_volume,
        grid_res=req.grid_res,
    )
    solver = DroneRoutingSolver(instance)
    routes = solver.solve()
    return {
        "status": "success" if routes else "failed",
        "routes": routes if routes else [],
    }


app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="static")
