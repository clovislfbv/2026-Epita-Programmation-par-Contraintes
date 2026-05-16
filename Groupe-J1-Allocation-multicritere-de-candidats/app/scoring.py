from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Iterable, List, Sequence, Tuple

from app.embedding_client import EmbeddingClient, fuzzy_token_overlap, lexical_similarity, normalize_text, tokenize
from app.models import (
    CandidateProfile,
    CompatibilityPenalty,
    CompatibilityResponse,
    CriterionDetail,
    CriterionScore,
    JobDiversityConstraint,
    JobProfile,
    PairCompatibility,
    SkillEntry,
)


DEFAULT_CRITERION_WEIGHTS = {
    "location": 0.1,
    "availability": 0.05,
    "contract": 0.08,
    "salary": 0.08,
    "education": 0.08,
    "experience": 0.12,
    "languages": 0.06,
    "required_skills": 0.2,
    "desired_skills": 0.1,
    "diversity_equity": 0.07,
    "role_alignment": 0.12,
    "motivation": 0.1,
    "culture": 0.05,
    "learning_potential": 0.05,
}

CRITERION_KEYS = tuple(DEFAULT_CRITERION_WEIGHTS.keys())

IGNORED_SHARED_TOKENS = {
    "a",
    "au",
    "aux",
    "avec",
    "ce",
    "ces",
    "dans",
    "de",
    "des",
    "du",
    "en",
    "et",
    "for",
    "la",
    "le",
    "les",
    "of",
    "on",
    "ou",
    "par",
    "pour",
    "sur",
    "the",
    "to",
    "un",
    "une",
}

SHORT_TOKEN_WHITELIST = {"ai", "bi", "crm", "erp", "pmo", "qa", "rh", "sql", "ux", "ui"}

GENDER_LABELS = {
    "female": "Femme",
    "male": "Homme",
    "non_binary": "Non-binaire",
    "other": "Autre",
    "undisclosed": "Non renseigné",
}

DIVERSITY_TAG_LABELS = {
    "first_generation": "Première génération",
    "reconversion": "Reconversion",
    "rqth": "RQTH / handicap déclaré",
    "international": "Parcours international",
    "caregiver": "Aidance / proche aidant",
    "rural_background": "Origine rurale",
}

DEGREE_HINTS = [
    (5, ("doctorat", "phd", "doctorate", "thèse", "these")),
    (4, ("bac+5", "master", "mastère", "mastère spécialisé", "msc", "ingénieur", "ingenieur", "grande ecole")),
    (3, ("bac+3", "licence", "license", "bachelor", "but", "diplôme universitaire", "diplome universitaire")),
    (2, ("bac+2", "bts", "dut", "deug")),
    (1, ("bac", "baccalauréat", "baccalaureat")),
]


@dataclass(frozen=True)
class TextSimilarityInsight:
    semantic_score: float
    lexical_score: float
    source: str
    shared_tokens: List[str]
    left_excerpt: str
    right_excerpt: str


def clamp_score(value: float) -> int:
    return max(0, min(100, int(round(value))))


def list_to_text(values: Iterable[str]) -> str:
    return ", ".join(value.strip() for value in values if value and value.strip())


def format_percent_value(percent: float, clamp: bool = True) -> str:
    bounded = max(0.0, min(100.0, percent)) if clamp else max(0.0, percent)
    rounded = round(bounded, 1)
    if rounded.is_integer():
        return f"{int(rounded)} %"
    return f"{rounded:.1f} %"


def format_ratio(value: float, clamp: bool = True) -> str:
    return format_percent_value(value * 100, clamp=clamp)


def format_currency(value: int | None) -> str:
    if value is None:
        return "Non renseigné"
    return f"{value:,}".replace(",", " ") + " EUR"


def work_mode_label(value: str) -> str:
    return {
        "on_site": "sur site",
        "hybrid": "hybride",
        "remote": "remote",
    }.get(value, value)


