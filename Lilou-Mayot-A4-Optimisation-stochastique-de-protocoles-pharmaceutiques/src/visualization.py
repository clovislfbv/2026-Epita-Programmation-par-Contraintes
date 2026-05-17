"""
visualization.py
================
Tracés des protocoles de traitement et analyses comparatives.

Fonctions
---------
plot_pk_catalog
    Profils PK des médicaments du catalogue.
plot_protocol
    Profil de concentration et calendrier d'un protocole donné.
plot_profiles_comparison
    Superposition des profils PK pour les trois approches.
plot_scenario_violins
    Violin plots de la distribution des métriques sur scénarios.
plot_comparison_bars
    Barres comparatives E[Obj], pire cas et Std entre approches.
plot_pareto
    Nuage de points Efficacité vs Toxicité (front de Pareto empirique).
plot_lambda_sensitivity
    Impact du paramètre λ sur le trade-off Efficacité / Toxicité.
plot_population_results
    Comparaison des approches sur une cohorte de patients.
"""

from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from typing import Dict, List, Optional, Tuple

from .models import PKParameters, Patient, OptResult
from .pharmacokinetics import pk_multi


# ── Palette ───────────────────────────────────────────────────────────────────

COLORS = {
    "det": "#2563EB",
    "sto": "#16A34A",
    "rob": "#DC2626",
    "teal": "#0D9488",
    "orange": "#F97316",
}
LABELS = {"det": "Déterministe", "sto": "Stochastique (SAA)", "rob": "Robuste (minimax)"}


def _apply_style(ax: plt.Axes) -> None:
    """Style minimal : pas de cadre haut/droite, grille légère."""
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(True, alpha=0.3)


# ─────────────────────────────────────────────────────────────────────────────

