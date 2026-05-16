from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Dict, List, Sequence

from ortools.sat.python import cp_model

from app.models import (
    AssignmentRequest,
    AssignmentResponse,
    CandidateProfile,
    JobAssignmentLoad,
    JobDiversityConstraint,
    JobProfile,
    PairCompatibility,
    UnassignedCandidate,
)
from app.scoring import CompatibilityScorer


class AssignmentSolver:
    def __init__(self, compatibility_scorer: CompatibilityScorer) -> None:
        self.compatibility_scorer = compatibility_scorer

    def solve(
        self,
        candidates: Sequence[CandidateProfile],
        jobs: Sequence[JobProfile],
        request: AssignmentRequest,
    ) -> AssignmentResponse:
        model = cp_model.CpModel()
        all_pairs = self._build_pair_results(candidates, jobs, request)
        eligible_pairs = {
            pair_key: pair_result
            for pair_key, pair_result in all_pairs.items()
            if self._is_pair_eligible(pair_result, request)
        }

        decision_vars: Dict[tuple[str, str], cp_model.IntVar] = {}
        for candidate in candidates:
            for job in jobs:
                pair_key = (candidate.id, job.id)
                if pair_key not in eligible_pairs:
                    continue
                decision_vars[pair_key] = model.NewBoolVar(f"assign_{candidate.id}_{job.id}")

        for candidate in candidates:
            candidate_vars = [
                decision_vars[(candidate.id, job.id)]
                for job in jobs
                if (candidate.id, job.id) in decision_vars
            ]
            if candidate_vars:
                model.Add(sum(candidate_vars) <= 1)

        for job in jobs:
            job_vars = [
                decision_vars[(candidate.id, job.id)]
                for candidate in candidates
                if (candidate.id, job.id) in decision_vars
            ]
            if job_vars:
                model.Add(sum(job_vars) <= job.conditions.capacity)

        if request.enforce_diversity_requirements:
            self._apply_job_diversity_constraints(model, candidates, jobs, decision_vars)

        if decision_vars:
            assignment_count_term = sum(decision_vars.values()) * 10000
            score_term = sum(
                eligible_pairs[pair_key].overall_score * variable * 100
                for pair_key, variable in decision_vars.items()
            )
            preferred_diversity_bonus = self._preferred_diversity_bonus(
                model,
                candidates,
                jobs,
                decision_vars,
            )
            model.Maximize(assignment_count_term + score_term + preferred_diversity_bonus)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = request.max_solver_time_seconds
        status = solver.Solve(model)

        selected_assignments = self._selected_assignments(
            solver,
            status,
            decision_vars,
            eligible_pairs,
        )
        assigned_candidate_ids = {assignment.candidate_id for assignment in selected_assignments}
        selected_by_job: Dict[str, int] = {}
        for assignment in selected_assignments:
            selected_by_job[assignment.job_id] = selected_by_job.get(assignment.job_id, 0) + 1

        unassigned_candidates = [
            UnassignedCandidate(
                candidate_id=candidate.id,
                candidate_name=candidate.full_name,
                reason=self._unassigned_reason(candidate, jobs, eligible_pairs),
            )
            for candidate in candidates
            if candidate.id not in assigned_candidate_ids
        ]

        job_loads = [
            JobAssignmentLoad(
                job_id=job.id,
                job_title=job.title,
                capacity=job.conditions.capacity,
                assigned_count=selected_by_job.get(job.id, 0),
                remaining_capacity=max(0, job.conditions.capacity - selected_by_job.get(job.id, 0)),
            )
            for job in jobs
        ]

        return AssignmentResponse(
            generated_at=datetime.now(timezone.utc).isoformat(),
            solver_status=self._status_label(status),
            total_score=sum(assignment.overall_score for assignment in selected_assignments),
            assigned_count=len(selected_assignments),
            unassigned_count=len(unassigned_candidates),
            considered_pairs=len(all_pairs),
            eligible_pairs=len(eligible_pairs),
            assignments=selected_assignments,
            unassigned_candidates=unassigned_candidates,
            job_loads=job_loads,
        )

    def _build_pair_results(
        self,
        candidates: Sequence[CandidateProfile],
        jobs: Sequence[JobProfile],
        request: AssignmentRequest,
    ) -> Dict[tuple[str, str], PairCompatibility]:
        return {
            (candidate.id, job.id): self.compatibility_scorer.score_pair(
                candidate,
                job,
                request.criterion_weights,
            )
            for candidate in candidates
            for job in jobs
        }

    def _is_pair_eligible(self, pair: PairCompatibility, request: AssignmentRequest) -> bool:
        if pair.overall_score < request.minimum_score:
            return False

        criteria_by_key = {criterion.key: criterion for criterion in pair.criteria}
        if request.enforce_location and criteria_by_key["location"].score == 0:
            return False
        if request.enforce_required_skills and criteria_by_key["required_skills"].score < 45:
            return False
        if request.enforce_contract and criteria_by_key["contract"].score < 40:
            return False
        if request.enforce_languages and criteria_by_key["languages"].score < 50:
            return False
        if request.enforce_availability and criteria_by_key["availability"].score < 35:
            return False
        return True

    def _apply_job_diversity_constraints(
        self,
        model: cp_model.CpModel,
        candidates: Sequence[CandidateProfile],
        jobs: Sequence[JobProfile],
        decision_vars: Dict[tuple[str, str], cp_model.IntVar],
    ) -> None:
        for job in jobs:
            job_vars = [
                decision_vars[(candidate.id, job.id)]
                for candidate in candidates
                if (candidate.id, job.id) in decision_vars
            ]
            if not job_vars:
                continue

            job_selected = model.NewBoolVar(f"job_selected_{job.id}")
            model.Add(sum(job_vars) >= 1).OnlyEnforceIf(job_selected)
            model.Add(sum(job_vars) == 0).OnlyEnforceIf(job_selected.Not())

            for rule in job.target_profile.diversity_constraints:
                if rule.priority != "required":
                    continue

                matching_vars = [
                    decision_vars[(candidate.id, job.id)]
                    for candidate in candidates
                    if (candidate.id, job.id) in decision_vars
                    and self._candidate_matches_diversity_rule(candidate, rule)
                ]

                if rule.minimum_count > 0:
                    if matching_vars:
                        model.Add(sum(matching_vars) >= rule.minimum_count).OnlyEnforceIf(job_selected)
                    else:
                        model.Add(job_selected == 0)

                if rule.maximum_count is not None and matching_vars:
                    model.Add(sum(matching_vars) <= rule.maximum_count)

    def _candidate_matches_diversity_rule(
        self,
        candidate: CandidateProfile,
        rule: JobDiversityConstraint,
    ) -> bool:
        normalized_value = rule.value.strip().lower()
        if rule.dimension == "gender":
            return candidate.diversity.gender.strip().lower() == normalized_value
        return normalized_value in {tag.strip().lower() for tag in candidate.diversity.self_declared_tags if tag.strip()}

    def _preferred_diversity_bonus(
        self,
        model: cp_model.CpModel,
        candidates: Sequence[CandidateProfile],
        jobs: Sequence[JobProfile],
        decision_vars: Dict[tuple[str, str], cp_model.IntVar],
    ) -> cp_model.LinearExpr:
        bonus_terms: List[cp_model.LinearExpr] = []
        for job in jobs:
            for rule in job.target_profile.diversity_constraints:
                if rule.priority != "preferred":
                    continue

                matching_vars = [
                    decision_vars[(candidate.id, job.id)]
                    for candidate in candidates
                    if (candidate.id, job.id) in decision_vars
                    and self._candidate_matches_diversity_rule(candidate, rule)
                ]
                if not matching_vars:
                    continue

                target_cap = rule.target_count if rule.target_count is not None else len(matching_vars)
                capped_matches = model.NewIntVar(
                    0,
                    min(len(matching_vars), target_cap),
                    f"preferred_diversity_{job.id}_{rule.dimension}_{rule.value}",
                )
                model.Add(capped_matches <= sum(matching_vars))
                model.Add(capped_matches <= target_cap)
                bonus_terms.append(capped_matches * 750)
        return sum(bonus_terms) if bonus_terms else 0

    def _parse_iso_date(self, raw_value: str | None) -> date | None:
        if not raw_value:
            return None
        try:
            return date.fromisoformat(raw_value)
        except ValueError:
            return None

    def _selected_assignments(
        self,
        solver: cp_model.CpSolver,
        status: int,
        decision_vars: Dict[tuple[str, str], cp_model.IntVar],
        eligible_pairs: Dict[tuple[str, str], PairCompatibility],
    ) -> List[PairCompatibility]:
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return []

        selected = [
            eligible_pairs[pair_key]
            for pair_key, variable in decision_vars.items()
            if solver.Value(variable) == 1
        ]
        selected.sort(key=lambda item: (item.job_title.lower(), -item.overall_score, item.candidate_name.lower()))
        return selected

    def _unassigned_reason(
        self,
        candidate: CandidateProfile,
        jobs: Sequence[JobProfile],
        eligible_pairs: Dict[tuple[str, str], PairCompatibility],
    ) -> str:
        if any((candidate.id, job.id) in eligible_pairs for job in jobs):
            return "Affectable, mais non retenu par l'optimisation globale sous contraintes."
        return "Aucun poste n'a passé les filtres d'éligibilité retenus pour l'affectation."

    def _status_label(self, status: int) -> str:
        if status == cp_model.OPTIMAL:
            return "optimal"
        if status == cp_model.FEASIBLE:
            return "feasible"
        if status == cp_model.INFEASIBLE:
            return "infeasible"
        if status == cp_model.MODEL_INVALID:
            return "invalid"
        return "unknown"
