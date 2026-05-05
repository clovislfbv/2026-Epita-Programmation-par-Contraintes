"""Parser pour le format de fichier CATS officiel (Leyton-Brown 2000).

Le générateur CATS (https://github.com/kevinlb1/CATS) écrit ses instances
dans un format texte simple :

    %% commentaires en %% ou %
    goods <n_real>
    bids  <n_total_bids>
    dummy <n_dummy_goods>

    <bid_id> <price> <good_id_1> <good_id_2> ... #
    ...

Les ``<good_id>`` < ``n_real`` sont de **vrais items**. Les
``<good_id>`` >= ``n_real`` sont des **dummy goods**, dispositif
spécifique à CATS pour encoder les contraintes XOR : deux bids qui
partagent le même dummy good deviennent automatiquement mutuellement
exclusifs (par l'exclusivité d'item). Cela permet d'exprimer le langage
**OR-of-XOR** (un bidder peut soumettre plusieurs clauses XOR
indépendantes) sans modifier la WDP elle-même.

Les prix sont des entiers car généré avec ``-int_prices`` : la valeur
réelle est ``stored / bid_alpha`` (par défaut ``bid_alpha=1000``).

Convention pour notre import :
    - Items réels : ``i_0``, ``i_1``, ..., ``i_{n_real-1}``.
    - Dummy goods : convertis en ``xor_groups`` Python explicites
      (un groupe par dummy good ayant >=2 bids).
    - Bidders : on génère un bidder unique par bid (faute d'info dans
      le fichier CATS — CATS travaille au niveau bid). On peut grouper
      les bids partageant un dummy comme appartenant au "même bidder
      logique" si nécessaire (cf. ``BidderGrouping``).

Référence : Leyton-Brown, Pearson, Shoham. *Towards a Universal Test
Suite for Combinatorial Auction Algorithms*. EC 2000.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from .instance import Bid, Budget, Instance


class BidderGrouping(str, Enum):
    """Stratégie d'attribution des bids aux bidders."""

    PER_BID = "per_bid"
    """Un bidder par bid (convention par défaut, sans hypothèse)."""

    PER_DUMMY = "per_dummy"
    """Les bids partageant un dummy good appartiennent au même bidder
    logique. Plus fidèle à la sémantique CATS où un dummy = une clause
    XOR d'un agent."""


@dataclass
class CatsHeader:
    n_real_goods: int
    n_total_bids: int
    n_dummy_goods: int
    raw_comments: list[str] = field(default_factory=list)


@dataclass
class CatsRawBid:
    bid_id: int
    price: float
    real_good_ids: list[int]
    dummy_good_ids: list[int]


def _parse_header_and_bids(
    text: str, bid_alpha: float = 1000.0
) -> tuple[CatsHeader, list[CatsRawBid]]:
    """Lit l'en-tête CATS + tous les bids ; ne convertit pas en Instance."""
    lines = text.splitlines()
    header_kv: dict[str, int] = {}
    raw_comments: list[str] = []
    bid_lines: list[str] = []

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("%"):
            raw_comments.append(line)
            continue
        # Header lines : "goods 30", "bids 104", "dummy 19"
        parts = line.split()
        if len(parts) == 2 and parts[0] in {"goods", "bids", "dummy"}:
            header_kv[parts[0]] = int(parts[1])
            continue
        # Bid line : "bid_id  price  good1 good2 ... #"
        bid_lines.append(line)

    if not {"goods", "bids", "dummy"} <= header_kv.keys():
        missing = {"goods", "bids", "dummy"} - header_kv.keys()
        raise ValueError(f"CATS header missing keys: {sorted(missing)}")

    n_real = header_kv["goods"]
    n_dummy = header_kv["dummy"]

    bids: list[CatsRawBid] = []
    for line in bid_lines:
        # Le séparateur est tab ou espace. La ligne se termine par '#'.
        line = line.rstrip()
        if line.endswith("#"):
            line = line[:-1].rstrip()
        tokens = line.split()
        if len(tokens) < 2:
            raise ValueError(f"CATS bid line malformée : {line!r}")
        bid_id = int(tokens[0])
        price_int = int(tokens[1])
        good_ids = [int(t) for t in tokens[2:]]
        real = [g for g in good_ids if g < n_real]
        dummy = [g for g in good_ids if g >= n_real]
        bids.append(
            CatsRawBid(
                bid_id=bid_id,
                price=price_int / bid_alpha,
                real_good_ids=real,
                dummy_good_ids=dummy,
            )
        )

    return (
        CatsHeader(
            n_real_goods=n_real,
            n_total_bids=header_kv["bids"],
            n_dummy_goods=n_dummy,
            raw_comments=raw_comments,
        ),
        bids,
    )