class CompatibilityScorer:
    def __init__(self, embedding_client: EmbeddingClient | None = None) -> None:
        self.embedding_client = embedding_client or EmbeddingClient()

    def score_all(
        self,
        candidates: Sequence[CandidateProfile],
        jobs: Sequence[JobProfile],
        top_k_per_candidate: int,
        criterion_weights: dict[str, float] | None = None,
    ) -> CompatibilityResponse:
        results: List[PairCompatibility] = []
        resolved_weights = self._resolve_criterion_weights(criterion_weights)

        for candidate in candidates:
            candidate_results = [self.score_pair(candidate, job, resolved_weights) for job in jobs]
            candidate_results.sort(key=lambda item: item.overall_score, reverse=True)
            results.extend(candidate_results[:top_k_per_candidate])

        results.sort(key=lambda item: (item.candidate_name.lower(), -item.overall_score, item.job_title.lower()))
        return CompatibilityResponse(
            generated_at=datetime.now(timezone.utc).isoformat(),
            embedding_mode="remote" if self.embedding_client.mode() == "remote" else "fallback",
            embedding_model=self.embedding_client.model,
            results=results,
        )

    def score_pair(
        self,
        candidate: CandidateProfile,
        job: JobProfile,
        criterion_weights: dict[str, float] | None = None,
    ) -> PairCompatibility:
        resolved_weights = self._resolve_criterion_weights(criterion_weights)
        criteria = [
            self._score_location(candidate, job, resolved_weights),
            self._score_availability(candidate, job, resolved_weights),
            self._score_contract(candidate, job, resolved_weights),
            self._score_salary(candidate, job, resolved_weights),
            self._score_education(candidate, job, resolved_weights),
            self._score_experience(candidate, job, resolved_weights),
            self._score_languages(candidate, job, resolved_weights),
            self._score_required_skills(candidate, job, resolved_weights),
            self._score_desired_skills(candidate, job, resolved_weights),
            self._score_diversity_equity(candidate, job, resolved_weights),
            self._score_role_alignment(candidate, job, resolved_weights),
            self._score_motivation(candidate, job, resolved_weights),
            self._score_culture(candidate, job, resolved_weights),
            self._score_learning_potential(candidate, job, resolved_weights),
        ]

        base_score = min(100.0, round(sum(item.score * item.weight for item in criteria), 2))
        penalties = self._compute_penalties(criteria)
        final_score = base_score
        for penalty in penalties:
            final_score *= penalty.factor

        summary = self._build_summary(criteria, penalties)
        return PairCompatibility(
            candidate_id=candidate.id,
            candidate_name=candidate.full_name,
            job_id=job.id,
            job_title=job.title,
            overall_score=clamp_score(final_score),
            base_score=base_score,
            criteria=criteria,
            penalties=penalties,
            summary=summary,
        )

    def _criterion(
        self,
        key: str,
        label: str,
        score: float,
        source: str,
        explanation: str,
        criterion_weights: dict[str, float],
        details: Sequence[tuple[str, str | None]] | None = None,
    ) -> CriterionScore:
        weight = criterion_weights[key]
        normalized_score = clamp_score(score)
        criterion_details = [
            CriterionDetail(label=detail_label, value=detail_value)
            for detail_label, detail_value in (details or [])
            if detail_value
        ]
        return CriterionScore(
            key=key,
            label=label,
            score=normalized_score,
            weight=weight,
            weighted_score=round(normalized_score * weight, 2),
            source=source,  # type: ignore[arg-type]
            explanation=explanation,
            details=criterion_details,
        )

    def _score_location(
        self,
        candidate: CandidateProfile,
        job: JobProfile,
        criterion_weights: dict[str, float],
    ) -> CriterionScore:
        same_city = normalize_text(candidate.location.city) == normalize_text(job.location.city)
        same_country = normalize_text(candidate.location.country) == normalize_text(job.location.country)
        candidate_pref = candidate.location.remote_preference
        job_mode = job.location.work_mode

        if job_mode == "remote":
            score = 100 if candidate_pref in {"remote", "hybrid"} else 80
            explanation = "Le poste est remote, donc la distance n'est pas bloquante et la préférence du candidat reste compatible."
        elif same_city:
            score = 100 if job_mode != "hybrid" or candidate_pref != "remote" else 90
            explanation = "Le candidat et le poste sont dans la même ville, ce qui élimine presque toute friction logistique."
        elif job_mode == "hybrid":
            if same_country and candidate.location.mobility_km >= 20:
                score = 60
                explanation = "Le poste est hybride dans une autre ville, mais la mobilité déclarée laisse une faisabilité partielle."
            else:
                score = 35
                explanation = "Le poste est hybride hors de la ville du candidat et la mobilité disponible paraît limitée pour suivre ce rythme."
        else:
            if same_country and candidate.location.mobility_km >= 50:
                score = 40
                explanation = "Le poste est sur site dans une autre ville; la mobilité compense seulement une partie de la contrainte."
            else:
                score = 0
                explanation = "Le poste est sur site hors zone de mobilité déclarée; la localisation devient bloquante."

        details = [
            (
                "Profil candidat",
                f"{candidate.location.city}, {candidate.location.country} • préférence {work_mode_label(candidate_pref)} • mobilité {candidate.location.mobility_km} km",
            ),
            (
                "Profil poste",
                f"{job.location.city}, {job.location.country} • mode {work_mode_label(job_mode)}",
            ),
            ("Lecture appliquée", explanation),
        ]
        return self._criterion("location", "Compatibilité géographique", score, "structured", explanation, criterion_weights, details)

    def _score_contract(
        self,
        candidate: CandidateProfile,
        job: JobProfile,
        criterion_weights: dict[str, float],
    ) -> CriterionScore:
        preferred_contracts = set(candidate.preferences.contract_types)
        if not preferred_contracts:
            explanation = "Aucune préférence de contrat n'est renseignée côté candidat; le score reste volontairement neutre."
            return self._criterion(
                "contract",
                "Compatibilité contrat",
                70,
                "structured",
                explanation,
                criterion_weights,
                [
                    ("Préférences candidat", "Non renseignées"),
                    ("Contrat poste", job.conditions.contract_type.upper()),
                ],
            )

        if job.conditions.contract_type in preferred_contracts:
            score = 100
            explanation = f"Le contrat {job.conditions.contract_type.upper()} figure explicitement parmi les préférences du candidat."
        else:
            score = 20
            explanation = f"Le contrat {job.conditions.contract_type.upper()} n'apparaît pas dans les formats recherchés par le candidat."

        details = [
            ("Préférences candidat", ", ".join(contract.upper() for contract in sorted(preferred_contracts))),
            ("Contrat poste", job.conditions.contract_type.upper()),
            ("Correspondance", "Oui" if score == 100 else "Non"),
        ]
        return self._criterion("contract", "Compatibilité contrat", score, "structured", explanation, criterion_weights, details)

    def _score_availability(
        self,
        candidate: CandidateProfile,
        job: JobProfile,
        criterion_weights: dict[str, float],
    ) -> CriterionScore:
        candidate_start = self._parse_iso_date(candidate.availability.start_date)
        job_start = self._parse_iso_date(job.conditions.start_date)

        if not candidate_start or not job_start:
            explanation = "La date de début du candidat ou du poste n'est pas suffisamment renseignée; le critère reste neutre."
            return self._criterion(
                "availability",
                "Disponibilité",
                70,
                "structured",
                explanation,
                criterion_weights,
                [
                    ("Début candidat", candidate.availability.start_date or "Non renseigné"),
                    ("Début poste", job.conditions.start_date or "Non renseigné"),
                    ("Rythme candidat", candidate.availability.schedule),
                ],
            )

        day_gap = (candidate_start - job_start).days
        if day_gap <= 0:
            score = 100
            explanation = "Le candidat peut démarrer à la date attendue ou plus tôt."
        elif day_gap <= 14:
            score = 80
            explanation = "Le candidat démarre légèrement après la date cible, mais le décalage reste modéré."
        elif day_gap <= 45:
            score = 55
            explanation = "Le décalage de disponibilité existe et peut nécessiter un arbitrage côté poste."
        else:
            score = 20
            explanation = "La disponibilité du candidat est nettement plus tardive que la date visée par le poste."

        return self._criterion(
            "availability",
            "Disponibilité",
            score,
            "structured",
            explanation,
            criterion_weights,
            [
                ("Début candidat", candidate.availability.start_date or "Non renseigné"),
                ("Début poste", job.conditions.start_date or "Non renseigné"),
                ("Décalage", f"{day_gap:+d} jour(s)"),
                ("Rythme candidat", candidate.availability.schedule),
            ],
        )

    def _score_salary(
        self,
        candidate: CandidateProfile,
        job: JobProfile,
        criterion_weights: dict[str, float],
    ) -> CriterionScore:
        expected_min = candidate.preferences.salary_min
        job_min = job.conditions.salary_min
        job_max = job.conditions.salary_max

        if expected_min is None or (job_min is None and job_max is None):
            explanation = "Les informations salariales sont incomplètes d'un côté ou de l'autre; le score est donc maintenu à un niveau neutre."
            return self._criterion(
                "salary",
                "Compatibilité salariale",
                70,
                "structured",
                explanation,
                criterion_weights,
                [
                    ("Attente candidat", format_currency(expected_min)),
                    ("Fourchette poste", f"{format_currency(job_min)} -> {format_currency(job_max)}"),
                ],
            )

        available_salary = job_max if job_max is not None else job_min
        if available_salary is None:
            score = 70
            explanation = "La rémunération du poste n'est pas exploitable; aucun écart précis ne peut être calculé."
        elif available_salary >= expected_min:
            score = 100
            explanation = "La fourchette salariale du poste atteint ou dépasse le minimum demandé par le candidat."
        else:
            score = max(0.0, min(100.0, (available_salary / expected_min) * 100))
            explanation = "La borne haute disponible pour le poste reste inférieure au minimum attendu par le candidat."

        coverage_ratio = 0.0 if available_salary is None or expected_min == 0 else available_salary / expected_min
        details = [
            ("Attente candidat", format_currency(expected_min)),
            ("Salaire min poste", format_currency(job_min)),
            ("Salaire max poste", format_currency(job_max)),
            ("Couverture de l'attente", format_ratio(coverage_ratio, clamp=False) if available_salary is not None and expected_min else "Non calculable"),
        ]
        return self._criterion("salary", "Compatibilité salariale", score, "structured", explanation, criterion_weights, details)

    def _score_education(
        self,
        candidate: CandidateProfile,
        job: JobProfile,
        criterion_weights: dict[str, float],
    ) -> CriterionScore:
        required_degree = job.requirements.minimum_degree
        candidate_degree = candidate.education.degree

        if not required_degree:
            explanation = "Le poste ne fixe pas de niveau de diplôme minimal; le critère n'est donc pas discriminant."
            return self._criterion(
                "education",
                "Formation et diplôme",
                100,
                "structured",
                explanation,
                criterion_weights,
                [
                    ("Diplôme candidat", candidate_degree or "Non renseigné"),
                    ("Minimum poste", "Aucun"),
                ],
            )

        required_rank = self._degree_rank(required_degree)
        candidate_rank = self._degree_rank(candidate_degree)

        if candidate_rank is None and not candidate_degree:
            score = 25
            explanation = "Le poste impose un niveau de diplôme, mais le candidat n'a pas renseigné de diplôme exploitable."
        elif candidate_rank is None:
            score = 40
            explanation = "Le candidat a renseigné un diplôme, mais le niveau n'a pas pu être interprété de manière fiable face au minimum demandé."
        elif required_rank is None:
            score = 70
            explanation = "Le poste demande un diplôme, mais son niveau n'a pas pu être classé précisément; le score reste intermédiaire."
        elif candidate_rank >= required_rank:
            score = 100
            explanation = "Le niveau de diplôme du candidat atteint ou dépasse explicitement le minimum attendu pour le poste."
        else:
            gap = required_rank - candidate_rank
            score = max(0.0, 100 - (gap * 35))
            explanation = "Le niveau de diplôme identifié est inférieur au seuil demandé, ce qui réduit fortement la compatibilité sur ce critère."

        details = [
            ("Diplôme candidat", candidate_degree or "Non renseigné"),
            ("Minimum poste", required_degree),
            ("Niveau candidat", self._degree_rank_label(candidate_rank)),
            ("Niveau requis", self._degree_rank_label(required_rank)),
        ]
        return self._criterion("education", "Formation et diplôme", score, "structured", explanation, criterion_weights, details)

    def _score_experience(
        self,
        candidate: CandidateProfile,
        job: JobProfile,
        criterion_weights: dict[str, float],
    ) -> CriterionScore:
        required_years = job.requirements.minimum_years_experience
        if required_years <= 0:
            explanation = "Le poste ne fixe aucun seuil d'expérience minimal; le critère est validé par défaut."
            return self._criterion(
                "experience",
                "Compatibilité expérience",
                100,
                "structured",
                explanation,
                criterion_weights,
                [
                    ("Expérience candidat", f"{candidate.years_experience} an(s)"),
                    ("Minimum poste", "Aucun"),
                ],
            )

        if candidate.years_experience >= required_years:
            score = 100
            explanation = "Le niveau d'expérience déclaré couvre le minimum demandé pour le poste."
        else:
            score = ((candidate.years_experience + 1) / (required_years + 1)) * 100
            explanation = "Le candidat est en dessous du seuil d'expérience demandé, mais l'écart reste quantifié de manière progressive."

        gap = candidate.years_experience - required_years
        details = [
            ("Expérience candidat", f"{candidate.years_experience} an(s)"),
            ("Minimum poste", f"{required_years} an(s)"),
            ("Écart", f"{gap:+d} an(s)"),
        ]
        return self._criterion("experience", "Compatibilité expérience", score, "structured", explanation, criterion_weights, details)

    def _score_languages(
        self,
        candidate: CandidateProfile,
        job: JobProfile,
        criterion_weights: dict[str, float],
    ) -> CriterionScore:
        required_languages = [language for language in job.requirements.languages if language.strip()]
        if not required_languages:
            explanation = "Le poste ne précise pas d'exigence linguistique explicite."
            return self._criterion(
                "languages",
                "Langues",
                100,
                "structured",
                explanation,
                criterion_weights,
                [("Langues requises", "Aucune")],
            )

        candidate_languages = [skill.name for skill in candidate.skills if skill.category == "language"]
        matched_languages, missing_languages = self._split_skill_matches(candidate_languages, required_languages)
        coverage_ratio = len(matched_languages) / len(required_languages) if required_languages else 1.0
        score = 100 * coverage_ratio
        explanation = (
            "Le score mesure la couverture explicite des langues demandées par le poste parmi les langues déclarées par le candidat."
        )
        return self._criterion(
            "languages",
            "Langues",
            score,
            "structured",
            explanation,
            criterion_weights,
            [
                ("Langues requises", list_to_text(required_languages)),
                ("Langues retrouvées", list_to_text(matched_languages) or "Aucune"),
                ("Langues manquantes", list_to_text(missing_languages) or "Aucune"),
                ("Couverture", format_ratio(coverage_ratio)),
            ],
        )

    def _score_required_skills(
        self,
        candidate: CandidateProfile,
        job: JobProfile,
        criterion_weights: dict[str, float],
    ) -> CriterionScore:
        required_skills = [skill for skill in job.requirements.mandatory_skills if skill.strip()]
        if not required_skills:
            explanation = "Le poste ne définit pas de compétences obligatoires; aucun verrou dur n'est donc appliqué ici."
            return self._criterion(
                "required_skills",
                "Compétences obligatoires",
                100,
                "structured",
                explanation,
                criterion_weights,
                [("Compétences obligatoires", "Aucune")],
            )

        candidate_skill_names = [skill.name for skill in candidate.skills]
        matched_skills, missing_skills = self._split_skill_matches(candidate_skill_names, required_skills)
        exact_ratio = len(matched_skills) / len(required_skills)
        insight = self._text_similarity_insight(list_to_text(required_skills), list_to_text(candidate_skill_names))
        score = 100 * ((0.65 * exact_ratio) + (0.35 * insight.semantic_score))

        explanation = (
            f"{len(matched_skills)} compétence(s) obligatoire(s) sur {len(required_skills)} sont retrouvées exactement. "
            "Le complément vient de la proximité sémantique calculée entre la liste attendue et le portefeuille global de compétences."
        )
        details = [
            ("Couverture exacte", f"{len(matched_skills)}/{len(required_skills)} ({format_ratio(exact_ratio)})"),
            ("Compétences retrouvées", list_to_text(matched_skills) or "Aucune"),
            ("Compétences manquantes", list_to_text(missing_skills) or "Aucune"),
            ("Formule", "65 % exact match + 35 % similarité sémantique"),
            *self._semantic_detail_rows(
                insight,
                left_label="Texte poste comparé",
                right_label="Texte candidat comparé",
            ),
        ]
        return self._criterion(
            "required_skills",
            "Compétences obligatoires",
            score,
            self._hybrid_source(insight.source),
            explanation,
            criterion_weights,
            details,
        )

    def _score_desired_skills(
        self,
        candidate: CandidateProfile,
        job: JobProfile,
        criterion_weights: dict[str, float],
    ) -> CriterionScore:
        desired_skills = [skill for skill in job.desired_skills if skill.name.strip()]
        if not desired_skills:
            explanation = "Le poste ne précise pas de compétences bonus; le score reste intermédiaire plutôt que maximal."
            return self._criterion(
                "desired_skills",
                "Compétences souhaitées",
                70,
                "structured",
                explanation,
                criterion_weights,
                [("Compétences bonus", "Aucune")],
            )

        level_ratio = self._desired_skill_level_ratio(candidate.skills, desired_skills)
        insight = self._text_similarity_insight(
            list_to_text(skill.name for skill in desired_skills),
            list_to_text(skill.name for skill in candidate.skills),
        )
        matched_levels, missing_skills = self._desired_skill_match_details(candidate.skills, desired_skills)
        score = 100 * ((0.6 * level_ratio) + (0.4 * insight.semantic_score))

        explanation = (
            "Le score combine la couverture pondérée par niveau des compétences bonus et la proximité sémantique "
            "entre les intitulés demandés et les compétences effectivement déclarées."
        )
        details = [
            ("Couverture pondérée", format_ratio(level_ratio)),
            ("Correspondances niveau", list_to_text(matched_levels) or "Aucune"),
            ("Compétences bonus absentes", list_to_text(missing_skills) or "Aucune"),
            ("Formule", "60 % niveaux couverts + 40 % similarité sémantique"),
            *self._semantic_detail_rows(
                insight,
                left_label="Compétences souhaitées",
                right_label="Compétences candidat",
            ),
        ]
        return self._criterion(
            "desired_skills",
            "Compétences souhaitées",
            score,
            self._hybrid_source(insight.source),
            explanation,
            criterion_weights,
            details,
        )

    def _score_diversity_equity(
        self,
        candidate: CandidateProfile,
        job: JobProfile,
        criterion_weights: dict[str, float],
    ) -> CriterionScore:
        rules = [rule for rule in job.target_profile.diversity_constraints if rule.value.strip()]
        if not rules:
            explanation = "Le poste ne déclare aucun objectif explicite de diversité ou d'équité; ce critère n'est donc pas discriminant."
            return self._criterion(
                "diversity_equity",
                "Diversité et équité",
                100,
                "structured",
                explanation,
                criterion_weights,
                [
                    ("Objectifs du poste", "Aucun objectif explicite"),
                    ("Profil déclaré candidat", self._candidate_diversity_snapshot(candidate)),
                ],
            )

        required_rules = [rule for rule in rules if rule.priority == "required"]
        preferred_rules = [rule for rule in rules if rule.priority != "required"]
        matched_required = [rule for rule in required_rules if self._candidate_matches_diversity_rule(candidate, rule)]
        matched_preferred = [rule for rule in preferred_rules if self._candidate_matches_diversity_rule(candidate, rule)]

        required_component = (
            len(matched_required) / len(required_rules)
            if required_rules
            else None
        )
        preferred_component = (
            len(matched_preferred) / len(preferred_rules)
            if preferred_rules
            else None
        )

        if required_component is not None and preferred_component is not None:
            score = 100 * ((0.8 * required_component) + (0.2 * preferred_component))
            formula = "80 % couverture requise + 20 % couverture préférée"
        elif required_component is not None:
            score = 100 * required_component
            formula = "100 % couverture requise"
        elif preferred_component is not None:
            score = 100 * preferred_component
            formula = "100 % couverture préférée"
        else:
            score = 0
            formula = "Aucune règle exploitable"

        explanation = (
            "Le score mesure la contribution potentielle du candidat aux objectifs de diversité et d'équité déclarés par le poste. "
            "Les objectifs requis pèsent beaucoup plus que les objectifs préférés, et aucun point n'est donné gratuitement quand aucune règle n'est satisfaite."
        )
        details = [
            ("Profil déclaré candidat", self._candidate_diversity_snapshot(candidate)),
            ("Règles requises compatibles", f"{len(matched_required)}/{len(required_rules)}" if required_rules else "Aucune"),
            ("Règles préférées compatibles", f"{len(matched_preferred)}/{len(preferred_rules)}" if preferred_rules else "Aucune"),
            ("Objectifs du poste", " | ".join(self._format_diversity_rule(rule) for rule in rules)),
            ("Compatibilités trouvées", " | ".join(self._format_diversity_rule(rule) for rule in [*matched_required, *matched_preferred]) or "Aucune"),
            ("Formule", formula),
        ]
        return self._criterion(
            "diversity_equity",
            "Diversité et équité",
            score,
            "structured",
            explanation,
            criterion_weights,
            details,
        )

    def _score_role_alignment(
        self,
        candidate: CandidateProfile,
        job: JobProfile,
        criterion_weights: dict[str, float],
    ) -> CriterionScore:
        role_terms = [term for term in [candidate.current_title or "", *candidate.preferences.target_roles] if term.strip()]
        candidate_text = " ".join([*role_terms, list_to_text(candidate.preferences.target_sectors)])
        job_text = " ".join([job.title, job.team or "", job.missions])
        insight = self._text_similarity_insight(candidate_text, job_text)
        best_role_term, title_alignment = self._best_matching_term(role_terms, job.title)
        mission_preferences = list_to_text(candidate.motivation.mission_preferences)
        mission_alignment = self._phrase_match_score(mission_preferences, job.missions)
        score = 100 * ((0.5 * title_alignment) + (0.2 * mission_alignment) + (0.3 * insight.semantic_score))

        explanation = (
            "Ce critère rapproche l'intitulé visé, le rôle actuel et les secteurs cibles du candidat "
            "avec l'intitulé du poste et ses missions concrètes."
        )
        details = [
            ("Rôle le plus proche du titre", f"{best_role_term} ({format_ratio(title_alignment)})" if best_role_term else "Aucun rôle renseigné"),
            ("Missions préférées candidat", mission_preferences or "Non renseignées"),
            ("Recouvrement missions", format_ratio(mission_alignment)),
            ("Secteurs visés", list_to_text(candidate.preferences.target_sectors) or "Non renseignés"),
            ("Formule", "50 % alignement titre + 20 % missions + 30 % similarité sémantique"),
            *self._semantic_detail_rows(
                insight,
                left_label="Projection candidat",
                right_label="Description poste",
            ),
        ]
        return self._criterion(
            "role_alignment",
            "Alignement du poste",
            score,
            self._hybrid_source(insight.source),
            explanation,
            criterion_weights,
            details,
        )

    def _score_motivation(
        self,
        candidate: CandidateProfile,
        job: JobProfile,
        criterion_weights: dict[str, float],
    ) -> CriterionScore:
        candidate_text = " ".join(
            [
                candidate.motivation.free_text,
                list_to_text(candidate.motivation.mission_preferences),
            ]
        )
        job_text = " ".join([job.missions, job.target_profile.growth_potential])
        insight = self._text_similarity_insight(candidate_text, job_text)
        missions_overlap = self._phrase_match_score(
            list_to_text(candidate.motivation.mission_preferences),
            job.missions,
        )
        drivers_overlap = self._phrase_match_score(
            list_to_text(candidate.motivation.drivers),
            " ".join([job.missions, list_to_text(job.environment.culture_keywords)]),
        )
        raw_score = (0.65 * insight.semantic_score) + (0.2 * missions_overlap) + (0.15 * drivers_overlap)
        score = self._soft_textual_score(raw_score, floor=28)

        explanation = (
            "La motivation est évaluée à partir du texte libre du candidat, de ses missions préférées "
            "et de la manière dont cela rejoint les missions et perspectives du poste."
        )
        details = [
            ("Missions préférées", list_to_text(candidate.motivation.mission_preferences) or "Non renseignées"),
            ("Moteurs candidat", list_to_text(candidate.motivation.drivers) or "Non renseignés"),
            ("Recouvrement missions", format_ratio(missions_overlap)),
            ("Recouvrement moteurs/culture", format_ratio(drivers_overlap)),
            ("Formule", "65 % similarité sémantique + 20 % missions + 15 % moteurs"),
            *self._semantic_detail_rows(
                insight,
                left_label="Motivation candidat",
                right_label="Missions et évolution du poste",
            ),
        ]
        return self._criterion(
            "motivation",
            "Motivation",
            score,
            self._hybrid_source(insight.source),
            explanation,
            criterion_weights,
            details,
        )

    def _score_culture(
        self,
        candidate: CandidateProfile,
        job: JobProfile,
        criterion_weights: dict[str, float],
    ) -> CriterionScore:
        candidate_text = " ".join(
            [
                list_to_text(candidate.preferences.values),
                list_to_text(candidate.motivation.drivers),
            ]
        )
        job_text = " ".join(
            [
                list_to_text(job.environment.culture_keywords),
                list_to_text(job.target_profile.expected_traits),
                job.environment.team_style,
            ]
        )
        insight = self._text_similarity_insight(candidate_text, job_text)
        values_overlap = self._phrase_match_score(
            " ".join([list_to_text(candidate.preferences.values), list_to_text(candidate.motivation.drivers)]),
            " ".join(
                [
                    list_to_text(job.environment.culture_keywords),
                    list_to_text(job.target_profile.expected_traits),
                    job.environment.team_style,
                ]
            ),
        )
        raw_score = (0.55 * insight.semantic_score) + (0.45 * values_overlap)
        score = self._soft_textual_score(raw_score, floor=22)

        explanation = (
            "Le score confronte les valeurs explicites et moteurs du candidat avec les mots-clés culturels, "
            "les traits attendus et le style d'équipe du poste."
        )
        details = [
            ("Valeurs candidat", list_to_text(candidate.preferences.values) or "Non renseignées"),
            ("Moteurs candidat", list_to_text(candidate.motivation.drivers) or "Non renseignés"),
            ("Culture poste", list_to_text(job.environment.culture_keywords) or "Non renseignée"),
            ("Recouvrement explicite", format_ratio(values_overlap)),
            ("Formule", "55 % similarité sémantique + 45 % valeurs explicites"),
            *self._semantic_detail_rows(
                insight,
                left_label="Valeurs et moteurs candidat",
                right_label="Culture et traits du poste",
            ),
        ]
        return self._criterion(
            "culture",
            "Culture et valeurs",
            score,
            self._hybrid_source(insight.source),
            explanation,
            criterion_weights,
            details,
        )

    def _score_learning_potential(
        self,
        candidate: CandidateProfile,
        job: JobProfile,
        criterion_weights: dict[str, float],
    ) -> CriterionScore:
        candidate_text = " ".join(
            [
                list_to_text(candidate.potential.learning_goals),
                list_to_text(candidate.potential.growth_domains),
                candidate.potential.transferable_experiences,
            ]
        )
        job_text = " ".join(
            [
                list_to_text(skill.name for skill in job.desired_skills),
                list_to_text(job.target_profile.learning_expectations),
                job.target_profile.growth_potential,
            ]
        )
        insight = self._text_similarity_insight(candidate_text, job_text)
        growth_overlap = self._phrase_match_score(
            " ".join([list_to_text(candidate.potential.learning_goals), list_to_text(candidate.potential.growth_domains)]),
            " ".join([list_to_text(job.target_profile.learning_expectations), job.target_profile.growth_potential]),
        )
        raw_score = (0.7 * insight.semantic_score) + (0.3 * growth_overlap)
        score = self._soft_textual_score(raw_score, floor=24)

        explanation = (
            "Le potentiel d'apprentissage mesure à quel point les objectifs de progression du candidat "
            "sont cohérents avec ce que le poste demande ou permet de développer."
        )
        details = [
            ("Objectifs d'apprentissage", list_to_text(candidate.potential.learning_goals) or "Non renseignés"),
            ("Domaines de progression", list_to_text(candidate.potential.growth_domains) or "Non renseignés"),
            ("Attendus du poste", list_to_text(job.target_profile.learning_expectations) or "Non renseignés"),
            ("Recouvrement explicite", format_ratio(growth_overlap)),
            ("Formule", "70 % similarité sémantique + 30 % attentes explicites"),
            *self._semantic_detail_rows(
                insight,
                left_label="Projection de progression candidat",
                right_label="Projection de progression poste",
            ),
        ]
        return self._criterion(
            "learning_potential",
            "Potentiel d'apprentissage",
            score,
            self._hybrid_source(insight.source),
            explanation,
            criterion_weights,
            details,
        )

    def _compute_penalties(self, criteria: Sequence[CriterionScore]) -> List[CompatibilityPenalty]:
        penalties: List[CompatibilityPenalty] = []
        lookup = {criterion.key: criterion for criterion in criteria}

        if lookup["location"].weight > 0 and lookup["location"].score == 0:
            penalties.append(
                CompatibilityPenalty(label="Localisation bloquante pour ce poste", factor=0.65)
            )
        if lookup["availability"].weight > 0 and lookup["availability"].score < 35:
            penalties.append(
                CompatibilityPenalty(label="Disponibilité trop éloignée du besoin du poste", factor=0.85)
            )
        if lookup["languages"].weight > 0 and lookup["languages"].score < 50:
            penalties.append(
                CompatibilityPenalty(label="Couverture linguistique insuffisante", factor=0.9)
            )
        if lookup["required_skills"].weight > 0 and lookup["required_skills"].score < 45:
            penalties.append(
                CompatibilityPenalty(label="Couverture insuffisante des compétences obligatoires", factor=0.8)
            )
        if lookup["contract"].weight > 0 and lookup["contract"].score < 40:
            penalties.append(
                CompatibilityPenalty(label="Type de contrat peu compatible", factor=0.9)
            )
        return penalties

    def _build_summary(
        self,
        criteria: Sequence[CriterionScore],
        penalties: Sequence[CompatibilityPenalty],
    ) -> str:
        active_criteria = [criterion for criterion in criteria if criterion.weight > 0]
        summary_scope = active_criteria or list(criteria)
        top_criteria = sorted(summary_scope, key=lambda item: item.score, reverse=True)[:2]
        low_criteria = sorted(summary_scope, key=lambda item: item.score)[:2]
        strengths = ", ".join(f"{item.label.lower()} ({item.score}%)" for item in top_criteria)
        weaknesses = ", ".join(f"{item.label.lower()} ({item.score}%)" for item in low_criteria)
        if penalties:
            penalty_text = "; pénalités : " + ", ".join(penalty.label for penalty in penalties)
        else:
            penalty_text = ""
        return f"Points forts : {strengths}. Points de vigilance : {weaknesses}{penalty_text}."

    def _resolve_criterion_weights(self, custom_weights: dict[str, float] | None) -> dict[str, float]:
        weights = dict(DEFAULT_CRITERION_WEIGHTS)
        for key, value in (custom_weights or {}).items():
            if key not in weights:
                continue
            if value < 0:
                continue
            weights[key] = float(value)

        total_weight = sum(weights.values())
        if total_weight <= 0:
            fallback_total = sum(DEFAULT_CRITERION_WEIGHTS.values())
            return {key: value / fallback_total for key, value in DEFAULT_CRITERION_WEIGHTS.items()}

        return {key: value / total_weight for key, value in weights.items()}

    def _parse_iso_date(self, raw_value: str | None) -> date | None:
        if not raw_value:
            return None
        try:
            return date.fromisoformat(raw_value)
        except ValueError:
            return None

    def _desired_skill_level_ratio(
        self,
        candidate_skills: Sequence[SkillEntry],
        desired_skills: Sequence[SkillEntry],
    ) -> float:
        if not desired_skills:
            return 1.0

        candidate_lookup = {normalize_text(skill.name): skill.level for skill in candidate_skills if skill.name.strip()}
        total_weight = sum(skill.level for skill in desired_skills)
        if total_weight == 0:
            return 0.0

        accumulated = 0.0
        for desired in desired_skills:
            candidate_level = candidate_lookup.get(normalize_text(desired.name), 0)
            coverage = min(candidate_level / desired.level, 1.0) if desired.level else 0.0
            accumulated += coverage * desired.level
        return accumulated / total_weight

    def _desired_skill_match_details(
        self,
        candidate_skills: Sequence[SkillEntry],
        desired_skills: Sequence[SkillEntry],
    ) -> tuple[List[str], List[str]]:
        candidate_lookup = {normalize_text(skill.name): skill.level for skill in candidate_skills if skill.name.strip()}
        matches: List[str] = []
        missing: List[str] = []
        for desired in desired_skills:
            candidate_level = candidate_lookup.get(normalize_text(desired.name))
            if candidate_level:
                matches.append(f"{desired.name} {candidate_level}/{desired.level}")
            else:
                missing.append(desired.name)
        return matches, missing

    def _candidate_matches_diversity_rule(
        self,
        candidate: CandidateProfile,
        rule: JobDiversityConstraint,
    ) -> bool:
        normalized_value = normalize_text(rule.value)
        if rule.dimension == "gender":
            return normalize_text(candidate.diversity.gender) == normalized_value
        candidate_tags = {normalize_text(tag) for tag in candidate.diversity.self_declared_tags if tag.strip()}
        return normalized_value in candidate_tags

    def _candidate_diversity_snapshot(self, candidate: CandidateProfile) -> str:
        gender_label = GENDER_LABELS.get(candidate.diversity.gender, candidate.diversity.gender)
        tags = list_to_text(self._diversity_value_label("tag", tag) for tag in candidate.diversity.self_declared_tags) or "aucun tag déclaré"
        return f"genre {gender_label} • tags {tags}"

    def _format_diversity_rule(self, rule: JobDiversityConstraint) -> str:
        thresholds: List[str] = []
        if rule.minimum_count > 0:
            thresholds.append(f"min {rule.minimum_count}")
        if rule.target_count is not None:
            thresholds.append(f"cible {rule.target_count}")
        if rule.maximum_count is not None:
            thresholds.append(f"max {rule.maximum_count}")
        threshold_text = ", ".join(thresholds) if thresholds else "sans seuil chiffré"
        priority_label = "requis" if rule.priority == "required" else "préféré"
        value_label = self._diversity_value_label(rule.dimension, rule.value)
        dimension_label = "genre" if rule.dimension == "gender" else "tag"
        return f"{priority_label} {dimension_label} {value_label} ({threshold_text})"

    def _diversity_value_label(self, dimension: str, value: str) -> str:
        if dimension == "gender":
            return GENDER_LABELS.get(value, value)
        return DIVERSITY_TAG_LABELS.get(value, value.replace("_", " "))

    def _split_skill_matches(
        self,
        candidate_skill_names: Sequence[str],
        expected_skills: Sequence[str],
    ) -> tuple[List[str], List[str]]:
        matched: List[str] = []
        missing: List[str] = []
        for skill in expected_skills:
            if self._has_skill(candidate_skill_names, skill):
                matched.append(skill)
            else:
                missing.append(skill)
        return matched, missing

    def _best_matching_term(self, terms: Sequence[str], text: str) -> tuple[str, float]:
        best_term = ""
        best_score = 0.0
        for term in terms:
            if not term.strip():
                continue
            score = self._phrase_match_score(term, text)
            if score > best_score:
                best_term = term
                best_score = score
        return best_term, best_score

    def _text_similarity_insight(self, left: str, right: str) -> TextSimilarityInsight:
        semantic_score, source = self._semantic_similarity(left, right)
        lexical_score = lexical_similarity(left, right)
        shared_tokens = self._meaningful_shared_tokens(left, right)
        return TextSimilarityInsight(
            semantic_score=semantic_score,
            lexical_score=lexical_score,
            source=source,
            shared_tokens=shared_tokens,
            left_excerpt=self._excerpt(left),
            right_excerpt=self._excerpt(right),
        )

    def _semantic_detail_rows(
        self,
        insight: TextSimilarityInsight,
        left_label: str,
        right_label: str,
    ) -> List[tuple[str, str]]:
        if insight.source == "embedding":
            source_text = (
                f"Le modèle d'embedding a renvoyé une similarité cosinus de {format_ratio(insight.semantic_score)} "
                f"sur les deux textes comparés."
            )
        else:
            source_text = (
                f"Pas de score embedding exploitable; le moteur a utilisé un fallback lexical de {format_ratio(insight.semantic_score)}."
            )

        return [
            ("Sortie sémantique", source_text),
            ("Signal lexical brut", format_ratio(insight.lexical_score)),
            ("Ancres lexicales communes", list_to_text(insight.shared_tokens) or "Aucune ancre exacte commune"),
            (left_label, insight.left_excerpt or "Texte vide"),
            (right_label, insight.right_excerpt or "Texte vide"),
        ]

    def _excerpt(self, text: str, max_length: int = 160) -> str:
        compact_text = " ".join((text or "").split())
        if len(compact_text) <= max_length:
            return compact_text
        return compact_text[: max_length - 1].rstrip() + "…"

    def _meaningful_shared_tokens(self, left: str, right: str) -> List[str]:
        shared_tokens = tokenize(left) & tokenize(right)
        filtered_tokens = [
            token
            for token in shared_tokens
            if token not in IGNORED_SHARED_TOKENS and (len(token) >= 3 or token in SHORT_TOKEN_WHITELIST)
        ]
        return sorted(filtered_tokens)[:6]

    def _degree_rank(self, degree: str | None) -> int | None:
        normalized_degree = normalize_text(degree or "")
        if not normalized_degree:
            return None

        for rank, hints in DEGREE_HINTS:
            if any(hint in normalized_degree for hint in hints):
                return rank
        return None

    def _degree_rank_label(self, rank: int | None) -> str:
        return {
            None: "Non interprété",
            1: "Bac",
            2: "Bac+2",
            3: "Bac+3",
            4: "Bac+5",
            5: "Doctorat",
        }[rank]

    def _has_skill(self, candidate_skill_names: Sequence[str], expected_skill: str) -> bool:
        normalized_expected = normalize_text(expected_skill)
        return any(normalize_text(skill_name) == normalized_expected for skill_name in candidate_skill_names)

    def _semantic_similarity(self, left: str, right: str) -> Tuple[float, str]:
        score, source = self.embedding_client.similarity(left, right)
        return max(0.0, min(1.0, score)), source

    def _hybrid_source(self, source: str) -> str:
        return "hybrid" if source == "embedding" else "lexical_fallback"

    def _phrase_match_score(self, left: str, right: str) -> float:
        normalized_left = normalize_text(left)
        normalized_right = normalize_text(right)
        if not normalized_left or not normalized_right:
            return 0.0
        if normalized_left in normalized_right or normalized_right in normalized_left:
            return 1.0
        return fuzzy_token_overlap(normalized_left, normalized_right)

    def _soft_textual_score(self, raw_score: float, floor: int) -> float:
        bounded = max(0.0, min(1.0, raw_score))
        return floor + ((100 - floor) * bounded)