def plot_pk_catalog(
    drugs: Dict[str, PKParameters],
    dose_per_m2: float = 75.0,
    bsa: float = 1.73,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Trace les profils PK des médicaments du catalogue (dose unique).

    Parameters
    ----------
    drugs : dict[str, PKParameters]
        Catalogue de médicaments.
    dose_per_m2 : float, optional
        Dose de référence (mg/m²). Défaut : 75.
    bsa : float, optional
        Surface corporelle de référence (m²). Défaut : 1.73.
    save_path : str, optional
        Chemin de sauvegarde de la figure (PNG). Si None, non sauvegardée.

    Returns
    -------
    plt.Figure
    """
    colors = ["#2563EB", "#16A34A", "#DC2626", "#D97706"]
    fig, axes = plt.subplots(2, 2, figsize=(13, 7))
    fig.suptitle("Profils pharmacocinétiques — Catalogue de médicaments",
                 fontsize=14, fontweight="bold")

    for ax, (name, pk), col in zip(axes.flat, drugs.items(), colors):
        T_h  = pk.t_half * 6
        t    = np.linspace(0, T_h, 1000)
        dose = dose_per_m2 * bsa
        c    = (dose / pk.vd) * np.exp(-pk.ke * t)

        ax.fill_between(t, c, alpha=0.15, color=col)
        ax.plot(t, c, color=col, lw=2.5)
        ax.axhspan(pk.cmin_eff, pk.cmax_safe, alpha=0.10, color="green",
                   label="Fenêtre thérapeutique")
        ax.axhline(pk.cmax_safe, color="red",   ls="--", lw=1.5)
        ax.axhline(pk.cmin_eff,  color="green", ls="--", lw=1.5)

        c_half = (dose / pk.vd) * np.exp(-pk.ke * pk.t_half)
        ax.annotate(
            f"t½={pk.t_half:.1f}h",
            xy=(pk.t_half, c_half),
            xytext=(pk.t_half + T_h * 0.06, c_half * 1.3),
            fontsize=9, color=col,
            arrowprops=dict(arrowstyle="->", color=col, lw=1.2),
        )
        ax.set_title(pk.name, fontsize=12, fontweight="bold", color=col)
        ax.set_xlabel("Temps (h)")
        ax.set_ylabel("Concentration (mg/L)")
        ax.legend(fontsize=8)
        _apply_style(ax)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=130, bbox_inches="tight")
    return fig


def plot_protocol(
    result: OptResult,
    pk_adj: PKParameters,
    horizon_days: int = 28,
    title_suffix: str = "",
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Trace le profil de concentration et le calendrier d'administration.

    Parameters
    ----------
    result : OptResult
        Protocole à visualiser.
    pk_adj : PKParameters
        Paramètres PK ajustés au patient.
    horizon_days : int, optional
        Horizon d'affichage (jours). Défaut : 28.
    title_suffix : str, optional
        Texte ajouté au titre (ex. identifiant patient).
    save_path : str, optional
        Chemin de sauvegarde (PNG).

    Returns
    -------
    plt.Figure
    """
    col   = COLORS.get(result.model, "#333")
    label = LABELS.get(result.model, result.model)
    t_ev  = np.linspace(0, horizon_days * 24, 5000)
    c     = pk_multi(result.doses, [d * 24 for d in result.times_days], pk_adj, t_ev) if result.doses else np.zeros_like(t_ev)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), height_ratios=[3, 1])

    ax1.fill_between(t_ev / 24, c, alpha=0.18, color=col)
    ax1.plot(t_ev / 24, c, color=col, lw=2.5)
    ax1.axhspan(pk_adj.cmin_eff, pk_adj.cmax_safe, alpha=0.10, color="green")
    ax1.axhline(pk_adj.cmax_safe, color="red",   ls="--", lw=1.5,
                label=f"Cmax_safe={pk_adj.cmax_safe:.4f}")
    ax1.axhline(pk_adj.cmin_eff,  color="green", ls="--", lw=1.5,
                label=f"Cmin_eff={pk_adj.cmin_eff:.5f}")

    for dose, day in zip(result.doses, result.times_days):
        ax1.axvline(day, color=col, ls=":", alpha=0.4)
        ax1.annotate(
            f"{dose:.0f}mg\nJ{day}",
            xy=(day, pk_adj.cmax_safe * 0.05),
            ha="center", fontsize=8, color=col,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.85),
        )

    ax1.set_xlim(0, horizon_days)
    ax1.set_ylabel("Concentration (mg/L)")
    ax1.set_title(
        f"Protocole {label}{' — ' + title_suffix if title_suffix else ''}\n"
        f"Eff={result.eff:.3f}  Tox={result.tox:.5f}  "
        f"Obj={result.obj:.3f}  Dose cumulée={result.cum_dose:.0f}mg",
        fontweight="bold",
    )
    ax1.legend(fontsize=9)
    _apply_style(ax1)

    ax2.set_facecolor("#F8FAFC")
    for dose, day in zip(result.doses, result.times_days):
        ax2.barh(0, 1.5, left=day - 0.75, height=0.6,
                 color=col, alpha=0.85, edgecolor="white")
        ax2.text(day, 0, f"{dose:.0f}", ha="center", va="center",
                 fontsize=9, fontweight="bold", color="white")
    ax2.set_xlim(0, horizon_days)
    ax2.set_ylim(-0.8, 0.8)
    ax2.set_yticks([])
    ax2.set_xlabel("Temps (jours)")
    ax2.set_title("Calendrier (doses en mg)", fontsize=10)
    _apply_style(ax2)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=130, bbox_inches="tight")
    return fig


