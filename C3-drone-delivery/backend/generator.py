import random
import math
from models import Client, Depot, Drone, ForbiddenZone, Point, SolveRequest, WeatherCondition


def generate_instance(
    n_clients: int = 10,
    n_drones: int = 3,
    n_zones: int = 2,
    center_lat: float = 48.8566,
    center_lng: float = 2.3522,
    radius_km: float = 15.0,
    seed: int = 42,
) -> SolveRequest:
    rng = random.Random(seed)

    lat_deg = radius_km / 111.0
    lng_deg = radius_km / (111.0 * math.cos(math.radians(center_lat)))

    def rand_point():
        return Point(
            lat=center_lat + rng.uniform(-lat_deg, lat_deg),
            lng=center_lng + rng.uniform(-lng_deg, lng_deg),
        )

    depot = Depot(position=Point(lat=center_lat, lng=center_lng))

    clients = [
        Client(
            id=i + 1,
            position=rand_point(),
            weight=round(rng.uniform(0.5, 5.0), 2),
            volume=round(rng.uniform(1.0, 10.0), 2),
            priority=rng.randint(1, 3),
        )
        for i in range(n_clients)
    ]

    drones = [
        Drone(
            id=i + 1,
            max_range=rng.uniform(20.0, 40.0),
            max_weight=rng.uniform(8.0, 15.0),
            max_volume=rng.uniform(20.0, 40.0),
            speed=60.0,
        )
        for i in range(n_drones)
    ]

    zones = []
    for i in range(n_zones):
        cx = center_lat + rng.uniform(-lat_deg * 0.7, lat_deg * 0.7)
        cy = center_lng + rng.uniform(-lng_deg * 0.7, lng_deg * 0.7)
        r_lat = rng.uniform(0.005, 0.015)
        r_lng = rng.uniform(0.005, 0.015)
        polygon = [
            Point(lat=cx + r_lat, lng=cy - r_lng),
            Point(lat=cx + r_lat, lng=cy + r_lng),
            Point(lat=cx - r_lat, lng=cy + r_lng),
            Point(lat=cx - r_lat, lng=cy - r_lng),
        ]
        zones.append(ForbiddenZone(id=i + 1, polygon=polygon, label=f"Zone {i+1}"))

    return SolveRequest(
        depot=depot,
        clients=clients,
        drones=drones,
        forbidden_zones=zones,
        weather=WeatherCondition(wind_factor=1.0),
        time_limit_seconds=30,
    )
