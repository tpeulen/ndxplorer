"""A ChiSurf sampling result opens from the folder the user actually has.

``sample_fit`` writes ``<target>/<timestamp>/chains/*.er4``: the folder chosen
when the run was started holds *runs*, and each run holds the chains. Asking the
user to walk down to the right level -- and silently returning nothing when they
pick the folder they know about -- is the difference between a result that opens
and one that does not.

The reader also has to say which chain a draw came from. ``n_runs`` independent
runs are stacked into one table, and whether those runs agree is the whole
question a sampling result exists to answer; a bag of numbers with the chain
identity thrown away cannot answer it.
"""

import numpy as np
import pandas as pd
import pytest

from ndxplorer.io import reader

HEADER = "# chi2r\tlnprior\tc\ta"


def write_chain(path, n_draws=20, offset=0.0, seed=0):
    """Write one ``.er4`` chain file in the format ``sample_fit`` produces."""
    rng = np.random.default_rng(seed)
    rows = np.column_stack([
        rng.normal(1.0, 0.01, n_draws),          # chi2r
        np.zeros(n_draws),                       # lnprior
        rng.normal(2.0 + offset, 0.1, n_draws),  # c
        rng.normal(0.5, 0.01, n_draws),          # a
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(HEADER + "\n")
        for row in rows:
            f.write("\t".join(f"{v:.18e}" for v in row) + "\n")
    return rows


def make_run(root, timestamp, n_chains=3, n_draws=20, offset=0.0):
    """Write one timestamped sampling run with ``n_chains`` chain files."""
    run = root / timestamp
    for i in range(n_chains):
        write_chain(run / "chains" / f"Model_-_Data_{i}.er4", n_draws=n_draws,
                    offset=offset, seed=i)
    return run


def test_the_folder_the_run_was_started_in_opens(tmp_path):
    """The user picks the folder they gave ChiSurf, not the one it created."""
    make_run(tmp_path, "2026-07-28_10-00-00", n_chains=3, n_draws=20)
    data = reader.read_sampling_folder(str(tmp_path)).data
    assert data is not None and len(data) == 60


@pytest.mark.parametrize("level", ["run", "chains"])
def test_the_inner_folders_open_too(tmp_path, level):
    """Whichever level is pointed at, the same chains come back."""
    run = make_run(tmp_path, "2026-07-28_10-00-00", n_chains=2, n_draws=15)
    target = run if level == "run" else run / "chains"
    data = reader.read_sampling_folder(str(target)).data
    assert data is not None and len(data) == 30


def test_a_draw_knows_which_chain_it_came_from(tmp_path):
    """Stacked runs must stay separable, or they cannot be compared."""
    make_run(tmp_path, "2026-07-28_10-00-00", n_chains=3, n_draws=25)
    data = reader.read_sampling_folder(str(tmp_path)).data
    assert sorted(data["chain"].unique()) == [0, 1, 2]
    assert data.groupby("chain").size().tolist() == [25, 25, 25]
    # ...and in which order, so a trace can be plotted at all.
    for _, chain in data.groupby("chain"):
        assert chain["draw"].tolist() == list(range(25))


def test_the_parameter_columns_survive_the_header(tmp_path):
    """The header is commented; its ``#`` must not end up in a column name."""
    make_run(tmp_path, "2026-07-28_10-00-00", n_chains=1, n_draws=10)
    data = reader.read_sampling_folder(str(tmp_path)).data
    assert list(data.columns)[:4] == ["chi2r", "lnprior", "c", "a"]
    assert np.isclose(data["a"].mean(), 0.5, atol=0.05)


def test_separate_runs_are_not_pooled_into_one_posterior(tmp_path):
    """Two timestamps are two sessions -- possibly of different fits.

    Stacking them would merge two posteriors into one cloud without saying so,
    which is worse than opening the wrong one: the result would look like a
    bimodal posterior that no run produced.
    """
    make_run(tmp_path, "2026-07-28_10-00-00", n_chains=2, n_draws=30, offset=0.0)
    make_run(tmp_path, "2026-07-28_18-30-00", n_chains=2, n_draws=30, offset=5.0)

    data = reader.read_sampling_folder(str(tmp_path)).data
    assert len(data) == 60
    # The most recent run is the one opened; timestamps sort chronologically.
    assert np.isclose(data["c"].mean(), 7.0, atol=0.5)


def test_a_folder_without_chains_returns_nothing_rather_than_raising(tmp_path):
    """An empty result is a normal outcome of pointing at the wrong place."""
    (tmp_path / "not-a-run").mkdir()
    assert reader.read_sampling_folder(str(tmp_path)).data is None or \
        reader.read_sampling_folder(str(tmp_path)).data.empty


def test_chain_and_draw_are_not_invented_when_the_file_has_them(tmp_path):
    """A file that already carries the columns keeps its own values."""
    path = tmp_path / "chains" / "run_0.er4"
    path.parent.mkdir(parents=True)
    frame = pd.DataFrame({
        "chi2r": [1.0, 1.1], "lnprior": [0.0, 0.0],
        "c": [2.0, 2.1], "chain": [7, 7], "draw": [100, 101],
    })
    frame.to_csv(path, sep="\t", index=False)
    data = reader.read_sampling_folder(str(tmp_path)).data
    assert data["chain"].tolist() == [7, 7]
    assert data["draw"].tolist() == [100, 101]


def test_a_partial_chain_is_not_counted_twice(tmp_path):
    """``<name>.partial.er4`` is a prefix of ``<name>.er4``, not another chain.

    A run writes the partial as it goes and deletes it on success. If the delete
    does not happen, reading both counts those draws twice and shows them as two
    chains that agree suspiciously well -- the one comparison that is supposed
    to reveal disagreement.
    """
    run = tmp_path / "2026-07-28_10-00-00"
    write_chain(run / "chains" / "Fit_0.er4", n_draws=25, seed=1)
    write_chain(run / "chains" / "Fit_0.partial.er4", n_draws=12, seed=1)

    data = reader.read_sampling_folder(str(tmp_path)).data
    assert len(data) == 25
    assert sorted(data["chain"].unique()) == [0]


def test_a_cancelled_run_is_still_read(tmp_path):
    """With no finished chain beside it, the partial is all there is."""
    run = tmp_path / "2026-07-28_10-00-00"
    write_chain(run / "chains" / "Fit_0.er4", n_draws=25, seed=1)
    write_chain(run / "chains" / "Fit_1.partial.er4", n_draws=10, seed=2)

    data = reader.read_sampling_folder(str(tmp_path)).data
    assert len(data) == 35
    assert sorted(data["chain"].unique()) == [0, 1]


def test_a_file_that_is_not_a_chain_is_skipped_and_said_so(tmp_path, caplog):
    """A chain missing from a posterior is a posterior that is quietly wrong.

    It must also not contribute a column of its own: concatenation would give
    every other chain a missing value there, and the fill would invent draws
    that were never sampled.
    """
    run = tmp_path / "2026-07-28_10-00-00"
    write_chain(run / "chains" / "Fit_0.er4", n_draws=20, seed=1)
    (run / "chains" / "Fit_1.er4").write_text("this is not a chain\n")

    with caplog.at_level("WARNING"):
        data = reader.read_sampling_folder(str(tmp_path)).data
    assert len(data) == 20
    assert list(data.columns) == ["chi2r", "lnprior", "c", "a", "chain", "draw"]
    assert "read 1 of 2 sampling chains" in caplog.text


def test_chains_of_different_parameters_are_not_merged(tmp_path):
    """Two fits' chains in one folder are not one posterior.

    Filling the difference would fabricate draws for parameters the other run
    never sampled.
    """
    run = tmp_path / "2026-07-28_10-00-00"
    write_chain(run / "chains" / "Fit_0.er4", n_draws=20, seed=1)
    with open(run / "chains" / "Other_0.er4", "w") as f:
        f.write("# chi2r\tlnprior\tx\ty\tz\n")
        for _ in range(20):
            f.write("1.0\t0.0\t1.0\t2.0\t3.0\n")

    data = reader.read_sampling_folder(str(tmp_path)).data
    assert len(data) == 20
    assert "z" not in data.columns
    assert not data.isna().any().any()


def write_hdf5_chain(path, n_draws=20, offset=0.0, seed=0):
    """Write one chain as the HDF5 table ChiSurf's ``hdf5`` format produces."""
    pytest.importorskip("tables")
    rng = np.random.default_rng(seed)
    frame = pd.DataFrame({
        "chi2r": rng.normal(1.0, 0.01, n_draws),
        "lnprior": np.zeros(n_draws),
        "c": rng.normal(2.0 + offset, 0.1, n_draws),
        "a": rng.normal(0.5, 0.01, n_draws),
    })
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_hdf(path, key="results", mode="w", format="table",
                 complib="zlib", complevel=5)


def test_chains_stored_as_hdf5_open_like_text_ones(tmp_path):
    """The storage format is not supposed to be visible on the other side."""
    run = tmp_path / "2026-07-28_10-00-00"
    for i in range(3):
        write_hdf5_chain(run / "chains" / f"Fit_{i}.h5", n_draws=20, seed=i)

    data = reader.read_sampling_folder(str(tmp_path)).data
    assert len(data) == 60
    assert list(data.columns) == ["chi2r", "lnprior", "c", "a", "chain", "draw"]
    assert sorted(data["chain"].unique()) == [0, 1, 2]
    assert np.isclose(data["a"].mean(), 0.5, atol=0.05)


def test_a_partial_hdf5_chain_is_not_counted_twice(tmp_path):
    """The partial/final rule is about the run, not about the file format."""
    run = tmp_path / "2026-07-28_10-00-00"
    write_hdf5_chain(run / "chains" / "Fit_0.h5", n_draws=25, seed=1)
    write_hdf5_chain(run / "chains" / "Fit_0.partial.h5", n_draws=12, seed=1)

    data = reader.read_sampling_folder(str(tmp_path)).data
    assert len(data) == 25
    assert sorted(data["chain"].unique()) == [0]


# --- ensemble-sampler chains stored in HDF5 --------------------------------

def write_sampling_hdf5(path, n_steps=4, n_walkers=6, names=("a", "b", "c"),
                        allocated=None, names_payload=None):
    """Write an ensemble-sampler chain in the layout ucfret's backend produces.

    ``allocated`` grows the datasets beyond the steps actually written, which is
    what a thinned run leaves behind: the tail rows are zeros, not draws.
    """
    h5py = pytest.importorskip("h5py")
    import pickle

    n_dim = len(names)
    allocated = n_steps if allocated is None else allocated
    rng = np.random.default_rng(0)
    chain = np.zeros((allocated, n_walkers, n_dim))
    chain[:n_steps] = rng.normal(1.0, 0.1, (n_steps, n_walkers, n_dim))
    log_prob = np.zeros((allocated, n_walkers))
    log_prob[:n_steps] = rng.normal(-100.0, 1.0, (n_steps, n_walkers))

    with h5py.File(path, "w") as f:
        mcmc = f.create_group("mcmc")
        mcmc.create_dataset("chain", data=chain)
        mcmc.create_dataset("log_prob", data=log_prob)
        mcmc.attrs["iteration"] = n_steps
        mcmc.attrs["ndim"] = n_dim
        mcmc.attrs["nwalkers"] = n_walkers
        blobs = f.create_group("blobs")
        payload = pickle.dumps(list(names)) if names_payload is None else names_payload
        blobs.attrs["parameter_names"] = np.void(payload)
    return chain[:n_steps]


def test_a_sampling_hdf5_is_recognised(tmp_path):
    """It must not be read as a table of bursts."""
    path = tmp_path / "run.hdf"
    write_sampling_hdf5(path)
    assert reader.is_ensemble_sampling_hdf5(str(path))
    assert not reader.is_ensemble_sampling_hdf5(str(tmp_path / "missing.hdf"))


def test_every_draw_becomes_a_row_that_knows_its_walker_and_step(tmp_path):
    """Walkers are the chains of an ensemble sampler."""
    path = tmp_path / "run.hdf"
    write_sampling_hdf5(path, n_steps=4, n_walkers=6, names=("a", "b", "c"))
    data = reader.read_ensemble_sampling_hdf5(str(path)).data

    assert len(data) == 4 * 6
    assert list(data.columns) == ["a", "b", "c", "log_prob", "chain", "draw"]
    assert sorted(data["chain"].unique()) == list(range(6))
    assert sorted(data["draw"].unique()) == list(range(4))
    # Every (walker, step) pair appears exactly once.
    assert len(data.groupby(["chain", "draw"])) == 24


def test_the_unwritten_tail_of_a_thinned_run_is_not_returned(tmp_path):
    """Storage is grown in whole chunks; a zero row is not a draw."""
    path = tmp_path / "run.hdf"
    write_sampling_hdf5(path, n_steps=3, n_walkers=4, allocated=10)
    data = reader.read_ensemble_sampling_hdf5(str(path)).data
    assert len(data) == 3 * 4
    assert (data["log_prob"] != 0.0).all()


def test_opening_a_file_never_runs_what_the_file_asks_for(tmp_path):
    """Metadata is pickled, so the reader must refuse to resolve any class.

    A pickle that reaches for a global is not metadata; the names fall back to
    positional ones and the chain still opens.
    """
    import pickle

    class _Reaching:
        """Pickles as a call to a global, which the reader must refuse."""

        def __reduce__(self):
            return (eval, ("1 + 1",))

    path = tmp_path / "hostile.hdf"
    write_sampling_hdf5(path, n_steps=2, n_walkers=4, names=("a", "b"),
                        names_payload=pickle.dumps(_Reaching()))
    data = reader.read_ensemble_sampling_hdf5(str(path)).data
    assert list(data.columns)[:2] == ["p0", "p1"]
    assert len(data) == 8


def test_several_sampling_files_keep_their_chains_apart(tmp_path):
    """Stacked files must not collide on walker index 0."""
    for i in range(2):
        write_sampling_hdf5(tmp_path / f"run{i}.hdf", n_steps=3, n_walkers=5)
    data = reader.read_ensemble_sampling_hdf5(
        [str(tmp_path / "run0.hdf"), str(tmp_path / "run1.hdf")]
    ).data
    assert len(data) == 2 * 3 * 5
    assert sorted(data["chain"].unique()) == list(range(10))


def test_the_hdf5_entry_point_routes_a_chain_to_the_sampling_reader(tmp_path):
    """The user opens an HDF5; which kind it is, is the reader's problem."""
    path = tmp_path / "run.hdf"
    write_sampling_hdf5(path, n_steps=3, n_walkers=4, names=("a", "b"))
    data = reader.read_mfd_hdf5([str(path)]).data
    assert len(data) == 12
    assert {"chain", "draw", "log_prob"} <= set(data.columns)
