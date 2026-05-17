"""Pipeline sur un probleme unique. Affiche les artefacts de chaque etage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Permet d'executer le script sans installer le package.
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "problem", type=Path, help="Chemin vers le fichier .txt de description NL."
    )
    parser.add_argument(
        "--provider",
        default="mistral",
        choices=["mistral", "anthropic", "mock"],
        help="LLM a utiliser (defaut: mistral).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override du modele (ex: mistral-medium-latest, codestral-latest).",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Alias pour --provider mock.",
    )
    parser.add_argument(
        "--effort",
        default="high",
        choices=["low", "medium", "high", "xhigh", "max"],
        help="Niveau d'effort Claude (Anthropic uniquement, defaut: high).",
    )
    parser.add_argument(
        "--save-code",
        type=Path,
        default=None,
        help="Si fourni, sauve le code Python genere a ce chemin.",
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
    client = build_client(args.provider, args.model, args.effort, cache_dir)

    print(f"=== Pipeline sur {args.problem} ===\n")
    result = run_pipeline(client, args.problem)

    print("--- Etage 1 : analyse ---")
    print(result.analysis.model_dump_json(indent=2))
    print()

    print("--- Etage 2 : variables ---")
    print(result.variables.model_dump_json(indent=2))
    print()

    print("--- Etage 3 : contraintes ---")
    print(result.constraints.model_dump_json(indent=2))
    print()

    print("--- Etage 4 : code genere ---")
    print(result.generated_code or "(non genere)")
    print()

    print("--- Verification ---")
    print(json.dumps(result.verification, indent=2, default=str))

    if result.error_stage:
        print(f"\nECHEC a l'etage : {result.error_stage}")
        print(f"Message : {result.error_message}")

    if args.save_code and result.generated_code:
        args.save_code.parent.mkdir(parents=True, exist_ok=True)
        args.save_code.write_text(result.generated_code)
        print(f"\nCode sauve dans : {args.save_code}")

    return 0 if result.verification.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
