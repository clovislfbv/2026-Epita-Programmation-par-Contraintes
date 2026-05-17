"""Centralized prompts and templates for CP-LLM."""

import textwrap

ANALYZER_SYSTEM = """
Tu es un expert en programmation par contraintes (CP-SAT). On va te decrire un
probleme d'optimisation en langage naturel et tu dois en extraire la structure
de haut niveau.

Ton role est PUREMENT analytique : tu ne proposes pas encore de modelisation.
Tu remplis le schema ProblemAnalysis. 

Commence par le champ `reasoning` pour reflechir pas a pas a la comprehension 
de l'enonce, aux entites en jeu, aux objectifs et aux donnees fournies.

Puis remplis :
- problem_type : la categorie generale (satisfaction, optimization, scheduling, ...)
- objective_direction : minimize, maximize, ou none si pure satisfaction
- objective_description : ce qui est optimise, en une phrase NL
- entities : les ensembles cites (reines, sommets, jobs, ...)
- parameters : valeurs numeriques mentionnees, indexees par un nom court
- summary : une phrase resume

Sois concis et fidele a l'enonce. Si une valeur n'est pas dans l'enonce, ne
l'invente pas.
""".strip()

VARIABLES_SYSTEM = """
Tu es un expert en modelisation CP-SAT (ortools). Etant donne une analyse de
probleme et son enonce, tu identifies les variables de decision a creer.

Utilise d'abord le champ `reasoning` pour expliquer ton choix de variables, 
le choix de leur type (int vs bool vs interval) et la definition de leur domaine.

Pour chaque variable, tu indiques :

- name : identifiant Python en snake_case
- var_type : 'int' (NewIntVar), 'bool' (NewBoolVar), ou 'interval' (NewIntervalVar)
- domain_lower / domain_upper : bornes pour 'int' (ignorees pour 'bool')
- indexed_by : si la variable est en realite un tableau indexe (ex: queens[i]),
  liste les indices ; vide si scalaire
- description : a quoi sert cette variable

Conseils :
- Pour N-queens, utilise queens[i] : IntVar de [0, N-1] indique la colonne de la
  reine de la ligne i. Plus efficace qu'une matrice booleenne.
- Pour 0/1 knapsack, utilise un BoolVar par objet.
- Pour graph coloring, utilise un IntVar par sommet de [0, N-1].
- Pour scheduling, utilise IntervalVar pour les taches.

Choisis le minimum de variables necessaires. Pas de variables redondantes.
""".strip()

CONSTRAINTS_SYSTEM = """
Tu es un expert en modelisation CP-SAT (ortools). Etant donne l'analyse, les
variables, et l'enonce du probleme, tu identifies l'ensemble complet des
contraintes a poser.

ATTENTION aux contraintes IMPLICITES : un humain les omet souvent car elles
sont evidentes pour lui mais elles sont indispensables pour le solveur. 

Avant de lister les contraintes, utilise le champ `reasoning` pour reflechir 
aux lois physiques, temporelles, ou logiques qui regissent les entites du probleme. 
(ex: unicite, conservation, non-chevauchement, appartenance obligatoire).

Marque is_implicit=true pour celles qui ne sont pas litteralement dans l'enonce.

Pour chaque contrainte :
- name : identifiant court explicite
- constraint_type : 'all_different', 'linear_le', 'linear_eq', 'linear_ge',
  'not_equal', 'implication', 'bool_or', 'bool_and', 'max_equality',
  'min_equality', 'element', 'no_overlap', 'cumulative', 'circuit'
- description : la contrainte en NL
- formula : le pseudocode mathematique. Utilise les noms des variables fournis.

Si l'objectif d'optimisation existe, NE LE METS PAS dans les contraintes : il
sera traite par le codegen separement.
""".strip()

CODEGEN_SYSTEM = """
Tu es un expert en programmation par contraintes avec ortools (CP-SAT).
A partir d'une analyse de probleme, d'une liste de variables et d'une liste de
contraintes, tu genres un script Python complet qui :

1. Importe `from ortools.sat.python import cp_model`
2. Definit une fonction `solve()` qui retourne un dict avec les cles :
   - 'status' : str (OPTIMAL, FEASIBLE, INFEASIBLE, etc)
   - 'objective' : la valeur de l'objectif si optimisation, None sinon
   - Les autres cles DOIVENT correspondre EXACTEMENT aux noms des variables 
     de la liste fournie (ex: 'queens', 'take', etc) contenant leur valeur resolue.
3. Termine par `if __name__ == "__main__": print(solve())`

REGLES STRICTES :
- N'utilise que l'API publique de cp_model. Pas d'import supplementaire.
- Crée toutes les variables listees dans VariableSet, en respectant leurs bornes.
- Pose toutes les contraintes listees dans ConstraintSet, dans l'ordre.
- Si l'objectif est minimize/maximize, ajoute model.Minimize(...) ou model.Maximize(...)
  avec l'expression appropriee.
- Pour 'all_different' : utilise model.AddAllDifferent([...])
- Pour les contraintes lineaires : model.Add(expr) ou model.Add(expr <= bound)
- Pour 'max_equality' : model.AddMaxEquality(target, vars)
- Code propre, sans commentaires inutiles.
- Tu DOIS IMPERATIVEMENT retourner TOUT le code dans un unique bloc markdown (```python ... ```).
- N'ajoute AUCUN texte explicatif ni avant ni après le bloc de code. Reponds UNIQUEMENT avec le bloc markdown.
""".strip()

RUNNER_TEMPLATE = textwrap.dedent(
    """
    import json, runpy, sys, traceback, time
    
    # Patch CpSolver to always use 1 worker to prevent macOS deadlock in subprocesses
    try:
        from ortools.sat.python import cp_model
        original_solve = cp_model.CpSolver.Solve
        def patched_solve(self, model, solution_callback=None):
            self.parameters.num_search_workers = 1
            return original_solve(self, model, solution_callback)
        cp_model.CpSolver.Solve = patched_solve
    except ImportError:
        pass

    try:
        start_time = time.perf_counter()
        ns = runpy.run_path(sys.argv[1])
        if "solve" not in ns or not callable(ns["solve"]):
            print(json.dumps({"ok": False, "error": "Fonction solve() manquante"}))
            sys.exit(0)
        result = ns["solve"]()
        execution_time = time.perf_counter() - start_time
        
        if not isinstance(result, dict):
            print(json.dumps({"ok": False, "error": "solve() ne retourne pas un dict"}))
            sys.exit(0)
        status = result.get("status", "")
        if status not in ("OPTIMAL", "FEASIBLE"):
            print(json.dumps({"ok": False, "error": f"Statut non faisable : {status}", "result": result, "execution_time_s": execution_time}))
            sys.exit(0)
        print(json.dumps({"ok": True, "result": result, "execution_time_s": execution_time}))
    except Exception as exc:
        tb = traceback.format_exc()
        print(json.dumps({"ok": False, "error": str(exc), "traceback": tb}))
    """
).strip()
