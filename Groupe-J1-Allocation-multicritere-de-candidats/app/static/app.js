const tabButtons = document.querySelectorAll(".tab-button");
const tabPanels = document.querySelectorAll(".tab-panel");

const candidateForm = document.getElementById("candidate-form");
const jobForm = document.getElementById("job-form");
const candidateList = document.getElementById("candidate-list");
const jobList = document.getElementById("job-list");
const candidateStatus = document.getElementById("candidate-status");
const jobStatus = document.getElementById("job-status");
const compatibilityStatus = document.getElementById("compatibility-status");
const compatibilityMeta = document.getElementById("compatibility-meta");
const compatibilityResults = document.getElementById("compatibility-results");
const compatibilityResultsSection = document.getElementById("compatibility-results-section");
const assignmentStatus = document.getElementById("assignment-status");
const assignmentMeta = document.getElementById("assignment-meta");
const assignmentResults = document.getElementById("assignment-results");
const assignmentResultsSection = document.getElementById("assignment-results-section");
const jumpToCompatibilityResultsButton = document.getElementById("jump-to-compatibility-results");
const jumpToAssignmentResultsButton = document.getElementById("jump-to-assignment-results");
const compatibilityCandidateFilter = document.getElementById("compatibility-candidate-filter");
const compatibilityJobFilter = document.getElementById("compatibility-job-filter");
const compatibilityTopK = document.getElementById("compatibility-top-k");
const compatibilityWeightSummary = document.getElementById("compatibility-weight-summary");
const weightGroupInputs = document.querySelectorAll("[data-weight-group]");
const sliderValueOutputs = document.querySelectorAll("[data-slider-value-for]");
const resetCriterionWeightsButton = document.getElementById("reset-criterion-weights");
const runCompatibilityButton = document.getElementById("run-compatibility");
const runAssignmentButton = document.getElementById("run-assignment");
const heroCandidateCount = document.getElementById("hero-candidate-count");
const heroJobCount = document.getElementById("hero-job-count");
const heroMatchCount = document.getElementById("hero-match-count");
const validationTargets = document.querySelectorAll("input, textarea, select");
const knownDiversityTags = [
  {
    key: "first_generation",
    label: "Première génération",
    description: "Premier parcours d'études supérieures ou de carrière qualifiée dans la famille proche.",
    aliases: ["first_generation", "premiere_generation", "premiere generation", "first gen"],
  },
  {
    key: "reconversion",
    label: "Reconversion",
    description: "Changement de métier ou d'industrie avec transfert de compétences.",
    aliases: ["reconversion", "career_change", "transition"],
  },
  {
    key: "rqth",
    label: "RQTH / handicap déclaré",
    description: "Situation de handicap déclarée ou besoin d'aménagement reconnu.",
    aliases: ["rqth", "handicap", "disability"],
  },
  {
    key: "international",
    label: "Parcours international",
    description: "Expérience de vie, d'études ou de travail dans plusieurs pays ou cultures.",
    aliases: ["international", "intl", "global"],
  },
  {
    key: "caregiver",
    label: "Aidance / proche aidant",
    description: "Responsabilités durables d'aidance ou de charge familiale significative.",
    aliases: ["caregiver", "aidant", "aidance", "carer"],
  },
  {
    key: "rural_background",
    label: "Origine rurale",
    description: "Parcours construit en dehors des grands centres urbains ou des grands bassins d'emploi.",
    aliases: ["rural_background", "rural", "origine_rurale"],
  },
];
const diversityTagAliasMap = knownDiversityTags.reduce((lookup, tag) => {
  tag.aliases.forEach((alias) => {
    lookup[alias] = tag.key;
  });
  return lookup;
}, {});
const diversityTagLabelMap = knownDiversityTags.reduce((lookup, tag) => {
  lookup[tag.key] = tag.label;
  return lookup;
}, {});
const genderLabelMap = {
  female: "Femme",
  male: "Homme",
  non_binary: "Non-binaire",
  other: "Autre",
  undisclosed: "Non renseigné",
};

let cachedCandidates = [];
let cachedJobs = [];
const animatedMetricValues = new WeakMap();
const defaultGroupSliders = {
  practical_fit: 100,
  education_focus: 100,
  experience_growth: 100,
  skills_match: 100,
  diversity_equity: 100,
  role_and_culture: 100,
};
const criterionWeightGroups = {
  practical_fit: {
    label: "Contraintes pratiques",
    criteria: {
      location: 0.10,
      availability: 0.05,
      contract: 0.08,
      salary: 0.08,
    },
  },
  education_focus: {
    label: "Diplôme",
    criteria: {
      education: 0.08,
    },
  },
  experience_growth: {
    label: "Expérience et progression",
    criteria: {
      experience: 0.12,
      learning_potential: 0.05,
    },
  },
  skills_match: {
    label: "Compétences",
    criteria: {
      languages: 0.06,
      required_skills: 0.20,
      desired_skills: 0.10,
    },
  },
  diversity_equity: {
    label: "Diversité et équité",
    criteria: {
      diversity_equity: 0.07,
    },
  },
  role_and_culture: {
    label: "Alignement humain et métier",
    criteria: {
      role_alignment: 0.12,
      motivation: 0.10,
      culture: 0.05,
    },
  },
};
let compatibilityRefreshTimer = null;
let compatibilityRequestSequence = 0;
let latestCompatibilityResponseSequence = 0;
let hasComputedCompatibility = false;
let latestCompatibilityResponse = null;
let latestAssignmentResponse = null;

tabButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const target = button.dataset.tab;

    tabButtons.forEach((item) => item.classList.toggle("active", item === button));
    tabPanels.forEach((panel) => panel.classList.toggle("active", panel.id === `${target}-panel`));
    document.getElementById(`${target}-panel`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

function scrollToSection(target) {
  target?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function splitList(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeDiversityTag(value) {
  const normalized = (value || "")
    .trim()
    .toLowerCase()
    .replace(/[()]/g, "")
    .replace(/[\s-]+/g, "_");
  return diversityTagAliasMap[normalized] || normalized;
}

function humanizeDiversityTag(value) {
  const normalized = normalizeDiversityTag(value);
  return diversityTagLabelMap[normalized] || value;
}

function humanizeGender(value) {
  return genderLabelMap[value] || value;
}

function uniqueValues(values) {
  return Array.from(new Set(values.filter(Boolean)));
}

function parseSkillBlock(value, category) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => {
      const [name, rawLevel] = item.split(":").map((part) => part.trim());
      const numericLevel = Number.parseInt(rawLevel || "3", 10);
      return {
        name,
        level: Number.isNaN(numericLevel) ? 3 : Math.min(Math.max(numericLevel, 1), 5),
        category,
      };
    });
}

function buildDiversityConstraintsFromForm(form) {
  const constraints = [];
  const genderGoal = form.target_profile_gender_goal.value;
  const genderPriority = form.target_profile_gender_goal_priority.value || "preferred";
  if (genderGoal) {
    constraints.push({
      dimension: "gender",
      value: genderGoal.toLowerCase(),
      minimum_count: genderPriority === "required" ? 1 : 0,
      maximum_count: null,
      target_count: 1,
      priority: genderPriority,
      rationale: "Objectif de représentation défini dans le formulaire poste.",
    });
  }

  const selectedTagGoals = selectedValuesByName(form, "target_profile_diversity_tags").map(normalizeDiversityTag);
  const customTagGoals = splitList(form.target_profile_diversity_custom_tags.value).map(normalizeDiversityTag);
  const allTagGoals = uniqueValues([...selectedTagGoals, ...customTagGoals]);
  const tagPriority = form.target_profile_diversity_tags_priority.value || "preferred";

  allTagGoals.forEach((tag) => {
    constraints.push({
      dimension: "tag",
      value: tag,
      minimum_count: tagPriority === "required" ? 1 : 0,
      maximum_count: null,
      target_count: 1,
      priority: tagPriority,
      rationale: "Parcours valorisé dans le formulaire poste.",
    });
  });

  return constraints;
}

function selectedValuesByName(form, name) {
  return Array.from(form.querySelectorAll(`input[name="${name}"]:checked`)).map((input) => input.value);
}

function setStatus(target, message, isError = false) {
  target.textContent = message;
  target.style.color = isError ? "#b91c1c" : "#0f766e";
}

function setMetricValue(target, value) {
  if (target) {
    animateMetricValue(target, Number(value) || 0);
  }
}

function animateMetricValue(target, nextValue) {
  const currentTextValue = Number.parseInt(target.textContent || "0", 10) || 0;
  const previousValue = animatedMetricValues.get(target) ?? currentTextValue;
  const safeNextValue = Math.max(0, nextValue);

  if (previousValue === safeNextValue) {
    target.textContent = String(safeNextValue);
    return;
  }

  const startTime = performance.now();
  const duration = 520;
  target.classList.remove("metric-updated");

  const step = (timestamp) => {
    const progress = Math.min((timestamp - startTime) / duration, 1);
    const eased = 1 - ((1 - progress) ** 3);
    const currentValue = Math.round(previousValue + ((safeNextValue - previousValue) * eased));
    target.textContent = String(currentValue);

    if (progress < 1) {
      window.requestAnimationFrame(step);
      return;
    }

    animatedMetricValues.set(target, safeNextValue);
    target.textContent = String(safeNextValue);
    target.classList.add("metric-updated");
    window.setTimeout(() => target.classList.remove("metric-updated"), 520);
  };

  window.requestAnimationFrame(step);
}

function normalizeOptionalNumber(value) {
  if (!value) {
    return null;
  }
  return Number.parseInt(value, 10);
}

function formatDecimal(value, digits = 2) {
  const rounded = Number.parseFloat(value.toFixed(digits));
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(digits);
}

function formatWeightPercent(weight) {
  return `${formatDecimal(weight * 100, 1)} %`;
}

function collectWeightGroupValues() {
  return Array.from(weightGroupInputs).reduce((groups, input) => {
    const numericValue = Number.parseFloat(input.value || "0");
    const safeValue = Number.isNaN(numericValue) || numericValue < 0 ? 0 : numericValue;
    groups[input.dataset.weightGroup] = safeValue / 100;
    return groups;
  }, {});
}

function deriveCriterionWeights() {
  const groupValues = collectWeightGroupValues();
  return Object.entries(criterionWeightGroups).reduce((weights, [groupKey, groupConfig]) => {
    const multiplier = groupValues[groupKey] ?? 1;
    Object.entries(groupConfig.criteria).forEach(([criterionKey, baseWeight]) => {
      weights[criterionKey] = baseWeight * multiplier;
    });
    return weights;
  }, {});
}

function normalizeCriterionWeights(weights) {
  const sanitizedWeights = Object.entries(weights).reduce((normalized, [criterionKey, rawValue]) => {
    const numericValue = Number.parseFloat(rawValue || "0");
    normalized[criterionKey] = Number.isNaN(numericValue) || numericValue < 0 ? 0 : numericValue;
    return normalized;
  }, {});

  const totalWeight = Object.values(sanitizedWeights).reduce((sum, value) => sum + value, 0);
  if (totalWeight <= 0) {
    return sanitizedWeights;
  }

  return Object.entries(sanitizedWeights).reduce((normalized, [criterionKey, value]) => {
    normalized[criterionKey] = value / totalWeight;
    return normalized;
  }, {});
}

function updateSliderValueOutputs() {
  sliderValueOutputs.forEach((output) => {
    const targetGroup = output.dataset.sliderValueFor;
    const input = document.querySelector(`[data-weight-group="${targetGroup}"]`);
    const numericValue = Number.parseFloat(input?.value || "0");
    const safeValue = Number.isNaN(numericValue) ? 0 : numericValue;
    output.textContent = `${Math.round(safeValue)}%`;
  });
}

function updateCriterionWeightSummary() {
  if (!compatibilityWeightSummary) {
    return;
  }

  updateSliderValueOutputs();
  const weights = normalizeCriterionWeights(deriveCriterionWeights());
  const total = Object.values(weights).reduce((sum, value) => sum + value, 0);
  if (total <= 0) {
    compatibilityWeightSummary.textContent = "Tous les blocs sont à 0. Le calcul ne peut pas être lancé.";
    compatibilityWeightSummary.style.color = "#b91c1c";
    return;
  }

  const groupValues = collectWeightGroupValues();
  const distributionText = Object.entries(criterionWeightGroups)
    .map(([groupKey, groupConfig]) => {
      const groupWeight = Object.keys(groupConfig.criteria)
        .reduce((sum, criterionKey) => sum + (weights[criterionKey] || 0), 0);
      const sliderPercent = Math.round((groupValues[groupKey] ?? 0) * 100);
      return `${groupConfig.label} ${sliderPercent}% -> ${formatWeightPercent(groupWeight / total)}`;
    })
    .join(" • ");

  compatibilityWeightSummary.textContent = `Répartition effective: ${distributionText}`;
  compatibilityWeightSummary.style.color = "#0f766e";
}

function resetCriterionWeights() {
  weightGroupInputs.forEach((input) => {
    const defaultValue = defaultGroupSliders[input.dataset.weightGroup];
    input.value = String(defaultValue);
  });
  updateCriterionWeightSummary();
}

function compatibilityPayload() {
  return {
    candidate_ids: compatibilityCandidateFilter.value ? [compatibilityCandidateFilter.value] : [],
    job_ids: compatibilityJobFilter.value ? [compatibilityJobFilter.value] : [],
    top_k_per_candidate: Number.parseInt(compatibilityTopK.value || "5", 10),
    criterion_weights: normalizeCriterionWeights(deriveCriterionWeights()),
  };
}

function assignmentPayload() {
  return {
    candidate_ids: compatibilityCandidateFilter.value ? [compatibilityCandidateFilter.value] : [],
    job_ids: compatibilityJobFilter.value ? [compatibilityJobFilter.value] : [],
    criterion_weights: normalizeCriterionWeights(deriveCriterionWeights()),
    minimum_score: 35,
    enforce_location: true,
    enforce_required_skills: true,
    enforce_contract: true,
    enforce_languages: true,
    enforce_availability: false,
    enforce_diversity_requirements: true,
    max_solver_time_seconds: 10,
  };
}

function clampScore(value) {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function computePenaltiesForCriteria(criteria) {
  const penalties = [];
  const lookup = Object.fromEntries(criteria.map((criterion) => [criterion.key, criterion]));

  if (lookup.location?.weight > 0 && lookup.location.score === 0) {
    penalties.push({ label: "Localisation bloquante pour ce poste", factor: 0.65 });
  }
  if (lookup.availability?.weight > 0 && lookup.availability.score < 35) {
    penalties.push({ label: "Disponibilité trop éloignée du besoin du poste", factor: 0.85 });
  }
  if (lookup.languages?.weight > 0 && lookup.languages.score < 50) {
    penalties.push({ label: "Couverture linguistique insuffisante", factor: 0.9 });
  }
  if (lookup.required_skills?.weight > 0 && lookup.required_skills.score < 45) {
    penalties.push({ label: "Couverture insuffisante des compétences obligatoires", factor: 0.8 });
  }
  if (lookup.contract?.weight > 0 && lookup.contract.score < 40) {
    penalties.push({ label: "Type de contrat peu compatible", factor: 0.9 });
  }

  return penalties;
}

function computeResultWithWeights(result, criterionWeights) {
  const normalizedWeights = normalizeCriterionWeights(criterionWeights);
  const criteria = result.criteria.map((criterion) => {
    const weight = normalizedWeights[criterion.key] || 0;
    const weightedScore = Number((criterion.score * weight).toFixed(2));
    return {
      ...criterion,
      weight,
      weighted_score: weightedScore,
    };
  });

  const baseScore = Math.min(
    100,
    Number(criteria.reduce((sum, criterion) => sum + (criterion.score * criterion.weight), 0).toFixed(2)),
  );
  let finalScore = baseScore;
  computePenaltiesForCriteria(criteria).forEach((penalty) => {
    finalScore *= penalty.factor;
  });

  return {
    ...result,
    base_score: baseScore,
    overall_score: clampScore(finalScore),
    criteria,
  };
}

function currentWeightedResults() {
  if (!latestCompatibilityResponse?.results) {
    return [];
  }

  const criterionWeights = normalizeCriterionWeights(deriveCriterionWeights());
  return latestCompatibilityResponse.results.map((result) => computeResultWithWeights(result, criterionWeights));
}

function updateScoreDisplay(element, nextScore) {
  if (!element) {
    return;
  }

  const safeTarget = Math.max(0, Math.min(100, Number.isNaN(nextScore) ? 0 : nextScore));
  element.dataset.targetScore = String(safeTarget);
  element.textContent = `${safeTarget}%`;
  const meter = element.closest(".criterion-pill, .overall-score-card")?.querySelector("[data-score-fill]");
  if (meter) {
    meter.style.setProperty("--score-fill", `${safeTarget}%`);
  }
}

function updateCompatibilityScoresInPlace() {
  if (!latestCompatibilityResponse?.results?.length) {
    return;
  }

  const weightedResults = currentWeightedResults();
  const weightedByKey = new Map(
    weightedResults.map((result) => [`${result.candidate_id}::${result.job_id}`, result]),
  );

  compatibilityResults.querySelectorAll(".compatibility-item").forEach((article) => {
    const resultKey = article.dataset.resultKey;
    const weightedResult = weightedByKey.get(resultKey);
    if (!weightedResult) {
      return;
    }

    const overallElement = article.querySelector('[data-role="overall-score"]');
    updateScoreDisplay(overallElement, weightedResult.overall_score);

    const baseScoreElement = article.querySelector('[data-role="base-score"]');
    if (baseScoreElement) {
      baseScoreElement.textContent = `Score brut ${Math.round(weightedResult.base_score)}% avant pénalités éventuelles`;
    }

    weightedResult.criteria.forEach((criterion) => {
      const metaElement = article.querySelector(
        `[data-role="criterion-meta"][data-criterion-key="${criterion.key}"]`,
      );
      if (metaElement) {
        metaElement.textContent = `${criterion.score}% • poids ${formatWeightPercent(criterion.weight)} • source ${criterion.source}`;
      }
    });
  });

  compatibilityResults.querySelectorAll("[data-role='group-average']").forEach((element) => {
    const jobId = element.dataset.jobId;
    const groupResults = weightedResults.filter((result) => result.job_id === jobId);
    if (!groupResults.length) {
      return;
    }
    const averageScore = Math.round(
      groupResults.reduce((sum, result) => sum + result.overall_score, 0) / groupResults.length,
    );
    element.textContent = `Moyenne ${averageScore}%`;
  });
}

async function runCompatibilityCalculation(options = {}) {
  const { silent = false, statusMessage = "Calcul en cours..." } = options;
  if (compatibilityRefreshTimer) {
    window.clearTimeout(compatibilityRefreshTimer);
    compatibilityRefreshTimer = null;
  }

  const payload = compatibilityPayload();
  const totalWeight = Object.values(payload.criterion_weights).reduce((sum, value) => sum + value, 0);
  if (totalWeight <= 0) {
    throw new Error("Veuillez laisser au moins un bloc avec un poids strictement positif.");
  }

  const requestSequence = compatibilityRequestSequence + 1;
  compatibilityRequestSequence = requestSequence;
  setStatus(compatibilityStatus, statusMessage);

  const response = await saveRecord("/api/compatibility", payload);
  if (requestSequence < latestCompatibilityResponseSequence) {
    return null;
  }

  latestCompatibilityResponseSequence = requestSequence;
  hasComputedCompatibility = true;
  renderCompatibilityResults(response);
  setStatus(compatibilityStatus, silent ? "Compatibilités mises à jour en direct." : "Calcul terminé.");
  return response;
}

function scheduleLiveCompatibilityRefresh() {
  if (!cachedCandidates.length || !cachedJobs.length) {
    return;
  }

  if (compatibilityRefreshTimer) {
    window.clearTimeout(compatibilityRefreshTimer);
  }

  compatibilityRefreshTimer = window.setTimeout(async () => {
    compatibilityRefreshTimer = null;
    try {
      await runCompatibilityCalculation({
        silent: true,
        statusMessage: "Mise à jour en direct des compatibilités...",
      });
    } catch (error) {
      setStatus(compatibilityStatus, `Erreur: ${error.message}`, true);
    }
  }, 260);
}

function invalidatePendingCompatibilityResponses() {
  if (compatibilityRefreshTimer) {
    window.clearTimeout(compatibilityRefreshTimer);
    compatibilityRefreshTimer = null;
  }
  latestCompatibilityResponseSequence = compatibilityRequestSequence + 1;
}

function applySliderChangesLocally() {
  invalidatePendingCompatibilityResponses();
  updateCriterionWeightSummary();
  const normalizedWeights = normalizeCriterionWeights(deriveCriterionWeights());
  const totalWeight = Object.values(normalizedWeights).reduce((sum, value) => sum + value, 0);
  if (totalWeight <= 0) {
    setStatus(compatibilityStatus, "Laissez au moins un bloc au-dessus de 0 % pour recalculer les scores.");
    if (latestAssignmentResponse) {
      setStatus(assignmentStatus, "Les poids ont changé. Relancez l'affectation optimale pour recalculer CP-SAT.");
    }
    return;
  }
  if (!hasComputedCompatibility) {
    return;
  }

  const weightedResults = latestCompatibilityResponse.results.map((result) => computeResultWithWeights(result, normalizedWeights));
  renderCompatibilityResults(
    {
      ...latestCompatibilityResponse,
      results: weightedResults,
    },
    {
      storePayload: false,
      scroll: false,
    },
  );
  setStatus(compatibilityStatus, "Compatibilités mises à jour localement.");
  if (latestAssignmentResponse) {
    setStatus(assignmentStatus, "Les poids ont changé. Relancez l'affectation optimale pour recalculer CP-SAT.");
  }
}

function frenchValidationMessage(field) {
  const { validity } = field;

  if (validity.valueMissing) {
    return "Ce champ est obligatoire.";
  }
  if (validity.typeMismatch && field.type === "email") {
    return "Veuillez saisir une adresse email valide.";
  }
  if (validity.badInput || validity.typeMismatch) {
    return "La valeur saisie n'est pas valide.";
  }
  if (validity.rangeUnderflow) {
    return `La valeur minimale autorisée est ${field.min}.`;
  }
  if (validity.rangeOverflow) {
    return `La valeur maximale autorisée est ${field.max}.`;
  }
  if (validity.tooShort) {
    return `Veuillez saisir au moins ${field.minLength} caractères.`;
  }
  if (validity.tooLong) {
    return `Veuillez saisir au maximum ${field.maxLength} caractères.`;
  }
  return "";
}

function attachFrenchValidation() {
  validationTargets.forEach((field) => {
    field.addEventListener("invalid", () => {
      field.setCustomValidity(frenchValidationMessage(field));
    });

    field.addEventListener("input", () => {
      field.setCustomValidity("");
    });

    field.addEventListener("change", () => {
      field.setCustomValidity("");
    });
  });
}

function candidatePayload(form) {
  const selectedKnownDiversityTags = selectedValuesByName(form, "diversity_self_declared_tags");
  const customDiversityTags = splitList(form.diversity_custom_tags.value).map(normalizeDiversityTag);
  return {
    full_name: form.full_name.value.trim(),
    email: form.email.value.trim() || null,
    current_title: form.current_title.value.trim() || null,
    years_experience: Number.parseInt(form.years_experience.value || "0", 10),
    location: {
      city: form.location_city.value.trim(),
      country: form.location_country.value.trim() || "France",
      remote_preference: form.location_remote_preference.value,
      mobility_km: Number.parseInt(form.location_mobility_km.value || "0", 10),
    },
    skills: [
      ...parseSkillBlock(form.skills_technical.value, "technical"),
      ...parseSkillBlock(form.skills_functional.value, "functional"),
      ...parseSkillBlock(form.skills_language.value, "language"),
    ],
    education: {
      degree: form.education_degree.value.trim() || null,
      field_of_study: form.education_field_of_study.value.trim() || null,
      certifications: splitList(form.education_certifications.value),
    },
    preferences: {
      target_roles: splitList(form.preferences_target_roles.value),
      target_sectors: splitList(form.preferences_target_sectors.value),
      contract_types: selectedValuesByName(form, "preferences_contract_types"),
      salary_min: normalizeOptionalNumber(form.preferences_salary_min.value),
      values: splitList(form.preferences_values.value),
    },
    motivation: {
      free_text: form.motivation_free_text.value.trim(),
      drivers: splitList(form.motivation_drivers.value),
      mission_preferences: splitList(form.motivation_mission_preferences.value),
    },
    potential: {
      learning_goals: splitList(form.potential_learning_goals.value),
      transferable_experiences: form.potential_transferable_experiences.value.trim(),
      growth_domains: splitList(form.potential_growth_domains.value),
    },
    availability: {
      start_date: form.availability_start_date.value || null,
      schedule: form.availability_schedule.value,
      constraints: form.availability_constraints.value.trim(),
    },
    diversity: {
      gender: form.diversity_gender.value,
      self_declared_tags: uniqueValues([
        ...selectedKnownDiversityTags,
        ...customDiversityTags,
      ]),
      equity_notes: form.diversity_equity_notes.value.trim(),
    },
  };
}

function jobPayload(form) {
  return {
    title: form.title.value.trim(),
    team: form.team.value.trim() || null,
    location: {
      city: form.location_city.value.trim(),
      country: form.location_country.value.trim() || "France",
      work_mode: form.location_work_mode.value,
    },
    requirements: {
      minimum_degree: form.requirements_minimum_degree.value.trim() || null,
      minimum_years_experience: Number.parseInt(
        form.requirements_minimum_years_experience.value || "0",
        10,
      ),
      mandatory_skills: splitList(form.requirements_mandatory_skills.value),
      languages: splitList(form.requirements_languages.value),
    },
    desired_skills: parseSkillBlock(form.desired_skills.value, "technical"),
    missions: form.missions.value.trim(),
    environment: {
      team_style: form.environment_team_style.value.trim(),
      pace: form.environment_pace.value.trim(),
      culture_keywords: splitList(form.environment_culture_keywords.value),
    },
    conditions: {
      salary_min: normalizeOptionalNumber(form.conditions_salary_min.value),
      salary_max: normalizeOptionalNumber(form.conditions_salary_max.value),
      contract_type: form.conditions_contract_type.value,
      start_date: form.conditions_start_date.value || null,
      capacity: Number.parseInt(form.conditions_capacity.value || "1", 10),
    },
    target_profile: {
      expected_traits: splitList(form.target_profile_expected_traits.value),
      growth_potential: form.target_profile_growth_potential.value.trim(),
      learning_expectations: splitList(form.target_profile_learning_expectations.value),
      diversity_constraints: buildDiversityConstraintsFromForm(form),
    },
  };
}

async function saveRecord(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Request failed");
  }

  return response.json();
}

function fillSelectOptions(select, items, getLabel) {
  const placeholder = select.querySelector('option[value=""]');
  select.innerHTML = "";
  if (placeholder) {
    select.appendChild(placeholder);
  }

  items.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = getLabel(item);
    select.appendChild(option);
  });
}

