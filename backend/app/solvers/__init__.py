"""Solver package.

Importing this package (or calling :func:`load_all`) imports every solver
module, which triggers self-registration via :func:`app.core.registry.register`.
Dropping a new file into a chapter folder is therefore enough — no import list,
router or UI change is ever required.
"""

from __future__ import annotations

import importlib
import pkgutil

_LOADED = False


def load_all(*, reload: bool = False) -> None:
    """Import all solver modules so they register themselves.

    Args:
        reload: When ``True``, re-import every module even if already loaded
            (used by tests that rebuild the registry).
    """
    global _LOADED
    if _LOADED and not reload:
        return
    for module_info in pkgutil.walk_packages(__path__, prefix=f"{__name__}."):
        leaf = module_info.name.rsplit(".", maxsplit=1)[-1]
        if leaf.startswith("_"):
            continue
        importlib.import_module(module_info.name)
    _LOADED = True
