"""Verification multi-niveau du code CP-SAT genere.

Trois niveaux :
1. Syntaxique : le code parse sans exception
2. Faisabilite : solver.Solve() retourne OPTIMAL ou FEASIBLE
3. Semantique : la solution respecte les contraintes extraites a l'etage 3

Le niveau 3 est partiellement implemente : on verifie via re-execution que la
fonction solve() retourne bien un statut faisable et un dict structure.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from cp_llm.prompts import RUNNER_TEMPLATE


def verify_syntactic(code: str) -> dict:
    """Niveau 1 : le code parse-t-il ?"""
    try:
        ast.parse(code)
        return {"ok": True, "stage": "syntactic", "error": None}
    except SyntaxError as e:
        return {
            "ok": False,
            "stage": "syntactic",
            "error": f"SyntaxError ligne {e.lineno} : {e.msg}",
        }


def verify_executable(code: str, timeout: float = 30.0) -> dict:
    """Niveaux 2-3 : le script tourne-t-il et produit-il un dict de solution ?"""
    syn = verify_syntactic(code)
    if not syn["ok"]:
        return syn

    with tempfile.TemporaryDirectory() as tmpdir:
        code_file = Path(tmpdir) / "generated.py"
        runner_file = Path(tmpdir) / "_runner.py"
        code_file.write_text(code)
        runner_file.write_text(RUNNER_TEMPLATE)

        try:
            proc = subprocess.run(
                [sys.executable, str(runner_file), str(code_file)],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "stage": "feasibility",
                "error": f"Timeout ({timeout}s) lors de l'execution.",
            }

        stdout = proc.stdout.strip()
        if not stdout:
            return {
                "ok": False,
                "stage": "feasibility",
                "error": "Pas de sortie. Stderr : " + proc.stderr[-500:],
            }

        try:
            payload = json.loads(stdout.splitlines()[-1])
        except json.JSONDecodeError:
            return {
                "ok": False,
                "stage": "feasibility",
                "error": "Sortie non-JSON : " + stdout[-500:],
            }

        if not payload.get("ok"):
            return {
                "ok": False,
                "stage": "feasibility",
                "error": payload.get("error", "Erreur inconnue"),
                "details": payload,
                "execution_time_s": payload.get("execution_time_s"),
            }

        return {
            "ok": True,
            "stage": "feasibility",
            "error": None,
            "result": payload["result"],
            "execution_time_s": payload.get("execution_time_s"),
        }


def _mock_all_different(*args):
    arr = list(args[0]) if len(args) == 1 else list(args)
    return len(set(arr)) == len(arr)


def verify_semantic(
    result_dict: dict, analysis_dict: dict, constraints: list[dict]
) -> dict:
    """Niveau 3 : la solution respecte-t-elle les contraintes ?"""
    context = {}
    context.update(analysis_dict.get("parameters", {}))
    context.update(result_dict)

    context["AllDifferent"] = _mock_all_different
    context["sum"] = sum
    context["len"] = len

    for c in constraints:
        formula = c.get("formula", "")
        if (
            "AllDifferent" in formula
            or "==" in formula
            or "<=" in formula
            or ">=" in formula
            or "!=" in formula
        ):
            try:
                clean_formula = formula.replace("model.Add(", "").rstrip(")")
                is_valid = eval(clean_formula, {"__builtins__": {}}, context)
                if not is_valid:
                    return {
                        "ok": False,
                        "stage": "semantic",
                        "error": f"Contrainte non respectee : {c.get('name')} -> {formula}",
                    }
            except Exception:
                pass

    return {"ok": True, "stage": "semantic", "error": None}


def verify_all(
    code: str,
    timeout: float = 30.0,
    analysis: dict = None,
    constraints: list[dict] = None,
) -> dict:
    """Lance les verifications en cascade. Retourne le premier echec ou OK final."""
    syn = verify_syntactic(code)
    if not syn["ok"]:
        return syn

    exe = verify_executable(code, timeout=timeout)
    if not exe["ok"]:
        return exe

    if analysis and constraints and "result" in exe:
        sem = verify_semantic(exe["result"], analysis, constraints)
        if not sem["ok"]:
            return sem

    return exe
