from .data_source import DataSource, DataSelection, RectangularDataSelection, Gaussian2DSelection
from .histograms import Histogram1D, Histogram2D, Histogram3D
from ..utils.histogram_computation import Axis, HistogramAxes

__all__ = [
    'DataSource',
    'DataSelection',
    'RectangularDataSelection',
    'Gaussian2DSelection',
    'NDXplorer',
    'Histogram1D',
    'Histogram2D',
    'Histogram3D',
    'Axis',
    'HistogramAxes',
]


def __getattr__(name: str):
    """The Qt window, loaded on first use so the data layer imports without Qt."""
    if name == "NDXplorer":
        from .plot_main import NDXplorer

        return NDXplorer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
