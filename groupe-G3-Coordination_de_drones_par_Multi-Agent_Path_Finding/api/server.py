from flask import Flask, request, jsonify
from flask_cors import CORS
from solver.grid import Grid
from solver.mapf import Drone, MAPFSolver
from solver.scenarios import list_scenarios


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    @app.route("/scenarios", methods=["GET"])
    def scenarios():
        return jsonify(list_scenarios())

    @app.route("/solve", methods=["POST"])
    def solve():
        body = request.get_json(force=True)

        gc = body.get("grid", {})
        grid = Grid(
            rows=gc.get("rows", 16),
            cols=gc.get("cols", 16),
            alts=gc.get("alts", 1),
        )

        for b in body.get("buildings", []):
            grid.add_building(b["row"], b["col"], b["height"])

        for nf in body.get("nofly", []):
            grid.add_nofly_box(tuple(nf["min"]), tuple(nf["max"]))

        drones = [
            Drone(
                id=d["id"],
                start=tuple(d["start"]),
                goal=tuple(d["goal"]),
            )
            for d in body.get("drones", [])
        ]

        time_limit = body.get("time_limit_s", 10)
        sol = MAPFSolver(grid, drones, time_limit_s=time_limit).solve()

        return jsonify({
            "status": sol.status,
            "makespan": sol.makespan,
            "solve_time_ms": round(sol.solve_time_ms, 1),
            "conflicts_avoided": sol.conflicts_avoided,
            "paths": {
                str(did): [list(pos) for pos in path]
                for did, path in sol.paths.items()
            },
        })

    return app


if __name__ == "__main__":
    create_app().run(port=5050, debug=True)
