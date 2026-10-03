"""Map an overlay provider's quantity names to the table's actual columns.

Aliases distinguish fluorescence-weighted (tau_f) from species-weighted
(tau_x) lifetimes. Uncorrected proximity ratios are not aliases of e_fret.
Names are matched exactly, ignoring case, never by substring.
"""
from __future__ import annotations

from typing import Optional, Sequence

AXIS_ALIASES = {
    "tau_f": ("tau_f (ns)", "Tau (green)", "TauD(A)", "<tauD(A)>f"),
    "tau_x": ("tau_x (ns)", "<tauD(A)>x"),
    "e_fret": ("E", "FRET efficiency", "FRET efficiency(PIE)",
               "FRET efficiency(ALEX)", "FRET efficiency (corrected)"),
}


def resolve_axis(names: Sequence[str], quantity: str) -> Optional[str]:
    """Return an exact column or its unique declared alias, else ``None``."""
    if quantity in names:
        return quantity
    wanted = quantity.casefold()
    exact = [name for name in names if name.casefold() == wanted]
    if exact:
        return exact[0] if len(exact) == 1 else None
    aliases = {name.casefold() for name in AXIS_ALIASES.get(wanted, ())}
    matches = [name for name in names if name.casefold() in aliases]
    return matches[0] if len(matches) == 1 else None
