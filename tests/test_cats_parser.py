"""Tests du parser pour le format CATS officiel."""

from __future__ import annotations

from pathlib import Path

import pytest

from wdp.cats_parser import (
    BidderGrouping,
    _parse_header_and_bids,
    parse_cats_file,
)
from wdp.solver_cpsat import solve_wdp_cpsat
from wdp.solver_milp import solve_wdp_milp

CATS_DIR = Path(__file__).resolve().parent.parent / "data" / "cats"
CATS_FILES = sorted(CATS_DIR.glob("*.txt"))


def _one_file_per_distribution() -> list[Path]:
    """Renvoie une seule instance par distribution (1ère par ordre alpha).

    Évite que la paramétrisation `CATS_FILES[:3]` ne couvre qu'une seule
    distribution (`arbitrary_*` en ordre alpha) — biais identifié par
    audit indépendant 2026-05-15.
    """
    seen: dict[str, Path] = {}
    for path in CATS_FILES:
        distrib = path.stem.split("_")[0]
        if distrib not in seen:
            seen[distrib] = path
    return list(seen.values())


CATS_FILES_ONE_PER_DIST = _one_file_per_distribution()


# ---------------------------------------------------------------------------
# Header / structure
# ---------------------------------------------------------------------------

def test_header_parsing_minimal():
    """Header CATS minimal correctement extrait."""
    text = (
        "%% comment\n"
        "% another\n"
        "\n"
        "goods 5\n"
        "bids  2\n"
        "dummy 1\n"
        "\n"
        "0\t1500\t0\t1\t5\t#\n"
        "1\t2000\t2\t3\t4\t5\t#\n"
    )
    header, bids = _parse_header_and_bids(text, bid_alpha=1000.0)
    assert header.n_real_goods == 5
    assert header.n_total_bids == 2
    assert header.n_dummy_goods == 1
    assert len(bids) == 2

    b0, b1 = bids
    assert b0.bid_id == 0
    assert b0.real_good_ids == [0, 1]
    assert b0.dummy_good_ids == [5]
    assert b0.price == pytest.approx(1.5)
    assert b1.real_good_ids == [2, 3, 4]
    assert b1.dummy_good_ids == [5]
    assert b1.price == pytest.approx(2.0)


def test_xor_groups_reconstructed_from_dummy_goods():
    """Bids partageant un dummy good doivent former un groupe XOR."""
    text = (
        "goods 4\n"
        "bids 3\n"
        "dummy 2\n"
        "0 1000 0 1 4 #\n"   # dummy 4
        "1 2000 2 3 4 #\n"   # dummy 4 (XOR avec 0)
        "2 3000 0 1 5 #\n"   # dummy 5 (singleton, pas de XOR)
    )
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(text)
        path = f.name
    inst = parse_cats_file(path)

    # Items réels uniquement (4 vrais)
    assert inst.n_items == 4
    assert inst.n_bids == 3
    # Un seul groupe XOR (le dummy 4 partagé par bids 0 et 1)
    assert len(inst.xor_groups) == 1
    assert sorted(inst.xor_groups[0]) == [0, 1]


# ---------------------------------------------------------------------------
# End-to-end : parse + solve
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", CATS_FILES, ids=lambda p: p.stem)
def test_cats_file_parses_and_solves(path):
    """Chaque fichier CATS doit (1) se parser sans erreur, (2) se résoudre
    à OPTIMAL par CP-SAT en moins de 30s, (3) produire un revenu >= 0."""
    inst = parse_cats_file(path)
    assert inst.n_items > 0
    assert inst.n_bids > 0
    alloc = solve_wdp_cpsat(inst, time_limit_s=30.0)
    assert alloc.status == "OPTIMAL", f"{path.name}: status={alloc.status}"
    assert alloc.revenue >= 0


