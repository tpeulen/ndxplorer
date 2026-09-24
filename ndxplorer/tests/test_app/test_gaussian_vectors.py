"""Population-wise Gaussians in the emtk app: drawn per population, saved and loaded.

A Gaussian parameter made a vector draws that component once per population
(tinted, labelled), and *Save* / *Load* keep the vector: the JSON carries the
group state (``"parameters"`` with its ``"vectors"`` entry) beside the records.
"""

from __future__ import annotations

import json

import numpy as np
import pytest
from ndxplorer.analysis import gaussian_mixture as gm
from ndxplorer.core.gaussian_parameters import build_gaussian_group

from .test_parameter_tables import gaussians  # noqa: F401 - the fixture


def test_save_and_load_keep_a_vector_in_the_file(tmp_path):
    group = build_gaussian_group()
    group.append((1.0, 2.0), np.diag([0.25, 0.25]))
    group.append((3.0, 4.0), np.diag([0.25, 0.25]))
    group.get("x_2").set_vector([2.5, 3.5], ["HF", "LF"], column="Population")
    group.get("x_2[LF]").fixed = True
    written = gm.save_gaussians(str(tmp_path / "g.json"), group.records(),
                                [(c.mu, c.cov, c.w) for c in group.components()],
                                {"x": {"name": "a"}, "y": {"name": "b"}},
                                state=group.get_state())
    saved = json.loads(open(written[0]).read())
    assert saved["parameters"]["vectors"]["x_2"]["populations"] == ["HF", "LF"]

    back = build_gaussian_group()
    rows, _axes = gm.load_gaussians(written[0])
    for mu, cov, w, *_flags in rows:
        back.append(mu, cov, w)
    back.set_state(gm.load_gaussian_state(written[0]))
    x2 = back.get("x_2")
    assert x2.is_vector and x2.populations == ["HF", "LF"]
    assert [e.value for e in x2.elements] == pytest.approx([2.5, 3.5])
    assert x2.element("LF").fixed and not x2.element("HF").fixed
    assert x2.vector_state()["column"] == "Population"
    assert gm.load_gaussian_state(written[1]) is None          # the CSV has no state


def test_the_panel_saves_and_loads_a_vector(gaussians, tmp_path):  # noqa: F811
    run, panel = gaussians
    panel.group.get("y_1").set_vector([0.3, 0.4], ["0", "1"])
    path = tmp_path / "gauss.json"
    panel._save_to(str(path))
    panel.clear()
    assert len(panel.group) == 0
    panel.load_from(str(path))
    y1 = panel.group.get("y_1")
    assert y1.is_vector and [e.value for e in y1.elements] == pytest.approx([0.3, 0.4])
    assert len(panel.group) == 2


def test_the_map_draws_each_population_of_a_vector_component(gaussians, monkeypatch):  # noqa: F811
    from emtk import implot

    run, panel = gaussians
    lines, texts = [], []
    real_line, real_text = implot.plot_line, implot.plot_text
    monkeypatch.setattr(implot, "plot_line",
                        lambda label, *a, **k: (lines.append(label), real_line(label, *a, **k))[1])
    monkeypatch.setattr(implot, "plot_text",
                        lambda text, *a, **k: (texts.append(text), real_text(text, *a, **k))[1])
    run.settle(2)
    assert {l.split(".")[1] for l in lines if l.startswith("##gauss0.")} == {"None"}
    lines.clear()
    panel.group.get("x_1").to_vector(["HF", "LF"])
    panel.group.get("x_1[LF]").value = panel.group.get("x_1").value * 1.1
    run.settle(2)
    pops = {l.split(".")[1] for l in lines if l.startswith("##gauss0.")}
    assert pops == {"HF", "LF"}
    assert {l.split(".")[1] for l in lines if l.startswith("##gauss1.")} == {"HF", "LF"}
    assert {"HF", "LF"} <= set(texts)
    assert len(panel.rows()) == 4                               # 2 populations x 2 Gaussians


def test_fitting_without_a_population_column_says_so(gaussians):  # noqa: F811
    run, panel = gaussians
    panel.group.get("x_1").set_vector([0.5, 0.6], ["A", "B"], column="no such column")
    messages = []
    panel.feature.message = lambda title, text: messages.append((title, text))
    panel.fit()
    assert messages and messages[0][0] == "No populations"
    assert "no such column" in messages[0][1]
