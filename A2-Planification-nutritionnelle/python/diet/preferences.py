from __future__ import annotations

from typing import Any, Dict


def score_item_penalty(item: Dict[str, Any], preferences: Dict[str, Any]) -> float:
    likes = set(preferences.get("likes", []))
    dislikes = set(preferences.get("dislikes", []))
    like_weight = float(preferences.get("like_weight", 0.0))
    dislike_weight = float(preferences.get("dislike_weight", 0.0))
    tag_bonus = preferences.get("tag_bonus", {}) or {}
    tag_penalty = preferences.get("tag_penalty", {}) or {}

    penalty = 0.0
    item_id = item.get("id")
    if item_id in dislikes:
        penalty += dislike_weight
    elif item_id in likes:
        penalty -= like_weight

    for tag in item.get("tags", []) or []:
        penalty += float(tag_penalty.get(tag, 0.0))
        penalty += float(tag_bonus.get(tag, 0.0))

    return penalty
