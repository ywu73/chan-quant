from __future__ import annotations

from itertools import pairwise

from chan_quant.domain.market import MarketBar
from chan_quant.domain.strategy import Fractal, FractalKind, StrategyStroke


def detect_fractals(bars: list[MarketBar]) -> list[Fractal]:
    fractals: list[Fractal] = []
    for pivot_index in range(1, len(bars) - 1):
        left = bars[pivot_index - 1]
        pivot = bars[pivot_index]
        right = bars[pivot_index + 1]
        if (
            pivot.high > left.high
            and pivot.high > right.high
            and pivot.low > left.low
            and pivot.low > right.low
        ):
            fractals.append(
                Fractal(
                    kind=FractalKind.TOP,
                    pivot_index=pivot_index,
                    confirmation_index=pivot_index + 1,
                    price=pivot.high,
                )
            )
        elif (
            pivot.low < left.low
            and pivot.low < right.low
            and pivot.high < left.high
            and pivot.high < right.high
        ):
            fractals.append(
                Fractal(
                    kind=FractalKind.BOTTOM,
                    pivot_index=pivot_index,
                    confirmation_index=pivot_index + 1,
                    price=pivot.low,
                )
            )
    return fractals


def _more_extreme(candidate: Fractal, current: Fractal) -> bool:
    if candidate.kind is FractalKind.TOP:
        return candidate.price > current.price
    return candidate.price < current.price


def build_strokes(fractals: list[Fractal], minimum_index_gap: int = 4) -> list[StrategyStroke]:
    if minimum_index_gap < 1:
        raise ValueError("minimum_index_gap must be positive")

    anchors: list[Fractal] = []
    for fractal in fractals:
        if not anchors:
            anchors.append(fractal)
            continue
        current = anchors[-1]
        if fractal.kind is current.kind:
            if _more_extreme(fractal, current):
                anchors[-1] = fractal
            continue
        if fractal.pivot_index - current.pivot_index >= minimum_index_gap:
            anchors.append(fractal)

    strokes: list[StrategyStroke] = []
    for index, (start, end) in enumerate(pairwise(anchors)):
        strokes.append(
            StrategyStroke(
                direction="UP" if start.kind is FractalKind.BOTTOM else "DOWN",
                start=start,
                end=end,
                confirmed=index < len(anchors) - 2,
            )
        )
    return strokes
