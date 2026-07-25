"""Unit tests for histogram plotting functionality."""

import pytest
import numpy as np
from unittest.mock import Mock, patch

from ndxplorer.plotting import histograms
from ndxplorer.core.histograms import Histogram1D, Histogram2D


class TestHistograms:
    """Test histogram plotting functions."""

    @patch('ndxplorer.plotting.histograms.is_data_ready', return_value=True)
    def test_plot_histogram_2d(self, _ready):
        """Test 2D histogram plotting from the (H, x_edges, y_edges) tuple form."""
        ndxplorer = Mock()
        ndxplorer._histogram = {
            "2d": (np.array([[1, 2], [3, 4]]), np.array([0, 1, 2]), np.array([0, 1, 2]))
        }

        H, (x_edges, y_edges) = histograms.plot_histogram(ndxplorer, "2d")

        assert np.array_equal(H, np.array([[1, 2], [3, 4]]))
        assert np.array_equal(x_edges, np.array([0, 1, 2]))
        assert np.array_equal(y_edges, np.array([0, 1, 2]))

    @patch('ndxplorer.plotting.histograms.is_data_ready', return_value=True)
    def test_plot_histogram_1d(self, _ready):
        """Test 1D histogram plotting from the (edges, counts) tuple form."""
        ndxplorer = Mock()
        ndxplorer._histogram = {
            "x": (np.array([0, 1, 2, 3]), np.array([5, 10, 15]))
        }

        bin_edges, counts = histograms.plot_histogram(ndxplorer, "x")

        assert np.array_equal(bin_edges, np.array([0, 1, 2, 3]))
        assert np.array_equal(counts, np.array([5, 10, 15]))

    @patch('ndxplorer.plotting.histograms.is_data_ready', return_value=True)
    def test_plot_histogram_1d_object_form(self, _ready):
        """plot_histogram accepts a Histogram1D object as well as a tuple."""
        ndxplorer = Mock()
        ndxplorer._histogram = {
            "x": Histogram1D(edges=np.array([0, 1, 2, 3]), counts=np.array([5, 10, 15]))
        }

        bin_edges, counts = histograms.plot_histogram(ndxplorer, "x")

        assert np.array_equal(bin_edges, np.array([0, 1, 2, 3]))
        assert np.array_equal(counts, np.array([5, 10, 15]))

    @patch('ndxplorer.plotting.histograms.is_data_ready', return_value=True)
    def test_plot_histogram_2d_object_form(self, _ready):
        """plot_histogram accepts a Histogram2D object as well as a tuple."""
        ndxplorer = Mock()
        ndxplorer._histogram = {
            "2d": Histogram2D(
                H=np.array([[1, 2], [3, 4]]),
                x_edges=np.array([0, 1, 2]),
                y_edges=np.array([0, 1, 2]),
            )
        }

        H, (x_edges, y_edges) = histograms.plot_histogram(ndxplorer, "2d")

        assert np.array_equal(H, np.array([[1, 2], [3, 4]]))
        assert np.array_equal(x_edges, np.array([0, 1, 2]))
        assert np.array_equal(y_edges, np.array([0, 1, 2]))

    @patch('ndxplorer.plotting.histograms.is_data_ready', return_value=True)
    def test_plot_histogram_invalid_dimension(self, _ready):
        """Test histogram plotting with invalid dimension."""
        ndxplorer = Mock()
        ndxplorer._histogram = {}

        bin_edges, counts = histograms.plot_histogram(ndxplorer, "invalid")

        assert np.array_equal(bin_edges, np.array([0, 1]))
        assert np.array_equal(counts, np.array([0]))

    def test_compute_2d_histogram_basic(self):
        """compute_2d_histogram returns a Histogram2D."""
        ndxplorer = Mock()
        x_data = np.array([1, 2, 3, 4])
        y_data = np.array([1, 2, 3, 4])

        hist = histograms.compute_2d_histogram(
            ndxplorer, x_data, y_data, 3, 3
        )

        assert isinstance(hist, Histogram2D)
        assert hist.H.shape == (3, 3)  # bins=3 -> 3 bins, 4 edges
        assert len(hist.x_edges) == 4
        assert len(hist.y_edges) == 4

    def test_compute_2d_histogram_with_weights(self):
        """compute_2d_histogram honours weights."""
        ndxplorer = Mock()
        x_data = np.array([1, 2, 3, 4])
        y_data = np.array([1, 2, 3, 4])
        weights = np.array([1, 2, 1, 2])

        hist = histograms.compute_2d_histogram(
            ndxplorer, x_data, y_data, 3, 3, weights=weights
        )

        assert isinstance(hist, Histogram2D)
        assert hist.H.shape == (3, 3)
        assert np.sum(hist.H) == np.sum(weights)

    def test_compute_1d_histogram_basic(self):
        """compute_1d_histogram returns a Histogram1D."""
        ndxplorer = Mock()
        data = np.array([1, 2, 3, 4, 5])

        hist = histograms.compute_1d_histogram(
            ndxplorer, data, 5
        )

        assert isinstance(hist, Histogram1D)
        assert len(hist.counts) == 5
        assert len(hist.edges) == 6
        assert np.sum(hist.counts) == len(data)

    def test_compute_1d_histogram_with_weights(self):
        """compute_1d_histogram honours weights."""
        ndxplorer = Mock()
        data = np.array([1, 2, 3, 4, 5])
        weights = np.array([1, 2, 1, 2, 1])

        hist = histograms.compute_1d_histogram(
            ndxplorer, data, 5, weights=weights
        )

        assert isinstance(hist, Histogram1D)
        assert len(hist.counts) == 5
        assert np.sum(hist.counts) == np.sum(weights)

    def test_get_histogram_statistics_2d(self):
        """Test statistics computation for 2D histogram."""
        ndxplorer = Mock()
        ndxplorer._histogram = {
            "2d": (np.array([[1, 2], [3, 4]]), np.array([0, 1, 2]), np.array([0, 1, 2]))
        }
        
        stats = histograms.get_histogram_statistics(ndxplorer, "2d")
        
        assert stats["count"] == 10
        assert stats["mean"] == 2.5
        assert stats["shape"] == (2, 2)
        assert "min" in stats
        assert "max" in stats

    def test_get_histogram_statistics_1d(self):
        """Statistics for a 1D histogram in (edges, counts) tuple form."""
        ndxplorer = Mock()
        ndxplorer._histogram = {
            # (edges, counts): 3 counts summing to 30.
            "x": (np.array([0, 1, 2, 3]), np.array([5, 10, 15]))
        }

        stats = histograms.get_histogram_statistics(ndxplorer, "x")

        assert stats["count"] == 30
        assert stats["mean"] == 10.0
        assert stats["bins"] == 3

    def test_get_histogram_statistics_1d_object_form(self):
        """Statistics accept a Histogram1D object too."""
        ndxplorer = Mock()
        ndxplorer._histogram = {
            "x": Histogram1D(edges=np.array([0, 1, 2, 3]), counts=np.array([5, 10, 15]))
        }

        stats = histograms.get_histogram_statistics(ndxplorer, "x")

        assert stats["count"] == 30
        assert stats["mean"] == 10.0
        assert stats["bins"] == 3

    def test_get_histogram_statistics_invalid(self):
        """Test statistics computation with invalid data."""
        ndxplorer = Mock()
        ndxplorer._histogram = {}
        
        stats = histograms.get_histogram_statistics(ndxplorer, "invalid")
        
        assert stats == {}

    # update_histograms and extract_histogram_params are imported *locally*
    # inside update_histogram_display (to dodge circular imports), so the
    # patches must target their source modules, not the histograms namespace.
    @patch('ndxplorer.plotting.plot_update_helpers.update_histograms')
    @patch('ndxplorer.plotting.histograms.should_recompute', return_value=True)
    @patch('ndxplorer.utils.histogram_helpers.extract_histogram_params',
           return_value=(Mock(), {}))
    @patch('ndxplorer.plotting.histograms.is_data_ready', return_value=True)
    def test_update_histogram_display_ready(self, _ready, _extract, _recompute, mock_update):
        """update_histogram_display triggers a recompute when data is ready."""
        ndxplorer = Mock()
        histograms.update_histogram_display(ndxplorer)

        mock_update.assert_called_once_with(ndxplorer)

    @patch('ndxplorer.plotting.plot_update_helpers.update_histograms')
    @patch('ndxplorer.plotting.histograms.is_data_ready', return_value=False)
    def test_update_histogram_display_not_ready(self, _ready, mock_update):
        """update_histogram_display does nothing when data is not ready."""
        ndxplorer = Mock()
        histograms.update_histogram_display(ndxplorer)

        mock_update.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__])
