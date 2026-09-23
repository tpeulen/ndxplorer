"""LUT and color management functionality for NDXplorer.

This module provides colormap management, LUT operations, and color
mapping utilities extracted from plot_main.py.
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Union
import numpy as np

from ..logging_config import logging

if False:  # pragma: no cover - type checking hints without runtime import
    from ..core.plot_main import NDXplorer

try:
    import pyqtgraph as pg
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False
    pg = None
    logging.warning("pyqtgraph not available, colormap functionality limited")


def get_available_colormaps() -> List[str]:
    """The colormap names (see :mod:`.colormap_lut`, which reads them without Qt)."""
    from .colormap_lut import available_colormaps

    return list(available_colormaps())


def create_colormap_lut(
    colormap_name: str,
    n_colors: int = 256,
    gamma: float = 1.0
) -> np.ndarray:
    """``(n_colors, 4)`` uint8 RGBA lookup table; see :func:`.colormap_lut.lookup_table`."""
    from .colormap_lut import lookup_table

    return lookup_table(colormap_name, n_colors, gamma)


def apply_colormap_to_data(
    data: np.ndarray,
    colormap_name: str = "viridis",
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    gamma: float = 1.0
) -> np.ndarray:
    """Colour a 2-D array as ``(h, w, 4)`` uint8 RGBA; see :func:`.colormap_lut.apply_colormap`."""
    from .colormap_lut import apply_colormap

    return apply_colormap(data, colormap_name, vmin, vmax, gamma)


def get_colormap_limits(
    data: np.ndarray,
    percentile_range: Tuple[float, float] = (1.0, 99.0)
) -> Tuple[float, float]:
    """
    Compute optimal colormap limits for data.
    
    Args:
        data: Input data array
        percentile_range: Percentile range for auto-scaling
        
    Returns:
        Tuple of (vmin, vmax)
    """
    if data.size == 0:
        return 0.0, 1.0
    
    # Remove NaN/Inf values
    finite_data = data[np.isfinite(data)]
    
    if finite_data.size == 0:
        return 0.0, 1.0
    
    if percentile_range == (0, 100):
        vmin, vmax = np.min(finite_data), np.max(finite_data)
    else:
        vmin = np.percentile(finite_data, percentile_range[0])
        vmax = np.percentile(finite_data, percentile_range[1])
    
    # Ensure vmin < vmax
    if vmin == vmax:
        vmin = vmin - 0.5
        vmax = vmax + 0.5
    
    return float(vmin), float(vmax)


def create_custom_colormap(
    colors: List[Union[str, Tuple[float, float, float]]],
    name: str = "custom",
    positions: Optional[List[float]] = None
) -> str:
    """
    Create custom colormap from list of colors.
    
    Args:
        colors: List of color names or RGB tuples
        name: Name for the custom colormap
        positions: Optional positions for colors (0-1)
        
    Returns:
        Name of the created colormap
    """
    try:
        if positions is None:
            positions = np.linspace(0, 1, len(colors))

        rgb_colors = []
        for color in colors:
            if isinstance(color, str):
                qcolor = pg.mkColor(color) if PYQTGRAPH_AVAILABLE else None
                if qcolor is None:
                    raise ValueError(f"Named color requires pyqtgraph: {color}")
                rgb_colors.append((qcolor.red(), qcolor.green(), qcolor.blue(), qcolor.alpha()))
            else:
                rgb = tuple(color)
                if max(rgb) <= 1.0:
                    rgb = tuple(int(component * 255) for component in rgb)
                rgb_colors.append(rgb)

        pg.colormap.ColorMap(np.asarray(positions, dtype=float), np.asarray(rgb_colors, dtype=np.ubyte))
        return name

    except Exception:
        logging.warning("pyqtgraph not available, custom colormap creation failed")
        return "viridis"


def current_cmap(ndxplorer: "NDXplorer") -> str:
    """Get current colormap name from combobox."""
    if hasattr(ndxplorer, 'comboBoxCmap'):
        return ndxplorer.comboBoxCmap.currentText()
    return "viridis"  # fallback


def populate_colormap_combobox(ndxplorer: "NDXplorer") -> None:
    """
    Populate colormap combobox with available colormaps.
    
    Args:
        ndxplorer: NDXplorer instance with comboBoxCmap attribute
    """
    if not hasattr(ndxplorer, 'comboBoxCmap'):
        logging.warning("NDXplorer instance missing comboBoxCmap")
        return
    
    colormap_names = get_available_colormaps()
    logging.debug(f"Found {len(colormap_names)} colormaps")
    
    # Clear existing items
    ndxplorer.comboBoxCmap.clear()
    
    # Add colormaps
    ndxplorer.comboBoxCmap.addItems(colormap_names)
    
    # Set default if available
    default_cmap = "viridis"
    if default_cmap in colormap_names:
        index = colormap_names.index(default_cmap)
        ndxplorer.comboBoxCmap.setCurrentIndex(index)
        logging.info(f"Set default colormap to {default_cmap}")


def update_colormap(ndxplorer: "NDXplorer", colormap_name: Optional[str] = None) -> bool:
    """Update the colormap of the 2D plot image item."""
    try:
        if not getattr(ndxplorer, "_deferred_init_done", False) or ndxplorer.g_2dplot is None:
            logging.debug("Plot not ready for colormap update")
            return False

        if colormap_name is None:
            colormap_name = current_cmap(ndxplorer)

        vmin = getattr(ndxplorer, "vmin", 0.0)
        vmax = getattr(ndxplorer, "vmax", 1.0)
        ndxplorer.cax.set_colormap(colormap_name, vmin, vmax)
        ndxplorer.g_2dplot.replot()
        logging.debug("Updated pyqtgraph colormap to %s", colormap_name)
        return True

    except Exception as e:
        logging.error(f"Failed to update colormap: {e}")
        return False


update_guiqwt_colormap = update_colormap


def get_colormap_statistics(
    colored_data: np.ndarray
) -> dict:
    """
    Compute statistics for colored/image data.
    
    Args:
        colored_data: RGBA image array
        
    Returns:
        Dictionary containing color statistics
    """
    if colored_data.ndim != 3 or colored_data.shape[2] != 4:
        raise ValueError("Data must be RGBA image array")
    
    # Separate channels
    r, g, b, a = colored_data[:, :, 0], colored_data[:, :, 1], colored_data[:, :, 2], colored_data[:, :, 3]
    
    stats = {
        "shape": colored_data.shape,
        "red_mean": np.mean(r),
        "green_mean": np.mean(g),
        "blue_mean": np.mean(b),
        "alpha_mean": np.mean(a),
        "red_std": np.std(r),
        "green_std": np.std(g),
        "blue_std": np.std(b),
        "alpha_std": np.std(a)
    }
    
    return stats


def set_default_colormap(ndxplorer: "NDXplorer", default_cmap: str) -> None:
    """
    Set default colormap in combobox and update plot if ready.
    
    Args:
        ndxplorer: NDXplorer instance
        default_cmap: Name of default colormap
    """
    logging.info(f"Setting default colormap to {default_cmap}")
    
    if not hasattr(ndxplorer, 'comboBoxCmap'):
        logging.warning("NDXplorer instance missing comboBoxCmap")
        return
    
    index = ndxplorer.comboBoxCmap.findText(default_cmap)
    if index == -1:
        logging.info(f"Colormap {default_cmap} not found in available colormaps")
        return
    
    ndxplorer.comboBoxCmap.setCurrentIndex(index)
    
    if getattr(ndxplorer, "_deferred_init_done", False) and hasattr(ndxplorer, 'cax') and ndxplorer.cax is not None:
        vmin = getattr(ndxplorer, 'vmin', 0.0)
        vmax = getattr(ndxplorer, 'vmax', 1.0)
        ndxplorer.cax.set_colormap(default_cmap, vmin, vmax)
        if hasattr(ndxplorer, 'g_2dplot') and ndxplorer.g_2dplot is not None:
            ndxplorer.g_2dplot.replot()