def plot_profiles_comparison(
    results: Dict[str, OptResult],
    pk_adj: PKParameters,
    cross_eval: Dict[str, Dict],
    horizon_days: int = 28,
    patient_label: str = "",
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Superpose les profils PK des trois approches sur trois axes partagés.

    Parameters
    ----------
    results : dict[str, OptResult]
        Résultats indexés par clé de modèle (``'det'``, ``'sto'``, ``'rob'``).
    pk_adj : PKParameters
        Paramètres PK ajustés au patient.
    cross_eval : dict[str, dict]
        Statistiques d'évaluation croisée (issues de :func:`eval_scenarios`)
        pour chaque modèle.
    horizon_days : int, optional
        Horizon d'affichage. Défaut : 28.
    patient_label : str, optional
        Identifiant du patient affiché dans le titre.
    save_path : str, optional
        Chemin de sauvegarde (PNG).

    Returns
    -------
    plt.Figure
    """
    t_ev = np.linspace(0, horizon_days * 24, 5000)
    fig, axes = plt.subplots(3, 1, figsize=(13, 10), sharex=True)
    fig.suptitle(
        f"Profils PK comparés{' — ' + patient_label if patient_label else ''}",
        fontsize=13, fontweight="bold",
    )

    for ax, (key, res) in zip(axes, results.items()):
        col   = COLORS.get(key, "#333")
        label = LABELS.get(key, key)
        c     = pk_multi(res.doses, [d * 24 for d in res.times_days], pk_adj, t_ev) if res.doses else np.zeros_like(t_ev)
        cx    = cross_eval.get(key, {})

        ax.fill_between(t_ev / 24, c, alpha=0.18, color=col)
        ax.plot(t_ev / 24, c, color=col, lw=2.5)
        ax.axhspan(pk_adj.cmin_eff, pk_adj.cmax_safe, alpha=0.08, color="green")
        ax.axhline(pk_adj.cmax_safe, color="red",   ls="--", lw=1.3)
        ax.axhline(pk_adj.cmin_eff,  color="green", ls="--", lw=1.3)

        for dose, day in zip(res.doses, res.times_days):
            ax.axvline(day, color=col, ls=":", alpha=0.35)
            ax.annotate(f"{dose:.0f}mg", (day, pk_adj.cmax_safe * 0.05),
                        ha="center", fontsize=8, color=col,
                        bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.85))

        ax.set_title(
            f"{label}  |  Eff={res.eff:.3f}  Tox={res.tox:.5f}  "
            f"E[Obj]={cx.get('obj_mean', 0):.3f}  "
            f"Pire cas={cx.get('obj_worst', 0):.3f}  {res.ms:.0f}ms",
            fontsize=11, color=col, fontweight="bold",
        )
        ax.set_ylabel("Concentration (mg/L)")
        ax.set_xlim(0, horizon_days)
        _apply_style(ax)

    axes[-1].set_xlabel("Temps (jours)")
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=130, bbox_inches="tight")
    return fig


def plot_scenario_violins(
    cross_eval: Dict[str, Dict],
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Violin plots des distributions de métriques sur les scénarios patients.

    Parameters
    ----------
    cross_eval : dict[str, dict]
        Statistiques par modèle, indexées par clé (``'det'``, ``'sto'``, ``'rob'``).
        Chaque valeur doit contenir les listes ``'objs'``, ``'effs'``, ``'toxs'``.
    save_path : str, optional
        Chemin de sauvegarde (PNG).

    Returns
    -------
    plt.Figure
    """
    keys  = [k for k in ["det", "sto", "rob"] if k in cross_eval]
    labs  = [LABELS[k] for k in keys]
    cols  = [COLORS[k] for k in keys]

    fig = plt.figure(figsize=(14, 9))
    gs  = gridspec.GridSpec(2, 3, figure=fig, hspace=0.5, wspace=0.35)
    fig.suptitle("Comparaison des trois approches", fontsize=13, fontweight="bold")

    for ci, (mk, mt) in enumerate([("objs", "Objectif"), ("effs", "Efficacité"), ("toxs", "Toxicité")]):
        ax   = fig.add_subplot(gs[0, ci])
        data = [cross_eval[k][mk] for k in keys]
        vp   = ax.violinplot(data, positions=range(len(keys)), showmedians=True)
        for pc, col in zip(vp["bodies"], cols):
            pc.set_facecolor(col)
            pc.set_alpha(0.60)
        vp["cmedians"].set_color("white")
        vp["cmedians"].set_linewidth(2.5)
        ax.set_xticks(range(len(keys)))
        ax.set_xticklabels(labs, fontsize=9)
        ax.set_title(mt, fontweight="bold")
        ax.set_ylabel("Score")
        _apply_style(ax)

    for ci, (bk, bt) in enumerate([
        ("obj_mean",  "E[Objectif] ↑"),
        ("obj_worst", "Pire cas ↑"),
        ("obj_std",   "Std[Objectif] ↓"),
    ]):
        ax   = fig.add_subplot(gs[1, ci])
        vals = [cross_eval[k][bk] for k in keys]
        bars = ax.bar(labs, vals, color=cols, alpha=0.85, edgecolor="white")
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + abs(max(vals) - min(vals)) * 0.02,
                    f"{v:.3f}", ha="center", fontsize=10, fontweight="bold")
        ax.set_title(bt, fontweight="bold")
        ax.set_ylabel("Valeur")
        ax.axhline(0, color="black", lw=0.8, ls="--")
        _apply_style(ax)

    if save_path:
        fig.savefig(save_path, dpi=130, bbox_inches="tight")
    return fig


