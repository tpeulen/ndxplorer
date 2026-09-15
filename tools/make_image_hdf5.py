#!/usr/bin/env python3
"""Build an MFIS-style image table from a CLSM measurement, for testing ndXplorer.

The imaging path in ndXplorer -- the pixel axes, the frame slider, the parameter
map, the ROI gate -- had no realistic test data. The fixture in ``test_cli.py``
is four pixels, which is enough to check that a TIFF comes out and nothing at
all about whether the program is usable on a real image.

This makes the real thing out of a confocal TTTR measurement: one row per
illuminated pixel per frame, carrying what a multiparameter fluorescence image
actually carries -- photon counts per detection channel, a mean micro time per
pixel, phasor coordinates, and the ratios derived from them. Roughly a million
rows from a 256 x 256 x 40 stack, which is the size at which the interactive
paths either work or do not.

Usage::

    python tools/make_image_hdf5.py --out image_test.h5
    python tools/make_image_hdf5.py --file my.ptu --green 0 1 --red 4 5

Then in ndXplorer::

    ndx image --file image_test.h5 --map "Tau (green)" --out tau.tiff
    ndx image --file image_test.h5 --map intensity --select "Number of Photons:20-" --out i.png

or open ``image_test.h5`` in the GUI: the pixel columns are named so the imaging
axes are detected, and ``Frame`` drives the frame slider.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np
import pandas as pd
import tttrlib

#: The CLSM measurement this was written against: 40 frames, 256 x 256, two
#: detection channels per colour. Roughly 15 million photons.
DEFAULT_FILE = ("/Users/tpeulen/dev/tttr-data/imaging/pq/ht3/pq_ht3_clsm.ht3")

#: A pixel needs at least this many photons for a mean micro time to mean
#: anything. Below it the value is left at zero by tttrlib and dropped to NaN
#: here -- which is the point: a real parameter map is full of holes, and a test
#: file without them does not test the paths that handle them.
MIN_PHOTONS = 3


def channel_image(tttr, channels, n_frames_max=None):
    """``(counts, mean_micro_time, phasor)`` per pixel for one detection colour."""
    image = tttrlib.CLSMImage(tttr, fill=False)
    image.fill(tttr, list(channels))
    counts = np.asarray(image.get_intensity()).astype(np.int32)
    micro = np.asarray(image.get_mean_micro_time(
        tttr, minimum_number_of_photons=MIN_PHOTONS))
    phasor = np.asarray(image.get_phasor(
        tttr, minimum_number_of_photons=MIN_PHOTONS))
    if n_frames_max is not None:
        counts, micro, phasor = (counts[:n_frames_max], micro[:n_frames_max],
                                 phasor[:n_frames_max])
    return counts, micro, phasor


def build(path, green, red, n_frames_max=None, min_total=1):
    """The per-pixel table, as a DataFrame."""
    tttr = tttrlib.TTTR(str(path))
    print(f"read {len(tttr):,} photons from {pathlib.Path(path).name}")

    ng, tg, pg = channel_image(tttr, green, n_frames_max)
    nr, tr, pr = channel_image(tttr, red, n_frames_max)
    n_frames, n_lines, n_pixels = ng.shape
    print(f"image stack {n_frames} x {n_lines} x {n_pixels}")

    frame, y, x = np.indices(ng.shape)
    total = ng + nr
    keep = (total >= min_total).ravel()

    def column(a):
        return a.ravel()[keep]

    def as_lifetime(a):
        """Mean micro time in nanoseconds, with the discriminated pixels NaN.

        tttrlib fills a pixel it could not evaluate with zero. Left as zero it
        would be a lifetime of zero -- a real value, in the middle of a real
        axis, that a gate would happily select. NaN is the honest answer and is
        what the store treats as "not measured".
        """
        out = column(a) * 1e9
        out[out <= 0.0] = np.nan
        return out

    def as_phasor(component, micro):
        """A phasor coordinate, NaN where the pixel had too few photons.

        The discrimination is read off the MEAN MICRO TIME, not off the phasor
        value: tttrlib fills a discriminated phasor pixel with -1, which is a
        perfectly ordinary coordinate for a pixel that was measured, so testing
        the value itself would throw away real data at the edge of the circle.
        """
        out = column(component)
        out[column(micro) <= 0.0] = np.nan
        return out

    with np.errstate(divide="ignore", invalid="ignore"):
        sg, sr = column(ng).astype(float), column(nr).astype(float)
        proximity = np.where(sg + sr > 0, sr / (sg + sr), np.nan)
        ratio = np.where(sr > 0, sg / sr, np.nan)

    frame_index = column(frame).astype(np.int32)
    table = pd.DataFrame({
        # ndXplorer finds the imaging axes by name, case-insensitively.
        "x pixel": column(x).astype(np.int32),
        "y pixel": column(y).astype(np.int32),
        "Frame": frame_index,
        "Number of Photons (green)": column(ng),
        "Number of Photons (red)": column(nr),
        "Number of Photons": column(total),
        "Tau (green)": as_lifetime(tg),
        "Tau (red)": as_lifetime(tr),
        "g (green)": as_phasor(pg[..., 0], tg),
        "s (green)": as_phasor(pg[..., 1], tg),
        "Proximity Ratio": proximity,
        "Sg/Sr": ratio,
    })
    # A per-frame timestamp, so the frame slider has something continuous to
    # show alongside the index.
    duration = tttr.header.macro_time_resolution * len(tttr) / max(n_frames, 1)
    table["Frame Time (s)"] = frame_index * duration
    return table


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--file", default=DEFAULT_FILE,
                        help="CLSM TTTR measurement (.ht3, .ptu, ...)")
    parser.add_argument("--out", default="image_test.h5", help="HDF5 to write")
    parser.add_argument("--green", type=int, nargs="+", default=[0, 1],
                        help="routing channels of the green detectors")
    parser.add_argument("--red", type=int, nargs="+", default=[4, 5],
                        help="routing channels of the red detectors")
    parser.add_argument("--frames", type=int, default=None,
                        help="keep only the first N frames")
    parser.add_argument("--min-photons", type=int, default=1,
                        help="drop pixels with fewer photons than this in total")
    args = parser.parse_args(argv)

    table = build(args.file, args.green, args.red, args.frames, args.min_photons)
    out = pathlib.Path(args.out)

    # A columnar HDF5 -- one dataset per column -- rather than a pandas table.
    # That is the layout a DataStore already has, so ndXplorer reads it with
    # tttrlib.read_hdf5 straight into the store it evaluates gates and fills
    # histograms in: no DataFrame in between, no second copy of the table at the
    # moment it is largest, and every column keeps the type it was written as.
    store = tttrlib.DataStore(out.stem)
    store.set_n_rows(len(table))
    for name in table.columns:
        column = store.add(name, table[name].to_numpy())
        if table[name].dtype.kind == "f":
            # A pixel with too few photons has no lifetime. Saying so with the
            # column's own validity bit is what keeps it out of a gate and out
            # of a histogram, rather than binning it at whatever NaN casts to.
            column.mask_non_finite()
    tttrlib.write_hdf5(str(out), store)

    print(f"wrote {len(table):,} rows x {table.shape[1]} columns to {out} "
          f"({out.stat().st_size / 1e6:.1f} MB)")
    print(table.describe().T[["count", "mean", "min", "max"]].to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
