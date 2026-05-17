"""Etage 4 : generation du code Python ortools a partir des specs etages 1-3."""

import re

from cp_llm.llm_client import LLMClient
from cp_llm.prompts import CODEGEN_SYSTEM
from cp_llm.schemas import ConstraintSet, ProblemAnalysis, VariableSet


def generate_code(
    client: LLMClient,
    problem_text: str,
    analysis: ProblemAnalysis,
    variables: VariableSet,
    constraints: ConstraintSet,
) -> str:
    user_prompt = (
        f"Enonce :\n\n{problem_text.strip()}\n\n"
        f"Analyse :\n\n{analysis.model_dump_json(indent=2)}\n\n"
        f"Variables :\n\n{variables.model_dump_json(indent=2)}\n\n"
        f"Contraintes :\n\n{constraints.model_dump_json(indent=2)}\n\n"
        "Genere le script Python complet."
    )
    code = client.call_text(CODEGEN_SYSTEM, user_prompt)
    return _strip_markdown_fences(code)


def _strip_markdown_fences(code: str) -> str:
    """Retire les fences markdown si le LLM en a mis malgre l'instruction."""
    match = re.search(r"```(?:python)?\s*(.*?)```", code, re.DOTALL)
    if match:
        return match.group(1).strip()
    return code.strip()
