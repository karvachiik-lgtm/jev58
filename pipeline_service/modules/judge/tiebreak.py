"""Draw tie-break, pure functions (no I/O), so the rule can be tested and its order-invariance checked on its own.

Why: when the multi-stage judge returns "draw", the bracket still needs a winner. The inherited rule used DINOv3 best-view similarity
(33.1% agreement with validator outcomes on recorded duels: chance) and otherwise returned "A", i.e. whichever candidate the bracket
happened to put first. S1 has already scored every angle in BOTH prompt orders, and its weighted penalty difference on a draw is only
"below the 0.7 threshold", not zero. Its sign agrees with a common-opponent quality ordering 76.4% of the time (n = 9,390 near-peer duels),
rising with |residual|. That signal is free: no extra judge call.

Invariant (proved for the decision rule in lean/TieBreak.lean, checked here by tests): swapping the two candidates swaps the answer.
"""
from __future__ import annotations


def _usable(angle: dict) -> bool:
    return not angle.get("contradictory") and not angle.get("json_failed") and "pen_a" in angle and "pen_b" in angle


def s1_residual(detail: dict | None) -> float | None:
    """Weighted mean S1 penalty of A minus that of B over the consistent angles (the same quantity S1 compares with its draw threshold).
    Lower penalty is better, so a negative residual favours A. None when S1 has no usable angle."""
    s1 = (detail or {}).get("s1") or {}
    angles = [a for a in s1.get("angles", []) if _usable(a)]
    tw = sum(float(a.get("weight", 1.0)) for a in angles)
    if not angles or tw <= 0:
        return None
    wpa = sum(float(a.get("weight", 1.0)) * float(a["pen_a"]) for a in angles) / tw
    wpb = sum(float(a.get("weight", 1.0)) * float(a["pen_b"]) for a in angles) / tw
    return wpa - wpb


def side_from_residual(r: float | None) -> str | None:
    """The decision rule: negative -> A, positive -> B, zero or unknown -> no decision."""
    if r is None or r == 0:
        return None
    return "A" if r < 0 else "B"


def s1_residual_side(detail: dict | None) -> tuple[str | None, str]:
    r = s1_residual(detail)
    side = side_from_residual(r)
    if side is None:
        return None, "no S1 residual"
    return side, f"S1-residual tie-break (wpA-wpB={r:+.3f} -> {side})"


def order_free_side(order_key: tuple[str, str] | None) -> str:
    """Last resort when neither S1 nor DINO says anything: pick by comparing content digests of the two candidates. Swapping the
    candidates swaps the answer, so no position is favoured. Identical candidates (equal digests) -> "A" (they are the same program)."""
    if not order_key or order_key[0] == order_key[1]:
        return "A"
    return "A" if order_key[0] < order_key[1] else "B"


def swap_detail(detail: dict) -> dict:
    """The S1 detail as it would read with the two candidates exchanged (used by the tests)."""
    s1 = dict(detail.get("s1") or {})
    s1["angles"] = [dict(a, pen_a=a["pen_b"], pen_b=a["pen_a"]) for a in s1.get("angles", [])]
    return dict(detail, s1=s1)
