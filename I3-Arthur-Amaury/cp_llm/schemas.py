"""Schemas Pydantic pour les sorties structurees de chaque etage du pipeline."""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ProblemAnalysis(BaseModel):
    """Etage 1 : analyse de haut niveau du probleme NL."""

    reasoning: str = Field(
        description="Reflexion pas a pas sur la comprehension de l'enonce, les entites et les objectifs."
    )
    problem_type: str = Field(
        description=(
            "Categorie generale : 'satisfaction', 'optimization', 'scheduling', "
            "'assignment', 'packing', 'coloring', 'routing', 'allocation'."
        )
    )
    objective_direction: Optional[Literal["minimize", "maximize", "none"]] = Field(
        description="Direction de l'objectif. 'none' si probleme de satisfaction pure."
    )
    objective_description: Optional[str] = Field(
        description="Description en langage naturel de ce qui est optimise (ou null)."
    )
    entities: list[str] = Field(
        description="Noms des ensembles/entites du probleme (ex: 'reines', 'objets', 'sommets')."
    )
    parameters: dict[str, Any] = Field(
        description=(
            "Valeurs numeriques mentionnees dans l'enonce, indexees par un nom court. "
            "Accepte scalaires, listes, et dicts imbriques (matrices, mappings). "
            "Ex: {'n_queens': 8, 'capacity': 50, 'weights': [10, 20, 30], "
            "'distances': {'A-B': 10, 'A-C': 15}}."
        )
    )
    summary: str = Field(description="Resume en une phrase du probleme.")


class VariableSpec(BaseModel):
    """Specification d'une variable de decision."""

    name: str = Field(description="Identifiant Python (snake_case).")
    var_type: Literal["int", "bool", "interval"] = Field(
        description="Type CP-SAT. 'int' = NewIntVar, 'bool' = NewBoolVar, 'interval' = NewIntervalVar."
    )
    domain_lower: Optional[int] = Field(
        description="Borne inf pour 'int' (ignoree pour 'bool')."
    )
    domain_upper: Optional[int] = Field(
        description="Borne sup pour 'int' (ignoree pour 'bool')."
    )
    indexed_by: list[str] = Field(
        default_factory=list,
        description=(
            "Si la variable est en realite un tableau indexe (ex: queens[i]), "
            "lister ici les ensembles d'indexation. [] si scalaire."
        ),
    )
    description: str = Field(description="A quoi sert cette variable.")


class VariableSet(BaseModel):
    """Etage 2 : ensemble des variables de decision."""

    reasoning: str = Field(
        description="Explication du choix des variables de decision et de leur domaine."
    )
    variables: list[VariableSpec]


class ConstraintSpec(BaseModel):
    """Specification d'une contrainte."""

    name: str = Field(description="Identifiant court (ex: 'all_different_rows').")
    constraint_type: str = Field(
        description=(
            "Type CP-SAT : 'all_different', 'linear_le', 'linear_eq', 'linear_ge', "
            "'not_equal', 'implication', 'bool_or', 'bool_and', 'max_equality', "
            "'min_equality', 'element', 'no_overlap', 'cumulative', 'circuit'."
        )
    )
    description: str = Field(
        description="Formulation en langage naturel de la contrainte."
    )
    formula: str = Field(
        description=(
            "Pseudocode mathematique. Ex: 'AllDifferent(queens)', "
            "'sum(weights[i] * take[i] for i in items) <= capacity'."
        )
    )
    is_implicit: bool = Field(
        description=(
            "True si la contrainte n'est pas explicitement enoncee mais necessaire "
            "(ex: 'au plus une copie de chaque objet' implicite dans 0/1)."
        )
    )


class ConstraintSet(BaseModel):
    """Etage 3 : ensemble des contraintes."""

    reasoning: str = Field(
        description="Analyse des lois physiques, temporelles, ou logiques du probleme pour deduire les contraintes implicites."
    )
    constraints: list[ConstraintSpec]


class CodegenAttempt(BaseModel):
    """Une tentative de generation de code, avec le code produit et l'erreur eventuelle."""

    attempt_number: int = Field(description="Indice de la tentative (1 pour la premiere).")
    code: str = Field(description="Code Python produit lors de cette tentative.")
    ok: bool = Field(description="True si la verification a passe pour cette tentative.")
    error: Optional[str] = Field(
        default=None,
        description="Message d'erreur si la tentative a echoue (None sinon).",
    )


class PipelineResult(BaseModel):
    """Resultat complet d'un passage du pipeline."""

    problem_path: str
    analysis: ProblemAnalysis
    variables: VariableSet
    constraints: ConstraintSet
    generated_code: str
    verification: dict
    codegen_attempts: list[CodegenAttempt] = Field(default_factory=list)
    execution_time_s: Optional[float] = None
    reference_execution_time_s: Optional[float] = None
    error_stage: Optional[
        Literal[
            "analysis",
            "variables",
            "constraints",
            "codegen",
            "verification",
            "syntactic",
            "feasibility",
            "semantic",
        ]
    ] = None
    error_message: Optional[str] = None