def plot_pareto(
    candidates_stats: List[Dict],
    highlighted: Dict[str, Dict],
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Front de Pareto empirique : Efficacité vs Toxicité.

    Parameters
    ----------
    candidates_stats : list of dict
        Statistiques d'évaluation de chaque candidat (clés ``'tox_mean'``,
        ``'eff_mean'``, ``'obj_mean'``).
    highlighted : dict[str, dict]
        Approches à mettre en évidence, indexées par clé de modèle.
    save_path : str, optional
        Chemin de sauvegarde (PNG).

    Returns
    -------
    plt.Figure
    """
    fig, ax = plt.subplots(figsize=(9, 6))
    sc = ax.scatter(
        [p["tox_mean"] for p in candidates_stats],
        [p["eff_mean"] for p in candidates_stats],
        c=[p["obj_mean"] for p in candidates_stats],
        cmap="RdYlGn", s=35, alpha=0.55, edgecolors="none", zorder=2,
    )
    plt.colorbar(sc, ax=ax, label="E[Obj]")

    ax.axvspan(0,    0.25, alpha=0.06, color="green")
    ax.axvspan(0.25, 0.50, alpha=0.06, color="yellow")
    ax.axvspan(0.50, 1.00, alpha=0.06, color="red")

    markers = {"det": "D", "sto": "^", "rob": "s"}
    for key, stats in highlighted.items():
        ax.scatter(
            stats.get("tox_mean", 0), stats.get("eff_mean", 0),
            color=COLORS.get(key, "#333"), s=200, zorder=5,
            marker=markers.get(key, "o"),
            edgecolors="white", linewidths=1.5,
            label=LABELS.get(key, key),
        )

    for x, lbl, color in [
        (0.12, "Faible risque",  "green"),
        (0.37, "Risque modéré",  "olive"),
        (0.70, "Haut risque",    "red"),
    ]:
        ax.text(x, 0.03, lbl, ha="center", fontsize=8, color=color, style="italic")

    ax.set_xlabel("Toxicité moyenne", fontsize=12)
    ax.set_ylabel("Efficacité moyenne", fontsize=12)
    ax.set_title("Front de Pareto empirique\n"
                 "Protocoles candidats évalués sur scénarios patients",
                 fontweight="bold")
    ax.legend(fontsize=10)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    _apply_style(ax)
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=130, bbox_inches="tight")
    return fig


def plot_lambda_sensitivity(
    df_lambda,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Visualise l'impact du paramètre λ sur le trade-off Eff/Tox.

    Parameters
    ----------
    df_lambda : pd.DataFrame
        Colonnes attendues : ``'λ'``, ``'Efficacité'``, ``'Toxicité'``, ``'N doses'``.
    save_path : str, optional
        Chemin de sauvegarde (PNG).

    Returns
    -------
    plt.Figure
    """
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    fig.suptitle("Analyse de sensibilité — Impact de λ", fontweight="bold")

    axes[0].plot(df_lambda["λ"], df_lambda["Efficacité"], "o-",
                 color=COLORS["teal"],   lw=2.5, ms=8, label="Efficacité")
    axes[0].plot(df_lambda["λ"], df_lambda["Toxicité"] * 10, "s-",
                 color=COLORS["orange"], lw=2.5, ms=8, label="Toxicité ×10")
    axes[0].set_xlabel("λ"); axes[0].set_ylabel("Score")
    axes[0].set_title("Efficacité & Toxicité vs λ", fontweight="bold")
    axes[0].legend()
    _apply_style(axes[0])

    axes[1].bar(df_lambda["λ"].astype(str), df_lambda["N doses"],
                color=COLORS["det"], alpha=0.8, edgecolor="white")
    axes[1].set_xlabel("λ"); axes[1].set_ylabel("N doses")
    axes[1].set_title("Nombre de doses vs λ", fontweight="bold")
    _apply_style(axes[1])

    sc = axes[2].scatter(df_lambda["Toxicité"], df_lambda["Efficacité"],
                         c=df_lambda["λ"], cmap="RdYlGn_r", s=160, zorder=5,
                         edgecolors="white", linewidths=1.5)
    plt.colorbar(sc, ax=axes[2], label="λ")
    for _, row in df_lambda.iterrows():
        axes[2].annotate(f"λ={row['λ']}", (row["Toxicité"], row["Efficacité"]),
                         textcoords="offset points", xytext=(6, 4), fontsize=8)
    axes[2].set_xlabel("Toxicité"); axes[2].set_ylabel("Efficacité")
    axes[2].set_title("Front de Pareto empirique (λ croissant →)", fontweight="bold")
    _apply_style(axes[2])

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=130, bbox_inches="tight")
    return fig