function formatList(values, fallback = "Non renseigné") {
  return values && values.length ? values.join(", ") : fallback;
}

function formatSkills(skills, fallback = "Non renseigné") {
  return skills && skills.length
    ? skills.map((skill) => `${skill.name} (${skill.level}/5)`).join(", ")
    : fallback;
}

function animateScoreElements(root = document) {
  const scoreElements = root.querySelectorAll("[data-target-score]");

  scoreElements.forEach((element, index) => {
    const targetScore = Number.parseInt(element.dataset.targetScore || "0", 10);
    const safeTarget = Math.max(0, Math.min(100, Number.isNaN(targetScore) ? 0 : targetScore));
    const startTime = performance.now() + (index * 45);
    const duration = 720;
    const meter = element.closest(".criterion-pill, .overall-score-card")?.querySelector("[data-score-fill]");

    element.classList.remove("score-animated");
    element.classList.add("score-loading");
    element.textContent = "…";
    if (meter) {
      meter.style.setProperty("--score-fill", "0%");
      meter.classList.remove("score-fill-active");
    }

    const step = (timestamp) => {
      if (timestamp < startTime) {
        window.requestAnimationFrame(step);
        return;
      }

      const progress = Math.min((timestamp - startTime) / duration, 1);
      const eased = 1 - ((1 - progress) ** 4);
      const value = Math.round(safeTarget * eased);
      element.textContent = `${value}%`;

      if (progress < 1) {
        window.requestAnimationFrame(step);
        return;
      }

      element.textContent = `${safeTarget}%`;
      element.classList.remove("score-loading");
      element.classList.add("score-animated");

      if (meter) {
        meter.style.setProperty("--score-fill", `${safeTarget}%`);
        meter.classList.add("score-fill-active");
      }
    };

    window.requestAnimationFrame(step);
  });
}

