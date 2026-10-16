"""Generic helpers shared by solvers and the API layer."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

import numpy as np


def to_builtin(obj: Any) -> Any:
    """Recursively convert NumPy scalars/arrays into JSON-safe Python values.

    Solvers work with NumPy, the response contract is JSON. This is the single
    safety net applied by the API layer before serialising a solve response.
    """
    if isinstance(obj, dict):
        return {key: to_builtin(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_builtin(value) for value in obj]
    if isinstance(obj, np.ndarray):
        return to_builtin(obj.tolist())
    if isinstance(obj, np.generic):
        return obj.item()
    return obj


def split_points(points: Sequence[Sequence[float]]) -> tuple[list[float], list[float]]:
    """Split ``[[x, y], ...]`` into parallel x and y lists."""
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return xs, ys


def float_list(values: Iterable[Any]) -> list[float]:
    """Convert any iterable of numbers to ``list[float]``."""
    return [float(value) for value in values]
