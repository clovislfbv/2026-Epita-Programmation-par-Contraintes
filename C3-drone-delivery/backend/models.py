from pydantic import BaseModel
from typing import List, Optional


class Point(BaseModel):
    lat: float
    lng: float


class Depot(BaseModel):
    position: Point


class Client(BaseModel):
    id: int
    position: Point
    weight: float   # kg
    volume: float   # litres
    priority: int = 1


class Drone(BaseModel):
    id: int
    max_range: float    # km
    max_weight: float   # kg
    max_volume: float   # litres
    speed: float = 60.0  # km/h


class ForbiddenZone(BaseModel):
    id: int
    polygon: List[Point]
    label: str = ""


class WeatherCondition(BaseModel):
    wind_factor: float = 1.0  # 0.8 = -20% autonomie
    rain: bool = False


class SolveRequest(BaseModel):
    depot: Depot
    clients: List[Client]
    drones: List[Drone]
    forbidden_zones: List[ForbiddenZone] = []
    weather: WeatherCondition = WeatherCondition()
    time_limit_seconds: int = 30


class DroneStop(BaseModel):
    client_id: int
    position: Point
    arrival_distance: float
    cumulative_distance: float


class DroneRoute(BaseModel):
    drone_id: int
    stops: List[DroneStop]
    total_distance: float
    total_weight: float
    battery_remaining: float  # %


class SolveResponse(BaseModel):
    status: str  # OPTIMAL, FEASIBLE, INFEASIBLE
    routes: List[DroneRoute]
    unserved_clients: List[int]
    total_distance: float
    solve_time_seconds: float
