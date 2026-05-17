import { useEffect, useMemo, useState } from "react";
import {
  BookOpen,
  CalendarDays,
  Calculator,
  Filter,
  RefreshCcw,
  Search,
  ShoppingCart,
  Shuffle,
  ThumbsDown,
  Utensils,
} from "lucide-react";

const DEFAULT_PREFERENCES = {
  likes: [],
  dislikes: [],
  like_weight: 1.5,
  dislike_weight: 1.5,
  tag_bonus: {},
  tag_penalty: {},
};

const SOLVER_OPTIONS = [
  { value: "cpsat", label: "CP-SAT (OR-Tools)" },
  { value: "lp", label: "PLNE (SCIP)" },
];

const DATASET_OPTIONS = [
  { value: "plats.json", label: "Base Spoonacular" },
  { value: "usda_base_dishes.json", label: "Base USDA" },
];

const SEASONS = [
  { value: "spring", label: "Printemps" },
  { value: "summer", label: "Ete" },
  { value: "autumn", label: "Automne" },
  { value: "winter", label: "Hiver" },
];

const MEAL_LABELS = {
  breakfast: "Petit dej",
  lunch: "Dejeuner",
  dinner: "Diner",
};

const MAIN_NUTRIENTS = [
  { key: "calories", label: "Calories" },
  { key: "protein_g", label: "Proteines" },
  { key: "carbs_g", label: "Glucides" },
  { key: "fat_g", label: "Lipides" },
];

const formatMoney = (value) => {
  if (typeof value !== "number" || Number.isNaN(value)) return "n/a";
  return `${value.toFixed(2)} EUR`;
};

const formatMs = (value) => {
  if (typeof value !== "number" || Number.isNaN(value)) return "n/a";
  return value >= 1000
    ? `${(value / 1000).toFixed(2)} s`
    : `${value.toFixed(2)} ms`;
};

const normalizeDishes = (data) => (Array.isArray(data) ? data : []);

const API_URL = import.meta.env.VITE_API_URL;