function renderTags(values, fallback = "Non renseigné") {
  if (!values || !values.length) {
    return `<span class="inline-text">${fallback}</span>`;
  }

  return `
    <div class="tag-list">
      ${values.map((value) => `<span class="info-tag">${value}</span>`).join("")}
    </div>
  `;
}

function renderDetailRows(rows) {
  return `
    <div class="detail-rows">
      ${rows
        .map(
          (row) => `
            <div class="detail-row">
              <span class="detail-label">${row.label}</span>
              <span class="detail-value">${row.value || "Non renseigné"}</span>
            </div>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderExplanationDetails(details) {
  if (!details || !details.length) {
    return "";
  }

  return `
    <div class="explanation-detail-list">
      ${details
        .map(
          (detail) => `
            <div class="explanation-detail-row">
              <span class="explanation-detail-label">${detail.label}</span>
              <span class="explanation-detail-value">${detail.value}</span>
            </div>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderCandidateList(items) {
  if (!items.length) {
    candidateList.innerHTML = "<p class=\"record-meta\">Aucun candidat enregistré.</p>";
    return;
  }

  candidateList.innerHTML = items
    .map(
      (item) => `
        <article class="record-item expandable-item" data-expanded="false">
          <button type="button" class="expandable-toggle" aria-expanded="false">
            <span class="expandable-main">
              <h3>${item.full_name}</h3>
              <p class="record-meta">${item.current_title || "Titre non renseigné"} • ${item.location.city} • ${item.years_experience} an(s)</p>
              <p class="record-meta">Compétences: ${item.skills.length} • Moteurs: ${formatList(item.motivation.drivers, "non renseignés")}</p>
            </span>
            <span class="toggle-label">
              <span class="toggle-text">Voir le profil</span>
              <span class="toggle-arrow" aria-hidden="true">▾</span>
            </span>
          </button>
          <div class="expandable-details" hidden>
            <div class="detail-grid">
              <div class="detail-card">
                <strong>Localisation</strong>
                ${renderDetailRows([
                  { label: "Ville", value: `${item.location.city}, ${item.location.country}` },
                  { label: "Mode", value: item.location.remote_preference },
                  { label: "Mobilité", value: `${item.location.mobility_km} km` },
                ])}
              </div>
              <div class="detail-card">
                <strong>Formation</strong>
                ${renderDetailRows([
                  { label: "Diplôme", value: item.education.degree || "Non renseigné" },
                  { label: "Domaine", value: item.education.field_of_study || "Non renseigné" },
                ])}
              </div>
              <div class="detail-card detail-card-wide">
                <strong>Compétences</strong>
                ${renderTags(item.skills.map((skill) => `${skill.name} ${skill.level}/5`), "Non renseigné")}
              </div>
              <div class="detail-card">
                <strong>Préférences</strong>
                ${renderDetailRows([
                  { label: "Salaire min", value: item.preferences.salary_min ? `${item.preferences.salary_min} EUR` : "Non renseigné" },
                ])}
                <div class="detail-subsection">
                  <span class="detail-subtitle">Postes visés</span>
                  ${renderTags(item.preferences.target_roles)}
                </div>
                <div class="detail-subsection">
                  <span class="detail-subtitle">Secteurs</span>
                  ${renderTags(item.preferences.target_sectors)}
                </div>
                <div class="detail-subsection">
                  <span class="detail-subtitle">Contrats</span>
                  ${renderTags(item.preferences.contract_types)}
                </div>
              </div>
              <div class="detail-card">
                <strong>Motivation</strong>
                <div class="detail-subsection">
                  <span class="detail-subtitle">Texte libre</span>
                  <p class="detail-paragraph">${item.motivation.free_text}</p>
                </div>
                <div class="detail-subsection">
                  <span class="detail-subtitle">Moteurs</span>
                  ${renderTags(item.motivation.drivers)}
                </div>
              </div>
              <div class="detail-card">
                <strong>Potentiel</strong>
                <div class="detail-subsection">
                  <span class="detail-subtitle">Objectifs d'apprentissage</span>
                  ${renderTags(item.potential.learning_goals)}
                </div>
                <div class="detail-subsection">
                  <span class="detail-subtitle">Domaines de progression</span>
                  ${renderTags(item.potential.growth_domains)}
                </div>
              </div>
              <div class="detail-card">
                <strong>Diversité et équité</strong>
                ${renderDetailRows([
                  { label: "Genre", value: humanizeGender(item.diversity?.gender || "undisclosed") },
                ])}
                <div class="detail-subsection">
                  <span class="detail-subtitle">Tags déclarés</span>
                  ${renderTags((item.diversity?.self_declared_tags || []).map(humanizeDiversityTag), "Aucun tag déclaré")}
                </div>
              </div>
              <div class="detail-card detail-card-wide">
                <strong>Expériences transférables</strong>
                <p class="detail-paragraph">${item.potential.transferable_experiences || "Non renseigné"}</p>
              </div>
              <div class="detail-card detail-card-wide">
                <strong>Notes d'équité</strong>
                <p class="detail-paragraph">${item.diversity?.equity_notes || "Non renseigné"}</p>
              </div>
            </div>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderJobList(items) {
  if (!items.length) {
    jobList.innerHTML = "<p class=\"record-meta\">Aucun poste enregistré.</p>";
    return;
  }

  jobList.innerHTML = items
    .map(
      (item) => `
        <article class="record-item expandable-item" data-expanded="false">
          <button type="button" class="expandable-toggle" aria-expanded="false">
            <span class="expandable-main">
              <h3>${item.title}</h3>
              <p class="record-meta">${item.team || "Équipe non renseignée"} • ${item.location.city} • ${item.location.work_mode}</p>
              <p class="record-meta">Capacité: ${item.conditions.capacity} • Exigences: ${formatList(item.requirements.mandatory_skills, "aucune")}</p>
            </span>
            <span class="toggle-label">
              <span class="toggle-text">Voir le poste</span>
              <span class="toggle-arrow" aria-hidden="true">▾</span>
            </span>
          </button>
          <div class="expandable-details" hidden>
            <div class="detail-grid">
              <div class="detail-card">
                <strong>Localisation</strong>
                ${renderDetailRows([
                  { label: "Ville", value: `${item.location.city}, ${item.location.country}` },
                  { label: "Mode", value: item.location.work_mode },
                ])}
              </div>
              <div class="detail-card">
                <strong>Conditions</strong>
                ${renderDetailRows([
                  { label: "Contrat", value: item.conditions.contract_type.toUpperCase() },
                  { label: "Capacité", value: `${item.conditions.capacity} place(s)` },
                  {
                    label: "Salaire",
                    value: `${item.conditions.salary_min || "?"} - ${item.conditions.salary_max || "?"} EUR`,
                  },
                ])}
              </div>
              <div class="detail-card detail-card-wide">
                <strong>Missions</strong>
                <p class="detail-paragraph">${item.missions}</p>
              </div>
              <div class="detail-card">
                <strong>Exigences dures</strong>
                ${renderDetailRows([
                  { label: "Diplôme", value: item.requirements.minimum_degree || "Non renseigné" },
                  { label: "Expérience", value: `${item.requirements.minimum_years_experience} an(s)` },
                ])}
                <div class="detail-subsection">
                  <span class="detail-subtitle">Compétences obligatoires</span>
                  ${renderTags(item.requirements.mandatory_skills)}
                </div>
              </div>
              <div class="detail-card">
                <strong>Compétences souhaitées</strong>
                ${renderTags(item.desired_skills.map((skill) => `${skill.name} ${skill.level}/5`), "Non renseigné")}
              </div>
              <div class="detail-card">
                <strong>Environnement</strong>
                ${renderDetailRows([
                  { label: "Style d'équipe", value: item.environment.team_style || "Non renseigné" },
                  { label: "Rythme", value: item.environment.pace || "Non renseigné" },
                ])}
                <div class="detail-subsection">
                  <span class="detail-subtitle">Culture</span>
                  ${renderTags(item.environment.culture_keywords)}
                </div>
              </div>
              <div class="detail-card detail-card-wide">
                <strong>Profil recherché</strong>
                <div class="detail-subsection">
                  <span class="detail-subtitle">Traits attendus</span>
                  ${renderTags(item.target_profile.expected_traits)}
                </div>
                <div class="detail-subsection">
                  <span class="detail-subtitle">Apprentissage attendu</span>
                  ${renderTags(item.target_profile.learning_expectations)}
                </div>
                <div class="detail-subsection">
                  <span class="detail-subtitle">Potentiel d'évolution</span>
                  <p class="detail-paragraph">${item.target_profile.growth_potential || "Non renseigné"}</p>
                </div>
              </div>
              <div class="detail-card detail-card-wide">
                <strong>Objectifs diversité / équité</strong>
                ${renderTags(
                  (item.target_profile.diversity_constraints || []).map(
                    (constraint) => `${constraint.priority === "required" ? "requis" : "préféré"} • ${constraint.dimension === "gender" ? `genre ${humanizeGender(constraint.value)}` : humanizeDiversityTag(constraint.value)}${constraint.minimum_count ? ` • min ${constraint.minimum_count}` : ""}${constraint.target_count != null ? ` • cible ${constraint.target_count}` : ""}${constraint.maximum_count != null ? ` • max ${constraint.maximum_count}` : ""}`,
                  ),
                  "Aucun objectif explicite",
                )}
              </div>
            </div>
          </div>
        </article>
      `,
    )
    .join("");
}

async function loadCandidates() {
  const response = await fetch("/api/candidates");
  const items = await response.json();
  cachedCandidates = items;
  setMetricValue(heroCandidateCount, items.length);
  renderCandidateList(items);
  fillSelectOptions(
    compatibilityCandidateFilter,
    items,
    (item) => `${item.full_name} - ${item.current_title || "Profil sans titre"}`,
  );
}

async function loadJobs() {
  const response = await fetch("/api/jobs");
  const items = await response.json();
  cachedJobs = items;
  setMetricValue(heroJobCount, items.length);
  renderJobList(items);
  fillSelectOptions(
    compatibilityJobFilter,
    items,
    (item) => `${item.title} - ${item.location.city}`,
  );
}

function renderCompatibilityResults(payload, options = {}) {
  const { storePayload = true, scroll = true } = options;
  const results = payload.results || [];
  if (storePayload) {
    latestCompatibilityResponse = JSON.parse(JSON.stringify(payload));
  }
  setMetricValue(heroMatchCount, results.length);
  compatibilityMeta.textContent = `Mode embeddings: ${payload.embedding_mode} • Modèle: ${payload.embedding_model} • Résultats: ${results.length}`;

  if (!results.length) {
    compatibilityResults.innerHTML = "<p class=\"record-meta\">Aucun résultat à afficher.</p>";
    return;
  }

  const groupedByJob = results.reduce((groups, item) => {
    if (!groups[item.job_id]) {
      groups[item.job_id] = {
        jobTitle: item.job_title,
        items: [],
      };
    }
    groups[item.job_id].items.push(item);
    return groups;
  }, {});

  compatibilityResults.innerHTML = Object.values(groupedByJob)
    .sort((left, right) => left.jobTitle.localeCompare(right.jobTitle, "fr"))
    .map((group) => {
      const sortedItems = [...group.items].sort((left, right) => right.overall_score - left.overall_score);
      const averageScore = Math.round(
        sortedItems.reduce((sum, item) => sum + item.overall_score, 0) / sortedItems.length,
      );

      const cardsHtml = sortedItems
        .map((item) => {
      const criteriaHtml = item.criteria
        .map(
          (criterion) => `
            <div class="criterion-pill">
              <strong class="criterion-score-value" data-target-score="${criterion.score}">0%</strong>
              <span>${criterion.label}</span>
              <span class="criterion-meter" aria-hidden="true">
                <span class="criterion-meter-fill" data-score-fill></span>
              </span>
              <span>Source: ${criterion.source}</span>
            </div>
          `,
        )
        .join("");

      const penaltiesHtml = (item.penalties || [])
        .map((penalty) => `<span class="badge">${penalty.label}</span>`)
        .join("");

      const explanationsHtml = item.criteria
        .map(
          (criterion) => `
            <div class="explanation-item">
              <div class="explanation-head">
                <strong>${criterion.label}</strong>
                <span data-role="criterion-meta" data-criterion-key="${criterion.key}">${criterion.score}% • poids ${formatWeightPercent(criterion.weight)} • source ${criterion.source}</span>
              </div>
              <p>${criterion.explanation}</p>
              ${renderExplanationDetails(criterion.details)}
            </div>
          `,
        )
        .join("");

      const penaltyDetailsHtml = (item.penalties || []).length
        ? `
          <div class="explanation-group">
            <h4>Pénalités appliquées</h4>
            ${(item.penalties || [])
              .map(
                (penalty) => `
                  <div class="explanation-item">
                    <div class="explanation-head">
                      <strong>${penalty.label}</strong>
                      <span>facteur ${penalty.factor}</span>
                    </div>
                  </div>
                `,
              )
              .join("")}
          </div>
        `
        : "";

      return `
        <article class="record-item compatibility-item" data-expanded="false" data-result-key="${item.candidate_id}::${item.job_id}">
          <button type="button" class="compatibility-toggle" aria-expanded="false">
            <span class="compatibility-header-main">
              <span class="compatibility-kicker">Compatibilité candidat-poste</span>
              <h3>${item.candidate_name} -> ${item.job_title}</h3>
              <p class="record-meta" data-role="base-score">Score brut ${Math.round(item.base_score)}% avant pénalités éventuelles</p>
            </span>
              <span class="compatibility-header-side">
              <span class="overall-score-card">
                <span class="overall-score-value" data-role="overall-score" data-target-score="${item.overall_score}">0%</span>
                <span class="overall-score-label">Compatibilité globale</span>
                <span class="overall-score-ring" data-score-fill aria-hidden="true"></span>
              </span>
              <span class="toggle-label">
                <span class="toggle-text">Voir les explications</span>
                <span class="toggle-arrow" aria-hidden="true">▾</span>
              </span>
            </span>
          </button>
          <div class="criteria-grid">${criteriaHtml}</div>
          <p class="summary">${item.summary}</p>
          ${penaltiesHtml ? `<div class="badge-row">${penaltiesHtml}</div>` : ""}
          <div class="compatibility-details" hidden>
            <div class="explanation-group">
              <h4>Explications par critère</h4>
              ${explanationsHtml}
            </div>
            ${penaltyDetailsHtml}
          </div>
        </article>
      `;
        })
        .join("");

      return `
        <section class="compatibility-group" data-expanded="false">
          <button type="button" class="compatibility-group-toggle" aria-expanded="false">
            <div class="compatibility-group-header">
              <div>
                <p class="compatibility-group-kicker">Poste</p>
                <h3>${group.jobTitle}</h3>
              </div>
              <div class="compatibility-group-metrics">
                <span class="badge">${sortedItems.length} candidat(s)</span>
                <span class="badge" data-role="group-average" data-job-id="${sortedItems[0]?.job_id || ""}">Moyenne ${averageScore}%</span>
                <span class="group-toggle-label">
                  <span class="group-toggle-text">Voir les compatibilités</span>
                  <span class="toggle-arrow" aria-hidden="true">▾</span>
                </span>
              </div>
            </div>
          </button>
          <div class="compatibility-group-list" hidden>
            ${cardsHtml}
          </div>
        </section>
      `;
    })
    .join("");

  animateScoreElements(compatibilityResults);
  if (scroll) {
    scrollToSection(compatibilityResultsSection);
  }
}

function renderAssignmentResults(payload) {
  latestAssignmentResponse = JSON.parse(JSON.stringify(payload));
  assignmentMeta.textContent = [
    `Solveur: ${payload.solver_status}`,
    `Score total: ${payload.total_score}`,
    `Affectations: ${payload.assigned_count}`,
    `Paires éligibles: ${payload.eligible_pairs}/${payload.considered_pairs}`,
  ].join(" • ");

  if (!payload.assignments?.length) {
    let emptyStateMessage = "Aucune paire n'a satisfait les contraintes d'éligibilité ou la capacité disponible.";
    if (payload.solver_status === "infeasible") {
      emptyStateMessage = "Le modèle CP-SAT est infaisable avec les contraintes actives. Vérifiez surtout les contraintes d'éligibilité et de diversité.";
    } else if (payload.eligible_pairs > 0) {
      emptyStateMessage = "Des paires étaient éligibles, mais aucune n'a pu être retenue par l'optimisation sous contraintes.";
    }

    assignmentResults.innerHTML = `
      <article class="record-item">
        <h3>Aucune affectation retenue</h3>
        <p class="record-meta">${emptyStateMessage}</p>
      </article>
    `;
    return;
  }

  const loadsHtml = (payload.job_loads || [])
    .map(
      (jobLoad) => `
        <div class="detail-card">
          <strong>${jobLoad.job_title}</strong>
          ${renderDetailRows([
            { label: "Capacité", value: `${jobLoad.capacity} place(s)` },
            { label: "Affectés", value: `${jobLoad.assigned_count}` },
            { label: "Restant", value: `${jobLoad.remaining_capacity}` },
          ])}
        </div>
      `,
    )
    .join("");

  const assignmentsHtml = payload.assignments
    .map(
      (item) => `
        <article class="record-item">
          <div class="assignment-card-head">
            <div>
              <p class="compatibility-kicker">Affectation retenue</p>
              <h3>${item.candidate_name} -> ${item.job_title}</h3>
              <p class="record-meta">Score brut ${Math.round(item.base_score)}% • Score final ${item.overall_score}%</p>
            </div>
            <div class="badge-row">
              <span class="badge">Score ${item.overall_score}%</span>
              ${(item.penalties || []).map((penalty) => `<span class="badge">${penalty.label}</span>`).join("")}
            </div>
          </div>
          <p class="summary">${item.summary}</p>
          <div class="criteria-grid">
            ${item.criteria
              .map(
                (criterion) => `
                  <div class="criterion-pill">
                    <strong class="criterion-score-value" data-target-score="${criterion.score}">0%</strong>
                    <span>${criterion.label}</span>
                    <span class="criterion-meter" aria-hidden="true">
                      <span class="criterion-meter-fill" data-score-fill></span>
                    </span>
                    <span>Poids ${formatWeightPercent(criterion.weight)}</span>
                  </div>
                `,
              )
              .join("")}
          </div>
        </article>
      `,
    )
    .join("");

  const unassignedHtml = payload.unassigned_candidates?.length
    ? `
      <section class="assignment-block">
        <div class="panel-banner panel-banner-compact">
          <p class="section-kicker panel-banner-kicker">Candidats non affectés</p>
          <h3>${payload.unassigned_count} profil(s)</h3>
        </div>
        <div class="record-list">
          ${payload.unassigned_candidates
            .map(
              (candidate) => `
                <article class="record-item">
                  <h3>${candidate.candidate_name}</h3>
                  <p class="record-meta">${candidate.reason}</p>
                </article>
              `,
            )
            .join("")}
        </div>
      </section>
    `
    : "";

  assignmentResults.innerHTML = `
    <section class="assignment-block">
      <div class="panel-banner panel-banner-compact">
        <p class="section-kicker panel-banner-kicker">Charge par poste</p>
        <h3>Capacités consommées</h3>
      </div>
      <div class="detail-grid">${loadsHtml}</div>
    </section>
    <section class="assignment-block">
      <div class="panel-banner panel-banner-compact">
        <p class="section-kicker panel-banner-kicker">Affectations optimales</p>
        <h3>${payload.assigned_count} affectation(s) retenue(s)</h3>
      </div>
      <div class="record-list">${assignmentsHtml}</div>
    </section>
    ${unassignedHtml}
  `;

  animateScoreElements(assignmentResults);
  scrollToSection(assignmentResultsSection);
}

candidateForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setStatus(candidateStatus, "Enregistrement en cours...");

  try {
    await saveRecord("/api/candidates", candidatePayload(candidateForm));
    candidateForm.reset();
    candidateForm.location_country.value = "France";
    candidateForm.location_remote_preference.value = "hybrid";
    candidateForm.availability_schedule.value = "full_time";
    setStatus(candidateStatus, "Candidat enregistré.");
    await loadCandidates();
  } catch (error) {
    setStatus(candidateStatus, `Erreur: ${error.message}`, true);
  }
});

jobForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setStatus(jobStatus, "Enregistrement en cours...");

  try {
    await saveRecord("/api/jobs", jobPayload(jobForm));
    jobForm.reset();
    jobForm.location_country.value = "France";
    jobForm.location_work_mode.value = "hybrid";
    jobForm.conditions_contract_type.value = "cdi";
    jobForm.conditions_capacity.value = "1";
    setStatus(jobStatus, "Poste enregistré.");
    await loadJobs();
  } catch (error) {
    setStatus(jobStatus, `Erreur: ${error.message}`, true);
  }
});

document.getElementById("refresh-candidates").addEventListener("click", () => {
  loadCandidates().catch((error) => setStatus(candidateStatus, `Erreur: ${error.message}`, true));
});

document.getElementById("refresh-jobs").addEventListener("click", () => {
  loadJobs().catch((error) => setStatus(jobStatus, `Erreur: ${error.message}`, true));
});

runCompatibilityButton.addEventListener("click", async () => {
  try {
    await runCompatibilityCalculation();
  } catch (error) {
    setStatus(compatibilityStatus, `Erreur: ${error.message}`, true);
  }
});

runAssignmentButton.addEventListener("click", async () => {
  setStatus(assignmentStatus, "Optimisation CP-SAT en cours...");

  try {
    const response = await saveRecord("/api/assignment", assignmentPayload());
    renderAssignmentResults(response);
    setStatus(assignmentStatus, "Affectation optimale calculée.");
  } catch (error) {
    latestAssignmentResponse = null;
    assignmentMeta.textContent = "";
    assignmentResults.innerHTML = "";
    setStatus(assignmentStatus, `Erreur: ${error.message}`, true);
  }
});

compatibilityResults.addEventListener("click", (event) => {
  const groupToggle = event.target.closest(".compatibility-group-toggle");
  if (groupToggle) {
    const group = groupToggle.closest(".compatibility-group");
    const details = group.querySelector(".compatibility-group-list");
    const isExpanded = groupToggle.getAttribute("aria-expanded") === "true";

    groupToggle.setAttribute("aria-expanded", String(!isExpanded));
    group.dataset.expanded = String(!isExpanded);
    details.hidden = isExpanded;

    const text = groupToggle.querySelector(".group-toggle-text");
    text.textContent = isExpanded ? "Voir les compatibilités" : "Masquer les compatibilités";
    return;
  }

  const toggle = event.target.closest(".compatibility-toggle");
  if (!toggle) {
    return;
  }

  const article = toggle.closest(".compatibility-item");
  const details = article.querySelector(".compatibility-details");
  const isExpanded = toggle.getAttribute("aria-expanded") === "true";

  toggle.setAttribute("aria-expanded", String(!isExpanded));
  article.dataset.expanded = String(!isExpanded);
  details.hidden = isExpanded;

  const text = toggle.querySelector(".toggle-text");
  text.textContent = isExpanded ? "Voir les explications" : "Masquer les explications";
});

function handleExpandableListClick(event, openText, closeText) {
  const toggle = event.target.closest(".expandable-toggle");
  if (!toggle) {
    return;
  }

  const article = toggle.closest(".expandable-item");
  const details = article.querySelector(".expandable-details");
  const isExpanded = toggle.getAttribute("aria-expanded") === "true";

  toggle.setAttribute("aria-expanded", String(!isExpanded));
  article.dataset.expanded = String(!isExpanded);
  details.hidden = isExpanded;

  const text = toggle.querySelector(".toggle-text");
  text.textContent = isExpanded ? openText : closeText;
}

candidateList.addEventListener("click", (event) => {
  handleExpandableListClick(event, "Voir le profil", "Masquer le profil");
});

jobList.addEventListener("click", (event) => {
  handleExpandableListClick(event, "Voir le poste", "Masquer le poste");
});

weightGroupInputs.forEach((input) => {
  input.addEventListener("input", () => {
    applySliderChangesLocally();
  });
});

resetCriterionWeightsButton.addEventListener("click", () => {
  resetCriterionWeights();
  if (hasComputedCompatibility) {
    applySliderChangesLocally();
    setStatus(compatibilityStatus, "Compatibilités remises à jour avec les sliders par défaut.");
  }
});

[compatibilityCandidateFilter, compatibilityJobFilter].forEach((input) => {
  input.addEventListener("change", scheduleLiveCompatibilityRefresh);
});

compatibilityTopK.addEventListener("input", scheduleLiveCompatibilityRefresh);

jumpToCompatibilityResultsButton.addEventListener("click", () => {
  scrollToSection(compatibilityResultsSection);
});

jumpToAssignmentResultsButton.addEventListener("click", () => {
  scrollToSection(assignmentResultsSection);
});

loadCandidates().catch(() => renderCandidateList([]));
loadJobs().catch(() => renderJobList([]));
attachFrenchValidation();
updateCriterionWeightSummary();
