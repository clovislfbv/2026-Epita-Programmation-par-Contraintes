"""Orchestrateur du pipeline complet : NL -> code -> verification."""

from pathlib import Path

from cp_llm.codegen import generate_code
from cp_llm.llm_client import LLMClient
from cp_llm.pipeline import analyze, extract_constraints, extract_variables
from cp_llm.schemas import CodegenAttempt, PipelineResult
from cp_llm.verification import verify_all


def run_pipeline(
    client: LLMClient, problem_path: str | Path, max_retries: int = 3
) -> PipelineResult:
    """Lance les 4 etages + la verification. Retourne un PipelineResult complet
    meme en cas d'echec partiel (le champ error_stage indique ou ca a casse).
    """
    problem_path = Path(problem_path)
    problem_text = problem_path.read_text(encoding="utf-8")

    try:
        analysis = analyze(client, problem_text)
    except Exception as e:
        return _failure(problem_path, "analysis", str(e))

    try:
        variables = extract_variables(client, problem_text, analysis)
    except Exception as e:
        return _failure(problem_path, "variables", str(e), analysis=analysis)

    try:
        constraints = extract_constraints(client, problem_text, analysis, variables)
    except Exception as e:
        return _failure(
            problem_path,
            "constraints",
            str(e),
            analysis=analysis,
            variables=variables,
        )

    code = ""
    error_msg = None
    verification: dict = {"ok": False}
    attempts: list[CodegenAttempt] = []

    # Retry loop for codegen
    for attempt in range(max_retries):
        try:
            if attempt == 0:
                code = generate_code(
                    client, problem_text, analysis, variables, constraints
                )
            else:
                # Retry prompt. Bumper la temperature sur chaque retry pour
                # diversifier les reponses : avec temperature=0, le LLM tend
                # a renvoyer exactement le meme code et la boucle est inutile.
                # Le prompt reste generique (pas d'indice sur la fix attendue).
                retry_temperature = 0.5 if attempt == 1 else 1.0
                retry_prompt = f"Le code precedent a echoue avec l'erreur suivante :\n{error_msg}\n\nVoici le code precedent :\n```python\n{code}\n```\n\nCorrige le code et renvoie TOUT le code dans un unique bloc markdown (```python ... ```). N'ajoute aucun texte explicatif."
                code = client.call_text(
                    "Tu es un expert ortools qui corrige du code Python.",
                    retry_prompt,
                    temperature=retry_temperature,
                )
                from cp_llm.codegen import _strip_markdown_fences

                code = _strip_markdown_fences(code)

        except Exception as e:
            attempts.append(
                CodegenAttempt(
                    attempt_number=attempt + 1,
                    code=code,
                    ok=False,
                    error=f"LLM call failed: {e}",
                )
            )
            failure = _failure(
                problem_path,
                "codegen",
                str(e),
                analysis=analysis,
                variables=variables,
                constraints=constraints,
            )
            failure.codegen_attempts = attempts
            return failure

        verification = verify_all(
            code,
            analysis=analysis.model_dump(),
            constraints=[c.model_dump() for c in constraints.constraints],
        )

        ok = verification.get("ok", False)
        attempt_error = (
            None
            if ok
            else f"Stage: {verification.get('stage')} - Error: {verification.get('error')}"
        )
        attempts.append(
            CodegenAttempt(
                attempt_number=attempt + 1,
                code=code,
                ok=ok,
                error=attempt_error,
            )
        )

        if ok:
            error_msg = None
            break
        else:
            error_msg = attempt_error

    return PipelineResult(
        problem_path=str(problem_path),
        analysis=analysis,
        variables=variables,
        constraints=constraints,
        generated_code=code,
        verification=verification,
        codegen_attempts=attempts,
        execution_time_s=verification.get("execution_time_s"),
        error_stage=None
        if verification.get("ok")
        else verification.get("stage", "verification"),
        error_message=error_msg,
    )


def _failure(
    problem_path: Path,
    stage: str,
    message: str,
    analysis=None,
    variables=None,
    constraints=None,
) -> PipelineResult:
    """Construit un PipelineResult d'echec partiel sans planter sur les champs manquants."""
    from cp_llm.schemas import ConstraintSet, ProblemAnalysis, VariableSet

    return PipelineResult(
        problem_path=str(problem_path),
        analysis=analysis
        or ProblemAnalysis(
            reasoning="(non aboutie)",
            problem_type="unknown",
            objective_direction=None,
            objective_description=None,
            entities=[],
            parameters={},
            summary="(analyse non aboutie)",
        ),
        variables=variables or VariableSet(reasoning="(non aboutie)", variables=[]),
        constraints=constraints
        or ConstraintSet(reasoning="(non aboutie)", constraints=[]),
        generated_code="",
        verification={"ok": False, "stage": stage, "error": message},
        error_stage=stage,  # type: ignore[arg-type]
        error_message=message,
    )