function App() {
  const [dishes, setDishes] = useState([]);
  const [bounds, setBounds] = useState(null);
  const [dislikedIds, setDislikedIds] = useState([]);
  const [dataset, setDataset] = useState("plats.json");
  const [solver, setSolver] = useState("cpsat");
  const [season, setSeason] = useState("spring");
  const [budget, setBudget] = useState("75");
  const [search, setSearch] = useState("");
  const [mealFilter, setMealFilter] = useState("all");
  const [plan, setPlan] = useState(null);
  const [benchmark, setBenchmark] = useState(null);
  const [activeTab, setActiveTab] = useState("articles");
  const [loadingData, setLoadingData] = useState(true);
  const [loadingPlan, setLoadingPlan] = useState(false);
  const [loadingBenchmark, setLoadingBenchmark] = useState(false);
  const [error, setError] = useState("");
  const API_URL = import.meta.env.VITE_API_URL;
  useEffect(() => {
    let isMounted = true;

    const loadData = async () => {
      setLoadingData(true);
      setError("");
      try {
        const [dishesRes, boundsRes] = await Promise.all([
          fetch(`/data/${dataset}`),
          fetch(`/data/nutrition_bounds.json`),
        ]);

        if (!dishesRes.ok || !boundsRes.ok) {
          throw new Error("Data fetch failed");
        }

        const dishesData = normalizeDishes(await dishesRes.json());
        const boundsData = await boundsRes.json();

        if (isMounted) {
          setDishes(dishesData);
          setBounds(boundsData);
          setDislikedIds([]);
          setPlan(null);
          setBenchmark(null);
        }
      } catch (loadError) {
        if (isMounted) {
          setError(
            "Impossible de charger les donnees. Lance le serveur Python.",
          );
        }
      } finally {
        if (isMounted) setLoadingData(false);
      }
    };

    loadData();

    return () => {
      isMounted = false;
    };
  }, [dataset]);

  const dislikedSet = useMemo(() => new Set(dislikedIds), [dislikedIds]);

  const filteredDishes = useMemo(() => {
    const term = search.trim().toLowerCase();
    return dishes.filter((dish) => {
      if (mealFilter !== "all" && dish.meal !== mealFilter) return false;
      if (!term) return true;
      const haystack = [dish.name, dish.id, dish.meal, ...(dish.tags || [])]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(term);
    });
  }, [dishes, search, mealFilter]);

  const dislikedNames = useMemo(() => {
    if (!dislikedIds.length) return [];
    const dishMap = new Map(dishes.map((dish) => [dish.id, dish]));
    return dislikedIds
      .map((id) => dishMap.get(id))
      .filter(Boolean)
      .map((dish) => dish.name || dish.id);
  }, [dishes, dislikedIds]);

  const hasPlanDays = (plan?.days?.length ?? 0) > 0;

  const handleToggleDislike = (id) => {
    setDislikedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  };

  const buildSolvePayload = () => ({
    dishes,
    bounds,
    season,
    budget: budget === "" ? null : Number(budget),
    preferences: {
      ...DEFAULT_PREFERENCES,
      likes: dishes
        .filter((dish) => !dislikedIds.includes(dish.id))
        .map((dish) => dish.id),
      dislikes: dislikedIds,
    },
    days: 7,
  });

  const handleSolve = async () => {
    if (!bounds || !dishes.length) {
      setError("Pas de donnees suffisantes pour resoudre.");
      return;
    }

    if (budget < 75) {
      setError("Le budget doit etre d'au moins 75 EUR pour un plan hebdo.");
      return;
    }

    setLoadingPlan(true);
    setError("");
    setBenchmark(null);

    try {
      const payload = {
        ...buildSolvePayload(),
        solver,
      };

      const response = await fetch(`${API_URL}/api/solve_weekly`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error("Solve failed");
      }

      const result = await response.json();
      setPlan(result);
    } catch (solveError) {
      setError("La resolution a echoue. Verifie le serveur Python.");
    } finally {
      setLoadingPlan(false);
    }
  };

  const handleBenchmark = async () => {
    if (!bounds || !dishes.length) {
      setError("Pas de donnees suffisantes pour comparer.");
      return;
    }

    setLoadingBenchmark(true);
    setError("");

    try {
      const response = await fetch(`${API_URL}/api/benchmark_weekly`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildSolvePayload()),
      });

      if (!response.ok) {
        throw new Error("Benchmark failed");
      }

      const result = await response.json();
      setBenchmark(result);
    } catch (benchmarkError) {
      setError("Le benchmark a echoue. Verifie le serveur Python.");
    } finally {
      setLoadingBenchmark(false);
    }
  };

  return (
    <div className="app">
      <header className="hero">
        <div className="hero-copy animate-in" style={{ "--delay": "0.05s" }}>
          <p className="kicker">Diet Problem - planification nutritionnelle</p>
          <h1>Un plan hebdo de 7 jours, adapte a tes choix.</h1>
          <p className="lead">
            L interface web pilote le solveur CP-SAT ou PLNE, integre les
            dislikes, et presente un plan different a chaque validation.
          </p>
          <div className="hero-actions">
            <button className="button" onClick={handleSolve}>
              <Calculator size={16} />
              Lancer la resolution
            </button>
            <a
              className="button ghost"
              href="#flow"
              onClick={() => setActiveTab("articles")}
            >
              <ThumbsDown size={16} />
              Gerer les dislikes
            </a>
          </div>
        </div>
        <div className="hero-panel animate-in" style={{ "--delay": "0.12s" }}>
          <div className="hero-stat">
            <span className="stat-label">Articles charges</span>
            <span className="stat-value">{dishes.length || "-"}</span>
          </div>
          <div className="hero-stat">
            <span className="stat-label">Source articles</span>
            <span className="stat-value small">
              {DATASET_OPTIONS.find((opt) => opt.value === dataset)?.label}
            </span>
          </div>
          <div className="hero-stat">
            <span className="stat-label">Limites nutritionnelles</span>
            <span className="stat-value">
              {bounds ? Object.keys(bounds).length : "-"}
            </span>
          </div>
          <div className="hero-stat">
            <span className="stat-label">Dislikes actifs</span>
            <span className="stat-value">{dislikedIds.length}</span>
          </div>
          <div className="hero-note">
            <CalendarDays size={16} />
            <span>Plan sur 7 jours, 3 repas par jour.</span>
          </div>
        </div>
      </header>

      <section className="section" id="tuto">
        <div className="section-header">
          <div className="section-title">
            <BookOpen size={18} />
            <h2>Tuto express</h2>
          </div>
          <p>
            Ce guide resume le flux de travail du projet et ce que fait l app.
          </p>
        </div>
        <div className="tuto-grid">
          {[
            {
              title: "Charger les donnees",
              desc: "On recupere les plats, les saisons, les couts et les apports nutritionnels OMS/ANSES recommandés.",
            },
            {
              title: "Definir les dislikes",
              desc: "Tu marques les articles que tu ne veux pas favoriser. Par défaut le solveur penalise les articles en dislike de 1.5 points",
            },
            {
              title: "Choisir le solveur",
              desc: "CP-SAT ou PLNE, avec ton budget minimum de 75 EUR, puis on lance la resolution.",
            },
            {
              title: "Comparer les plans",
              desc: "Tu peux aussi lancer un benchmark pour comparer les resultats et temps de calcul des deux solveurs sur ta configuration.",
            },
          ].map((step, index) => (
            <article
              key={step.title}
              className="card animate-in"
              style={{ "--delay": `${0.08 + index * 0.06}s` }}
            >
              <h3>{step.title}</h3>
              <p>{step.desc}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section" id="flow">
        <div className="tab-bar">
          <button
            className={`tab ${activeTab === "articles" ? "active" : ""}`}
            onClick={() => setActiveTab("articles")}
            type="button"
          >
            Articles & dislikes
          </button>
          <button
            className={`tab ${activeTab === "panier" ? "active" : ""}`}
            onClick={() => setActiveTab("panier")}
            type="button"
          >
            Valider le panier
          </button>
        </div>

        <div className="tab-panel">
          {activeTab === "articles" && (
            <div className="tab-content">
              <div className="section-header">
                <div className="section-title">
                  <ThumbsDown size={18} />
                  <h2>Articles et dislikes</h2>
                </div>
                <p>
                  Filtre les plats par repas, puis ajoute un dislike si un
                  article ne te plait pas.
                </p>
              </div>

              <div className="toolbar">
                <div className="input-group">
                  <Search size={16} />
                  <input
                    type="search"
                    placeholder="Rechercher un article"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                  />
                </div>
                <div className="select-group">
                  <Filter size={16} />
                  <select
                    value={mealFilter}
                    onChange={(event) => setMealFilter(event.target.value)}
                  >
                    <option value="all">Tous les repas</option>
                    <option value="breakfast">Petit dej</option>
                    <option value="lunch">Dejeuner</option>
                    <option value="dinner">Diner</option>
                  </select>
                </div>
                <div className="select-group">
                  <Utensils size={16} />
                  <select
                    value={dataset}
                    onChange={(event) => setDataset(event.target.value)}
                  >
                    {DATASET_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="toolbar-meta">
                  {filteredDishes.length} articles
                </div>
              </div>

              {loadingData ? (
                <div className="empty">Chargement des articles...</div>
              ) : (
                <div className="articles-grid">
                  {filteredDishes.map((dish, index) => {
                    const isDisliked = dislikedSet.has(dish.id);
                    return (
                      <article
                        key={dish.id}
                        className={`article-card animate-in ${isDisliked ? "is-disliked" : ""}`}
                        style={{ "--delay": `${0.02 + (index % 12) * 0.02}s` }}
                      >
                        <header>
                          <div>
                            <h3>{dish.name || dish.id}</h3>
                            <p className="muted">
                              {MEAL_LABELS[dish.meal] || dish.meal} -{" "}
                              {formatMoney(dish.cost || 0)}
                            </p>
                          </div>
                          {isDisliked && <span className="badge">Dislike</span>}
                        </header>
                        <div className="chip-row">
                          {(dish.tags || []).map((tag) => (
                            <span key={tag} className="chip">
                              {tag}
                            </span>
                          ))}
                        </div>
                        <div className="chip-row secondary">
                          {(dish.seasons || []).map((seasonValue) => (
                            <span key={seasonValue} className="chip ghost">
                              {seasonValue}
                            </span>
                          ))}
                        </div>
                        <button
                          className={`button ghost ${isDisliked ? "active" : ""}`}
                          onClick={() => handleToggleDislike(dish.id)}
                          aria-pressed={isDisliked}
                        >
                          <ThumbsDown size={16} />
                          {isDisliked ? "Retirer" : "Dislike"}
                        </button>
                      </article>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {activeTab === "panier" && (
            <div className="tab-content">
              <div className="section-header">
                <div className="section-title">
                  <ShoppingCart size={18} />
                  <h2>Valider le panier</h2>
                </div>
                <p>
                  Choisis le mode de resolution, la saison et le budget, puis
                  lance la generation du plan nutritionnel.
                </p>
              </div>

              <div className="panier-grid">
                <div
                  className="card animate-in"
                  style={{ "--delay": "0.08s", height: "fit-content" }}
                >
                  <h3>Configuration</h3>
                  <div className="form-grid">
                    <label>
                      Type d articles
                      <select
                        value={dataset}
                        onChange={(event) => setDataset(event.target.value)}
                      >
                        {DATASET_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Mode de resolution
                      <select
                        value={solver}
                        onChange={(event) => setSolver(event.target.value)}
                      >
                        {SOLVER_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Saison
                      <select
                        value={season}
                        onChange={(event) => setSeason(event.target.value)}
                      >
                        {SEASONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Budget hebdo (EUR)
                      <input
                        type="number"
                        min="75"
                        step="1"
                        value={budget}
                        onChange={(event) => setBudget(event.target.value)}
                      />
                    </label>
                  </div>
                  <div className="panier-actions">
                    <button
                      className="button"
                      onClick={handleSolve}
                      disabled={loadingPlan || loadingBenchmark}
                    >
                      <Calculator size={16} />
                      {loadingPlan ? "Calcul en cours" : "Valider le panier"}
                    </button>
                    <button
                      className="button benchmark"
                      onClick={handleBenchmark}
                      disabled={loadingPlan || loadingBenchmark}
                      type="button"
                    >
                      <Calculator size={16} />
                      {loadingBenchmark ? "Benchmark en cours" : "Benchmark"}
                    </button>
                    <button
                      className="button ghost"
                      onClick={() => {
                        setPlan(null);
                        setBenchmark(null);
                      }}
                      type="button"
                    >
                      <RefreshCcw size={16} />
                      Effacer le plan
                    </button>
                  </div>
                  <div className="panier-meta">
                    <div>
                      <span className="muted">Dislikes actifs</span>
                      <strong>{dislikedIds.length}</strong>
                    </div>
                    <div>
                      <span className="muted">Mode</span>
                      <strong>
                        {
                          SOLVER_OPTIONS.find((opt) => opt.value === solver)
                            ?.label
                        }
                      </strong>
                    </div>
                    <div>
                      <span className="muted">Articles</span>
                      <strong>
                        {
                          DATASET_OPTIONS.find((opt) => opt.value === dataset)
                            ?.label
                        }
                      </strong>
                    </div>
                  </div>
                  {!!dislikedNames.length && (
                    <div className="panier-list">
                      <p className="muted">Articles en dislike :</p>
                      <div className="chip-row">
                        {dislikedNames.slice(0, 6).map((name) => (
                          <span key={name} className="chip">
                            {name}
                          </span>
                        ))}
                        {dislikedNames.length > 6 && (
                          <span className="chip ghost">
                            +{dislikedNames.length - 6}
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                <div className="card animate-in" style={{ "--delay": "0.14s" }}>
                  <div className="plan-header">
                    <div>
                      <h3>Plan nutritionnel sur 7 jours</h3>
                      <p className="muted">
                        Resultats en sortie du solveur avec les preferences
                        appliquees.
                      </p>
                    </div>
                    <div className="plan-icons">
                      <Shuffle size={16} />
                      <CalendarDays size={16} />
                    </div>
                  </div>

                  {error && <div className="empty error">{error}</div>}

                  {!plan && !benchmark && !error && (
                    <div className="empty">
                      Aucun plan calcule. Clique sur "Valider le panier".
                    </div>
                  )}

                  {plan && (
                    <div className="plan-body">
                      <div className="plan-meta-grid">
                        <div className="meta-card">
                          <span className="muted">Statut</span>
                          <strong>{plan.status || "-"}</strong>
                        </div>
                        <div className="meta-card">
                          <span className="muted">Solver</span>
                          <strong>{plan.solver || solver}</strong>
                        </div>
                        <div className="meta-card">
                          <span className="muted">Cout total</span>
                          <strong>{formatMoney(plan.weekly_cost)}</strong>
                        </div>
                      </div>

                      {!hasPlanDays && (
                        <div className="empty">
                          Aucun plan exploitable trouve pour cette
                          configuration. Essaie un budget plus large, une saison
                          differente ou des bornes nutritionnelles moins
                          strictes.
                        </div>
                      )}

                      {hasPlanDays && (
                        <>
                          <div className="nutrient-row">
                            {MAIN_NUTRIENTS.map((nutrient) => (
                              <div key={nutrient.key} className="nutrient-card">
                                <span className="muted">{nutrient.label}</span>
                                <strong>
                                  {plan.weekly_totals?.[nutrient.key] ?? "-"}
                                </strong>
                              </div>
                            ))}
                          </div>

                          <div className="plan-grid">
                            {(plan.days || []).map((day) => (
                              <article key={day.day} className="plan-card">
                                <header>
                                  <h4>Jour {day.day}</h4>
                                  <span className="muted">
                                    {formatMoney(day.cost)}
                                  </span>
                                </header>
                                <div className="meal-grid">
                                  {Object.entries(day.meals || {}).map(
                                    ([mealKey, meal]) => (
                                      <div key={mealKey} className="meal-card">
                                        <span className="muted">
                                          {MEAL_LABELS[mealKey] || mealKey}
                                        </span>
                                        <strong>{meal.name || meal.id}</strong>
                                        <span className="muted">
                                          {formatMoney(meal.cost)}
                                        </span>
                                      </div>
                                    ),
                                  )}
                                </div>
                                <div className="totals-row">
                                  {MAIN_NUTRIENTS.map((nutrient) => (
                                    <span key={nutrient.key}>
                                      {nutrient.label}:{" "}
                                      {day.totals?.[nutrient.key] ?? "-"}
                                    </span>
                                  ))}
                                </div>
                              </article>
                            ))}
                          </div>
                        </>
                      )}
                    </div>
                  )}

                  {benchmark && (
                    <div className="benchmark-body">
                      <h4>Benchmark CP-SAT vs PLNE</h4>
                      <div className="benchmark-grid">
                        {["cpsat", "lp"].map((solverName) => {
                          const solverResult = benchmark.solvers?.[solverName];
                          return (
                            <div key={solverName} className="benchmark-card">
                              <span className="muted">
                                {SOLVER_OPTIONS.find(
                                  (opt) => opt.value === solverName,
                                )?.label || solverName}
                              </span>
                              <strong>{solverResult?.status || "-"}</strong>
                              <span>
                                Temps : {formatMs(solverResult?.elapsed_ms)}
                              </span>
                              <span>
                                Cout : {formatMoney(solverResult?.weekly_cost)}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      <footer className="footer">
        <div className="footer-card">
          <span className="muted">Diet Planner - CP-SAT et PLNE</span>
          <span className="muted">Interface web Vite + React</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