def parse_cats_file(
    path: str | Path,
    bid_alpha: float = 1000.0,
    bidder_grouping: BidderGrouping = BidderGrouping.PER_BID,
    name: Optional[str] = None,
) -> Instance:
    """Charge une instance CATS et la convertit en :class:`Instance`.

    Args:
        path: chemin vers le fichier CATS (``.txt`` ou similaire).
        bid_alpha: facteur appliqué par CATS via ``-int_prices`` (défaut 1000).
        bidder_grouping: voir :class:`BidderGrouping`.
        name: nom logique (par défaut, basename du fichier sans extension).

    Returns:
        :class:`Instance` avec :
            - ``items = ["i_0", ..., "i_{n_real-1}"]``
            - ``xor_groups`` reconstruits à partir des dummy goods
              (un groupe par dummy good partagé par >=2 bids)
            - ``bidders`` selon ``bidder_grouping``
    """
    path = Path(path)
    text = path.read_text()
    header, raw_bids = _parse_header_and_bids(text, bid_alpha=bid_alpha)

    items = [f"i_{i}" for i in range(header.n_real_goods)]

    # Bidder mapping
    bidder_of_bid: dict[int, str] = {}
    if bidder_grouping == BidderGrouping.PER_BID:
        for rb in raw_bids:
            bidder_of_bid[rb.bid_id] = f"b{rb.bid_id}"
    elif bidder_grouping == BidderGrouping.PER_DUMMY:
        # Union-find pour regrouper les bids partageant un dummy
        parent: dict[int, int] = {rb.bid_id: rb.bid_id for rb in raw_bids}

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int) -> None:
            ra, rb_ = find(a), find(b)
            if ra != rb_:
                parent[ra] = rb_

        # Indexe par dummy good
        bids_by_dummy: dict[int, list[int]] = {}
        for rb in raw_bids:
            for d in rb.dummy_good_ids:
                bids_by_dummy.setdefault(d, []).append(rb.bid_id)
        for group in bids_by_dummy.values():
            anchor = group[0]
            for other in group[1:]:
                union(anchor, other)

        # Nomme chaque cluster
        cluster_name: dict[int, str] = {}
        next_id = 0
        for rb in raw_bids:
            root = find(rb.bid_id)
            if root not in cluster_name:
                cluster_name[root] = f"b{next_id}"
                next_id += 1
            bidder_of_bid[rb.bid_id] = cluster_name[root]
    else:
        raise ValueError(f"Unknown BidderGrouping: {bidder_grouping}")

    bidders = sorted(set(bidder_of_bid.values()))

    bids: list[Bid] = [
        Bid(
            id=rb.bid_id,
            bidder=bidder_of_bid[rb.bid_id],
            items=frozenset(f"i_{g}" for g in rb.real_good_ids),
            price=float(rb.price),
        )
        for rb in raw_bids
    ]

    # XOR groups : un par dummy good ayant >= 2 bids
    bids_by_dummy: dict[int, list[int]] = {}
    for rb in raw_bids:
        for d in rb.dummy_good_ids:
            bids_by_dummy.setdefault(d, []).append(rb.bid_id)
    xor_groups = [sorted(group) for group in bids_by_dummy.values() if len(group) >= 2]

    return Instance(
        name=name or path.stem,
        items=items,
        bidders=bidders,
        bids=bids,
        budget=Budget(),
        xor_groups=xor_groups,
    )