@pytest.mark.parametrize(
    "path", CATS_FILES_ONE_PER_DIST, ids=lambda p: p.stem
)
def test_cats_cpsat_milp_agree(path):
    """CP-SAT et PLNE doivent donner le même optimum sur les CATS instances
    (validation de la cohérence des deux modélisations).

    Couvre **une instance par distribution** (arbitrary, matching, paths,
    regions, scheduling) pour garantir une couverture représentative.
    """
    inst = parse_cats_file(path)
    cp = solve_wdp_cpsat(inst, time_limit_s=30.0)
    mip = solve_wdp_milp(inst, time_limit_s=30.0)
    if cp.status == "OPTIMAL" and mip.status == "OPTIMAL":
        # PRICE_SCALE=1000 dans solver_cpsat.py est aligné sur
        # bid_alpha=1000 du parser CATS : CP-SAT manipule donc les prix
        # CATS de manière bit-exacte. Tolérance étroite suffisante.
        assert cp.revenue == pytest.approx(mip.revenue, rel=1e-4, abs=1e-3)


# ---------------------------------------------------------------------------
# Output properties (item-exclusivity + XOR satisfaction)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "path", CATS_FILES_ONE_PER_DIST, ids=lambda p: p.stem
)
def test_cats_solver_output_respects_constraints(path):
    """Sur chaque distribution CATS : la solution CP-SAT doit respecter
    (a) l'exclusivité d'item (items des bids gagnants 2-à-2 disjoints),
    (b) les groupes XOR (au plus 1 gagnant par groupe),
    et le revenu rapporté doit recoller avec la somme des prix gagnants.

    Audit indépendant 2026-05-15 : ces invariants étaient vérifiés
    manuellement, désormais codifiés.
    """
    inst = parse_cats_file(path)
    alloc = solve_wdp_cpsat(inst, time_limit_s=30.0)
    assert alloc.status == "OPTIMAL"

    bid_by_id = {b.id: b for b in inst.bids}
    winners = [bid_by_id[i] for i in alloc.winning_bid_ids]

    # (a) Item exclusivity : aucun item partagé entre 2 winners
    seen_items: set[str] = set()
    for b in winners:
        overlap = b.items & seen_items
        assert not overlap, f"Item conflict in {path.name}: {sorted(overlap)}"
        seen_items |= b.items

    # (b) XOR : chaque groupe a au plus 1 winner
    winner_ids = set(alloc.winning_bid_ids)
    for k, group in enumerate(inst.xor_groups):
        active = winner_ids & set(group)
        assert len(active) <= 1, (
            f"XOR group {k} in {path.name} has {len(active)} winners: "
            f"{sorted(active)}"
        )

    # (c) Revenu rapporté = somme des prix.
    # PRICE_SCALE=1000 (cf. solver_cpsat.py) aligne CP-SAT sur le
    # bid_alpha=1000 de CATS : aucune perte de précision attendue
    # au-delà du bruit FP standard.
    recomputed = sum(b.price for b in winners)
    assert alloc.revenue == pytest.approx(recomputed, rel=1e-4, abs=1e-3)


# ---------------------------------------------------------------------------
# BidderGrouping
# ---------------------------------------------------------------------------

def test_bidder_grouping_per_dummy_aggregates_xor_clusters():
    """En mode PER_DUMMY, les bids partageant un dummy good appartiennent
    au même bidder logique (cluster transitif)."""
    text = (
        "goods 4\n"
        "bids 4\n"
        "dummy 2\n"
        "0 1000 0    4    #\n"   # dummy 4
        "1 1000 1    4    #\n"   # dummy 4 → cluster avec 0
        "2 1000 2 5       #\n"   # dummy 5 → cluster séparé
        "3 1000 3 5       #\n"   # dummy 5 → cluster avec 2
    )
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(text)
        path = f.name

    inst_per_bid = parse_cats_file(path, bidder_grouping=BidderGrouping.PER_BID)
    assert inst_per_bid.n_bidders == 4

    inst_per_dummy = parse_cats_file(
        path, bidder_grouping=BidderGrouping.PER_DUMMY
    )
    # 2 clusters : {0,1} et {2,3}
    assert inst_per_dummy.n_bidders == 2
