"""Benchmark complet : pipeline sur tous les problemes, rapport JSON.

Pour chaque probleme du dossier benchmark/problems/, lance le pipeline et
collecte :
- Statut final (succes / echec)
- Etage d'echec si applicable
- Code genere (longueur, presence d'objectif)
- Resultat de la verification
- Si une reference manuelle existe, compare la valeur d'objectif
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cp_llm.llm_client import LLMClient, MistralClient  # noqa: E402
from cp_llm.runner import run_pipeline  # noqa: E402

# Patch CpSolver globally for this process (essential for macOS stability)
try:
    from ortools.sat.python import cp_model
    _original_solve = cp_model.CpSolver.Solve
    def _patched_solve(self, model, solution_callback=None):
        self.parameters.num_search_workers = 1
        return _original_solve(self, model, solution_callback)
    cp_model.CpSolver.Solve = _patched_solve
except ImportError:
    pass

def build_client(
    provider: str,
    model: str | None,
    effort: str,
    cache_dir: Path | None = None,
) -> LLMClient:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    if provider == "mistral":
        inner: LLMClient = MistralClient(model=model)
    else:
        raise ValueError(f"Provider inconnu : {provider}")

    if cache_dir is not None:
        from cp_llm.cache import CachedLLMClient

        return CachedLLMClient(inner, cache_dir)
    return inner


def load_reference(problem_name: str) -> tuple[dict | None, float | None]:
    """Lance le modele manuel de reference pour comparaison et mesure le temps."""
    ref_path = ROOT / "benchmark" / "references" / f"{problem_name}.py"
    if not ref_path.exists():
        return None, None

    import runpy
    import time

    try:
        start_time = time.perf_counter()
        ns = runpy.run_path(str(ref_path))
        if "solve" in ns and callable(ns["solve"]):
            res = ns["solve"]()
            exec_time = time.perf_counter() - start_time
            return res, exec_time
    except Exception as exc:
        return {"error": str(exc)}, None
    return None, None


def benchmark(
    provider: str = "mistral",
    model: str | None = None,
    effort: str = "high",
    cache_dir: Path | None = None,
) -> list[dict]:
    client = build_client(provider, model, effort, cache_dir)

    problems_dir = ROOT / "benchmark" / "problems"
    rows = []

    for problem_path in sorted(problems_dir.glob("*.txt")):
        name = problem_path.stem
        print(f"--- {name} ---", flush=True)

        import time

        t0 = time.perf_counter()
        try:
            result = run_pipeline(client, problem_path)
        except Exception as exc:
            rows.append(
                {
                    "problem": name,
                    "ok": False,
                    "error_stage": "runner",
                    "error_message": str(exc),
                }
            )
            print(f"  ERREUR runner : {exc}", flush=True)
            continue

        gen_time = time.perf_counter() - t0

        reference, ref_exec_time = load_reference(name)
        result.reference_execution_time_s = ref_exec_time

        row = {
            "problem": name,
            "ok": result.verification.get("ok", False),
            "error_stage": result.error_stage,
            "error_message": result.error_message,
            "n_variables_generated": len(result.variables.variables),
            "n_constraints_generated": len(result.constraints.constraints),
            "n_implicit_constraints": sum(
                1 for c in result.constraints.constraints if c.is_implicit
            ),
            "code_lines": (
                len(result.generated_code.splitlines()) if result.generated_code else 0
            ),
            "verification": result.verification,
            "n_codegen_attempts": len(result.codegen_attempts),
            "n_codegen_failures": sum(1 for a in result.codegen_attempts if not a.ok),
            "codegen_attempts": [a.model_dump() for a in result.codegen_attempts],
            "reference": reference,
            "objective_match": _compare_objectives(result.verification, reference),
            "generation_time_s": gen_time,
            "execution_time_s": result.execution_time_s,
            "reference_execution_time_s": result.reference_execution_time_s,
            "execution_time_diff_s": (result.execution_time_s - result.reference_execution_time_s) if result.execution_time_s is not None and result.reference_execution_time_s is not None else None,
        }
        rows.append(row)

        status = "OK" if row["ok"] else f"ECHEC ({row['error_stage']})"
        print(
            f"  {status} | vars={row['n_variables_generated']} contraintes={row['n_constraints_generated']} | exec={row['execution_time_s']:.3f}s ref={row['reference_execution_time_s']:.3f}s" if row['execution_time_s'] is not None and row['reference_execution_time_s'] is not None else f"  {status} | vars={row['n_variables_generated']} contraintes={row['n_constraints_generated']}",
            flush=True,
        )

    return rows


def _compare_objectives(verification: dict, reference: dict | None) -> str:
    """Compare la valeur d'objectif si elle est presente dans les deux."""
    if not reference or not verification.get("ok"):
        return "n/a"
    gen_result = verification.get("result", {})
    gen_obj = (
        gen_result.get("objective")
        or gen_result.get("value")
        or gen_result.get("n_colors")
    )
    ref_obj = (
        reference.get("objective")
        or reference.get("value")
        or reference.get("n_colors")
    )
    if gen_obj is None and ref_obj is None:
        return "satisfaction (no objective)"
    if gen_obj is None or ref_obj is None:
        return "missing"
    if gen_obj == ref_obj:
        return f"match ({gen_obj})"
    return f"mismatch (gen={gen_obj}, ref={ref_obj})"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider",
        default="mistral",
        choices=["mistral", "anthropic", "mock"],
        help="LLM a utiliser (defaut: mistral).",
    )
    parser.add_argument("--model", default=None, help="Override du modele.")
    parser.add_argument(
        "--mock", action="store_true", help="Alias pour --provider mock."
    )
    parser.add_argument(
        "--effort",
        default="high",
        choices=["low", "medium", "high", "xhigh", "max"],
        help="Niveau d'effort (Anthropic uniquement).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "benchmark_report.json",
        help="Chemin du rapport JSON de sortie.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=ROOT / ".cache" / "llm",
        help="Repertoire de cache disque pour les reponses LLM.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Desactive le cache disque (par defaut active).",
    )
    args = parser.parse_args()

    if args.mock:
        args.provider = "mock"

    cache_dir = None if args.no_cache else args.cache_dir
    rows = benchmark(
        provider=args.provider,
        model=args.model,
        effort=args.effort,
        cache_dir=cache_dir,
    )
    args.output.write_text(json.dumps(rows, indent=2, default=str))

    n_ok = sum(1 for r in rows if r.get("ok"))
    print(f"\n=== {n_ok}/{len(rows)} problemes resolus avec succes ===")
    print(f"Rapport sauve dans {args.output}")
    return 0 if n_ok == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