def plot_population_results(
    df_pop,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Visualise les résultats des trois approches sur une cohorte de patients.

    Parameters
    ----------
    df_pop : pd.DataFrame
        Colonnes attendues : ``'PID'``, ``'E[Obj] Det'``, ``'E[Obj] SAA'``,
        ``'E[Obj] Rob'``, ``'Pire Det'``, ``'Pire Rob'``,
        ``'Sens.'``, ``'P(rép)'``, ``'Meilleure'``.
    save_path : str, optional
        Chemin de sauvegarde (PNG).

    Returns
    -------
    plt.Figure
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Résultats population", fontweight="bold")

    x  = np.arange(len(df_pop))
    bw = 0.25

    axes[0].bar(x - bw, df_pop["E[Obj] Det"], bw, label="Déterministe",
                color=COLORS["det"], alpha=0.85)
    axes[0].bar(x,      df_pop["E[Obj] SAA"], bw, label="SAA",
                color=COLORS["sto"], alpha=0.85)
    axes[0].bar(x + bw, df_pop["E[Obj] Rob"], bw, label="Robuste",
                color=COLORS["rob"], alpha=0.85)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(df_pop["PID"], rotation=45)
    axes[0].set_ylabel("E[Objectif]")
    axes[0].set_title("Espérance de l'objectif par patient", fontweight="bold")
    axes[0].legend(fontsize=9)
    axes[0].axhline(0, color="black", lw=0.8, ls="--")
    _apply_style(axes[0])

    sc = axes[1].scatter(
        df_pop["Sens."], df_pop["P(rép)"],
        c=df_pop["E[Obj] SAA"], cmap="RdYlGn",
        s=180, alpha=0.9, edgecolors="white", vmin=-0.1, vmax=0.45,
    )
    plt.colorbar(sc, ax=axes[1], label="E[Obj] SAA")
    for _, r in df_pop.iterrows():
        axes[1].annotate(
            f"{r['PID']}\n({r['Meilleure']})",
            (r["Sens."], r["P(rép)"]),
            textcoords="offset points", xytext=(5, 5), fontsize=7,
        )
    axes[1].set_xlabel("Sensibilité à la toxicité")
    axes[1].set_ylabel("P(réponse tumorale)")
    axes[1].set_title("Carte de risque — meilleure approche par patient", fontweight="bold")
    _apply_style(axes[1])

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=130, bbox_inches="tight")
    return fig


