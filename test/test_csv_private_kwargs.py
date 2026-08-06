"""Guard: the reader-choice flags never reach pandas.

``_detect_and_build_kwargs`` mixes two things into one dict — arguments for the
CSV reader, and the decision about *which* reader a file gets (``_tttrlib``).
The second kind is prefixed and must be dropped before the dict is splatted.

It was not, in ``read_csv_file``, and the failure is the quiet kind: pandas
raises ``unexpected keyword argument '_tttrlib'``, every caller catches that as
"could not read this file", and an ordinary comma-delimited file with a header
on the first line — which is exactly the shape the flag is set for — reads as an
empty table with nothing but a warning in the log.
"""

from __future__ import annotations

import pandas as pd

from ndxplorer.io import reader


def _write(path, text: str):
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_a_plain_comma_file_with_a_header_actually_reads(tmp_path):
    """The shape that sets the flag. It has to come back with its rows."""
    path = _write(tmp_path / "plain.csv", "a,b,c\n1,2,3\n4,5,6\n")
    frame = reader.read_csv_file(path)
    assert list(frame.columns) == ["a", "b", "c"]
    assert len(frame) == 2


def test_the_detected_kwargs_carry_a_private_flag(tmp_path):
    """If this stops being true the test above stops testing anything."""
    kwargs = reader._detect_and_build_kwargs(["a,b,c", "1,2,3"])
    assert any(k.startswith("_") for k in kwargs), (
        "no private key left to strip -- the guard below is now vacuous"
    )


def test_private_keys_are_stripped_and_the_rest_survive():
    kwargs = {"sep": ",", "header": 0, "_tttrlib": True}
    assert reader._pandas_kwargs(kwargs) == {"sep": ",", "header": 0}


def test_stripping_does_not_consume_the_flag():
    """The dict is cached and reused for every further file of one format, so
    popping the flag would send all but the first through the other reader."""
    kwargs = {"sep": ",", "_tttrlib": True}
    reader._pandas_kwargs(kwargs)
    assert kwargs["_tttrlib"] is True


def test_a_zipped_csv_reads_too(tmp_path):
    """The other unstripped call site."""
    import zipfile

    inner = tmp_path / "inner.csv"
    _write(inner, "x,y\n1,2\n3,4\n")
    archive = tmp_path / "bundle.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.write(inner, "inner.csv")

    frame = reader.read_csv_file(str(archive))
    assert list(frame.columns) == ["x", "y"]
    assert len(frame) == 2
