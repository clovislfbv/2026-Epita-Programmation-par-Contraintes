import streamlit as st
import json
import pandas as pd
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import ast

from cp_llm.cache import CachedLLMClient
from cp_llm.llm_client import MistralClient
from cp_llm.runner import run_pipeline
from cp_llm import prompts as cp_prompts
from cp_llm import visualizers
from scripts.run_benchmark import load_reference

CACHE_DIR = ROOT / ".cache" / "llm"


def _extract_solve_and_main(source: str) -> str:
    """Garde uniquement `def solve(...)` et le bloc `if __name__ == "__main__":`.
    Drop imports, docstrings, constantes module-level, etc.
    """
    if not source:
        return source
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source
    keep = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "solve":
            keep.append(node)
        elif isinstance(node, ast.If):
            t = node.test
            if (
                isinstance(t, ast.Compare)
                and isinstance(t.left, ast.Name)
                and t.left.id == "__name__"
                and t.ops
                and isinstance(t.ops[0], ast.Eq)
                and t.comparators
                and isinstance(t.comparators[0], ast.Constant)
                and t.comparators[0].value == "__main__"
            ):
                keep.append(node)
    if not keep:
        return source
    return "\n\n".join(ast.unparse(n) for n in keep)


# Patch CpSolver globally for this process (essential for macOS stability)
try:
    from ortools.sat.python import cp_model

    _original_solve = cp_model.CpSolver.Solve

    def _patched_solve(self, model, solution_callback=None):
        self.parameters.num_search_workers = 1
        return _original_solve(self, model, solution_callback)

    cp_model.CpSolver.Solve = _patched_solve
except ImportError:
    pass

st.set_page_config(page_title="CP-LLM Demo", layout="wide")

st.title("🧩 Modélisation CP Assistée par LLM")

tab1, tab2, tab3 = st.tabs(
    [
        "🚀 Live Run & Repair",
        "📊 Benchmark Dashboard",
        "📜 Prompts templates",
    ]
)

with tab1:
    st.header("Live Pipeline Execution")
    problems_dir = ROOT / "benchmark" / "problems"
    problems = (
        [p.stem for p in problems_dir.glob("*.txt")] if problems_dir.exists() else []
    )

    if not problems:
        st.warning("Aucun problème trouvé dans benchmark/problems/")
    else:
        selected_problem = st.selectbox("Sélectionnez un problème :", sorted(problems))

        if st.button("Lancer le pipeline"):
            try:
                from dotenv import load_dotenv

                load_dotenv(ROOT / ".env")
            except ImportError:
                pass

            client = CachedLLMClient(MistralClient(), CACHE_DIR)
            problem_path = problems_dir / f"{selected_problem}.txt"
            st.info(f"Enoncé : {problem_path.read_text()}")

            with st.spinner("Exécution du pipeline (LLM + Vérification)..."):
                result = run_pipeline(client, problem_path)

            # Load reference for comparison
            with st.spinner("Exécution de la référence..."):
                reference, ref_exec_time = load_reference(selected_problem)

            if result.error_stage:
                st.error(f"Échec à l'étape : {result.error_stage}")
                st.code(result.error_message, language="text")
            else:
                st.success("Génération et vérification réussies !")

            # --- Reasoning Display ---
            st.subheader("🧠 Étapes de réflexion de l'LLM")

            with st.expander("1. Analyse du problème", expanded=False):
                st.write("**Raisonnement :**")
                st.write(result.analysis.reasoning)
                st.write("**Résumé :**", result.analysis.summary)
                st.write("**Paramètres extraits :**", result.analysis.parameters)

            with st.expander("2. Identification des variables", expanded=False):
                st.write("**Raisonnement :**")
                st.write(result.variables.reasoning)
                col_v1, col_v2 = st.columns(2)
                for i, v in enumerate(result.variables.variables):
                    with col_v1 if i % 2 == 0 else col_v2:
                        st.markdown(f"- `{v.name}` ({v.var_type}): {v.description}")

            with st.expander("3. Extraction des contraintes", expanded=False):
                st.write("**Raisonnement :**")
                st.write(result.constraints.reasoning)
                for c in result.constraints.constraints:
                    st.markdown(
                        f"- **{c.name}** : `{c.formula}` ({'Implicite' if c.is_implicit else 'Explicite'})"
                    )

            # --- Solution visualisee (unique : LLM si dispo, sinon reference) ---
            st.subheader("🎯 Solution")
            solver_result = result.verification.get("result")
            ref_solver_result = reference if isinstance(reference, dict) else None

            viz_source = None
            viz_label = None
            if solver_result:
                viz_source = solver_result
                viz_label = "Solution trouvée par le code LLM"
            elif ref_solver_result:
                viz_source = ref_solver_result
                viz_label = "Solution de la référence (pipeline LLM en échec)"

            if viz_source is not None:
                fig = visualizers.render(selected_problem, viz_source)
                if fig is not None:
                    left, mid, right = st.columns([1, 2, 1])
                    with mid:
                        st.caption(viz_label)
                        st.pyplot(fig, use_container_width=True)
                else:
                    st.info(f"{viz_label} — visualiseur indisponible pour ce format.")
                    st.json(viz_source, expanded=False)
            else:
                st.warning(
                    "Aucune solution disponible (pipeline en échec, pas de référence)."
                )

            # --- Code comparaison (solve + main uniquement) ---
            st.subheader("💻 Code — LLM vs Référence")
            ref_path = ROOT / "benchmark" / "references" / f"{selected_problem}.py"
            ref_full = (
                ref_path.read_text(encoding="utf-8") if ref_path.exists() else None
            )
            llm_code = _extract_solve_and_main(result.generated_code or "")
            ref_code = _extract_solve_and_main(ref_full or "")
            code_col_llm, code_col_ref = st.columns(2)
            with code_col_llm:
                st.caption(
                    f"LLM — {len(llm_code.splitlines()) if llm_code else 0} lignes"
                )
                st.code(llm_code or "(non genere)", language="python")
            with code_col_ref:
                st.caption(
                    f"Référence manuelle — {len(ref_code.splitlines()) if ref_code else 0} lignes"
                )
                st.code(ref_code or "(reference absente)", language="python")

            # --- Historique des tentatives codegen ---
            attempts = getattr(result, "codegen_attempts", None) or []
            if len(attempts) > 1 or (attempts and not attempts[0].ok):
                n_failed = sum(1 for a in attempts if not a.ok)
                final_ok = attempts[-1].ok if attempts else False
                badge = "✅ réparé" if final_ok else "❌ échec final"
                st.subheader(
                    f"🔁 Historique codegen — {len(attempts)} tentative(s), {n_failed} échec(s), {badge}"
                )
                for a in attempts:
                    icon = "✅" if a.ok else "❌"
                    label = f"{icon} Tentative {a.attempt_number}" + (
                        "" if a.ok else f" — {(a.error or '')[:120]}"
                    )
                    with st.expander(label, expanded=False):
                        if a.error and not a.ok:
                            st.error(a.error)
                        st.code(
                            _extract_solve_and_main(a.code) or a.code, language="python"
                        )

            # --- Performance & details ---
            st.subheader("⏱️ Performance")
            perf_cols = st.columns(3)
            exec_time = result.execution_time_s
            with perf_cols[0]:
                st.metric(
                    "LLM Generated",
                    f"{exec_time:.4f} s" if exec_time is not None else "N/A",
                )
            with perf_cols[1]:
                st.metric(
                    "Référence",
                    f"{ref_exec_time:.4f} s" if ref_exec_time is not None else "N/A",
                )
            with perf_cols[2]:
                if exec_time is not None and ref_exec_time is not None:
                    diff = exec_time - ref_exec_time
                    st.metric("Δ (LLM − Réf)", f"{diff:+.4f} s")
                else:
                    st.metric("Δ", "N/A")

            if solver_result:
                with st.expander("Résultat brut du solveur (JSON)", expanded=False):
                    st.json(solver_result)

