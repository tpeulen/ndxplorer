"""The derived-column equations as an editable table: rows, validation, files.

An equation is ``{output: "expression"}``; the list of them derives the
columns ndXplorer plots (Proximity ratio, FRET efficiency, Fd/Fa…) from data
columns and constants. :class:`EquationTable` holds them as rows of
``output``, ``expression`` and a validity mark, the way both equation editors
show them, and checks every row the way the compute engine
(:mod:`ndxplorer.core.equation_graph`) will: the expression parses under the
arithmetic whitelist and every quoted name is a column, a constant or an
output. Toolkit-free.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .equation_graph import _ALLOWED_FUNCS, validate_equation

__all__ = ["OK_MARK", "BAD_MARK", "EquationTable", "validate_rows", "summary",
           "allowed_functions"]

OK_MARK = "✓"
BAD_MARK = "✗"


def allowed_functions() -> List[str]:
    """The functions an equation may call -- what the compute engine accepts."""
    return sorted(_ALLOWED_FUNCS)


def validate_rows(rows: Sequence[dict], columns: Iterable[str] = (),
                  constants: Iterable[str] = ()) -> int:
    """Mark every row ``ok``/``message``/``status``; returns how many are bad.

    An output may reference any other output: the engine orders them.
    """
    columns, constants = list(columns), list(constants)
    outputs = [str(r.get("output", "")).strip() for r in rows]
    outputs = [o for o in outputs if o]
    bad = 0
    for row in rows:
        name = str(row.get("output", "")).strip()
        ok, message = validate_equation(str(row.get("expression", "")).strip(), columns,
                                        constants, outputs)
        if not name:
            ok, message = False, "missing output name"
        row["ok"] = bool(ok)
        row["message"] = "" if ok else (message or "invalid")
        row["status"] = OK_MARK if ok else BAD_MARK
        bad += 0 if ok else 1
    return bad


def summary(total: int, bad: int) -> str:
    """``"N equation(s), all valid"`` or ``"N equation(s), M with problems"``."""
    if bad:
        return f"{total} equation(s), {bad} with problems"
    return f"{total} equation(s), all valid"


class EquationTable:
    """The equations as rows the user edits.

    Parameters
    ----------
    equations : list of dict, optional
        ``[{output: expression}, ...]``.
    """

    def __init__(self, equations: Optional[Sequence[dict]] = None) -> None:
        self.rows: List[dict] = []
        self.status = ""
        self.set_equations(equations or [])

    # ---------------------------------------------------------------- rows
    def set_equations(self, equations: Sequence[dict]) -> None:
        """Replace the rows."""
        self.rows = [self._row(str(k), str(v)) for mapping in equations or []
                     for k, v in dict(mapping).items()]

    @staticmethod
    def _row(output: str = "", expression: str = "") -> dict:
        return {"output": output, "expression": expression, "status": "", "ok": False,
                "message": ""}

    def equations(self) -> List[Dict[str, str]]:
        """The rows as ``[{output: expression}]``, leaving out incomplete ones."""
        out = []
        for row in self.rows:
            name = str(row.get("output", "")).strip()
            expression = str(row.get("expression", "")).strip()
            if name and expression:
                out.append({name: expression})
        return out

    def add(self, output: str = "", expression: str = "") -> int:
        """Append a row; returns its index."""
        self.rows.append(self._row(output, expression))
        return len(self.rows) - 1

    def remove(self, index: int) -> None:
        if 0 <= index < len(self.rows):
            del self.rows[index]

    def edit(self, index: int, key: str, value) -> None:
        """A cell changed: ``output`` or ``expression``."""
        if 0 <= index < len(self.rows) and key in ("output", "expression"):
            self.rows[index][key] = str(value)

    def insert(self, index: Optional[int], token: str) -> int:
        """Append *token* to the expression of row *index* (a new row if none)."""
        if index is None or not 0 <= index < len(self.rows):
            index = self.add()
        self.rows[index]["expression"] = (self.rows[index]["expression"] + token).strip()
        return index

    # ---------------------------------------------------------- validation
    def validate(self, columns: Iterable[str] = (), constants: Iterable[str] = ()) -> int:
        """Check every row; sets :attr:`status`; returns how many are bad."""
        bad = validate_rows(self.rows, columns, constants)
        self.status = summary(len(self.rows), bad)
        return bad

    # --------------------------------------------------------------- files
    def text(self) -> str:
        """The equations as YAML (a list of one-key maps), as the files hold them."""
        import yaml

        return yaml.safe_dump(self.equations(), sort_keys=False, default_flow_style=False,
                              allow_unicode=True)

    def set_text(self, text: str) -> None:
        import yaml

        data = yaml.safe_load(text) or []
        if not isinstance(data, list):
            raise ValueError("an equations file is a list of {output: expression}")
        self.set_equations(data)

    def load(self, path) -> None:
        with open(path, "r", encoding="utf-8") as handle:
            self.set_text(handle.read())

    def save(self, path) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(self.text())

    # --------------------------------------------------------------- names
    @staticmethod
    def names(columns: Iterable[str], constants: Iterable[str],
              outputs: Iterable[str] = ()) -> List[Tuple[str, str]]:
        """The Names & functions list: ``(kind, name)`` with ``kind`` a header.

        ``("header", "Constants")`` starts a group; ``("name", n)`` inserts
        ``'n'``, ``("function", "abs")`` inserts ``abs(``.
        """
        rows: List[Tuple[str, str]] = []
        groups = (("Constants", list(constants)),
                  ("Columns", list(dict.fromkeys(list(columns) + list(outputs)))))
        for title, names in groups:
            if names:
                rows.append(("header", title))
                rows.extend(("name", str(n)) for n in names)
        rows.append(("header", "Functions"))
        rows.extend(("function", f) for f in allowed_functions())
        return rows
