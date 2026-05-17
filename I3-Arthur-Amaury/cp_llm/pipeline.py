"""Etages 1 a 3 du pipeline NL -> CP-SAT (analyse, variables, contraintes)."""

from cp_llm.llm_client import LLMClient
from cp_llm.prompts import ANALYZER_SYSTEM, CONSTRAINTS_SYSTEM, VARIABLES_SYSTEM
from cp_llm.schemas import ConstraintSet, ProblemAnalysis, VariableSet


def analyze(client: LLMClient, problem_text: str) -> ProblemAnalysis:
    user_prompt = f"Voici l'enonce du probleme :\n\n{problem_text.strip()}"
    return client.call_structured(ANALYZER_SYSTEM, user_prompt, ProblemAnalysis)


def extract_variables(
    client: LLMClient,
    problem_text: str,
    analysis: ProblemAnalysis,
) -> VariableSet:
    user_prompt = (
        f"Enonce :\n\n{problem_text.strip()}\n\n"
        f"Analyse de l'etage precedent (JSON) :\n\n{analysis.model_dump_json(indent=2)}\n\n"
        "Identifie les variables de decision a creer."
    )
    return client.call_structured(VARIABLES_SYSTEM, user_prompt, VariableSet)


def extract_constraints(
    client: LLMClient,
    problem_text: str,
    analysis: ProblemAnalysis,
    variables: VariableSet,
) -> ConstraintSet:
    user_prompt = (
        f"Enonce :\n\n{problem_text.strip()}\n\n"
        f"Analyse :\n\n{analysis.model_dump_json(indent=2)}\n\n"
        f"Variables :\n\n{variables.model_dump_json(indent=2)}\n\n"
        "Liste TOUTES les contraintes, y compris les implicites."
    )
    return client.call_structured(CONSTRAINTS_SYSTEM, user_prompt, ConstraintSet)