with tab2:
    st.header("Benchmark Comparison")
    report_path = ROOT / "benchmark_report.json"
    if report_path.exists():
        data = json.loads(report_path.read_text())
        df = pd.DataFrame(data)

        cols_to_show = [
            "problem",
            "ok",
            "error_stage",
            "n_codegen_attempts",
            "n_codegen_failures",
            "execution_time_s",
            "reference_execution_time_s",
            "execution_time_diff_s",
        ]
        cols_to_show = [c for c in cols_to_show if c in df.columns]

        st.dataframe(df[cols_to_show])

        if "execution_time_s" in df.columns:
            st.subheader("Temps d'exécution (Generated vs Reference)")
            chart_data = df[df["ok"]].set_index("problem")[
                ["execution_time_s", "reference_execution_time_s"]
            ]
            st.bar_chart(chart_data)
        else:
            st.info(
                "Lancez `python scripts/run_benchmark.py` pour générer les temps d'exécution."
            )
    else:
        st.warning("Veuillez lancer `run_benchmark.py` pour générer le rapport JSON.")

with tab3:
    st.header("Prompts templates envoyés au modèle")
    st.markdown(
        "Le pipeline est en **4 étages**. Chaque étage envoie à Mistral un "
        "*system prompt* fixe (ci-dessous) et un *user prompt* qui contient "
        "l'enoncé + les sorties des étages precedents."
    )
    stages = [
        ("1️⃣ Analyzer — analyse de haut niveau", cp_prompts.ANALYZER_SYSTEM),
        (
            "2️⃣ Variables — extraction des variables de décision",
            cp_prompts.VARIABLES_SYSTEM,
        ),
        ("3️⃣ Constraints — extraction des contraintes", cp_prompts.CONSTRAINTS_SYSTEM),
        ("4️⃣ Codegen — génération du code ortools", cp_prompts.CODEGEN_SYSTEM),
    ]
    for label, prompt in stages:
        with st.expander(label, expanded=False):
            st.code(prompt, language="markdown")

    st.divider()
    st.subheader("🔧 Prompt de retry (codegen)")
    st.markdown(
        "Quand le code généré échoue à la vérification, le runner reformule un "
        "prompt incluant l'erreur et le code précédent, puis redemande au LLM "
        "(jusqu'à 3 tentatives par défaut) :"
    )
    st.code(
        "Le code precedent a echoue avec l'erreur suivante :\n"
        "{error_message}\n\n"
        "Voici le code precedent :\n"
        "```python\n{previous_code}\n```\n\n"
        "Corrige le code et renvoie TOUT le code dans un unique bloc markdown\n"
        "(```python ... ```). N'ajoute aucun texte explicatif.",
        language="markdown",
    )
    st.caption(
        "System prompt associé : *Tu es un expert ortools qui corrige du code Python.*"
    )
