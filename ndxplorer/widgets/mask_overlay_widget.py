"""
Transparent overlay widget for drawing masks on the 2D plot.
"""
from typing import Optional
import numpy as np

try:
    from chisurf.gui import QtCore, QtGui, QtWidgets
except ImportError:
    from qtpy import QtCore, QtGui, QtWidgets


class MaskOverlayWidget(QtWidgets.QWidget):
    """
    Transparent widget that overlays the 2D plot for mask visualization.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Make widget transparent
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        
        # Enable mouse tracking for cursor preview
        self.setMouseTracking(True)
        
        # Store mask data, and the RGBA image drawn from it
        self._mask = None
        self._rgba = None
        self._image = None
        self._xedges = None
        self._yedges = None
        
        # Cursor preview
        self._cursor_pos = None
        self._brush_radius = 5
        self._show_cursor = False
        
        # Color map for different classes
        self._colors = [
            QtGui.QColor(255, 0, 0, 100),      # Class 1: Red
            QtGui.QColor(0, 255, 0, 100),      # Class 2: Green
            QtGui.QColor(0, 0, 255, 100),      # Class 3: Blue
            QtGui.QColor(255, 255, 0, 100),    # Class 4: Yellow
            QtGui.QColor(255, 0, 255, 100),    # Class 5: Magenta
            QtGui.QColor(0, 255, 255, 100),    # Class 6: Cyan
            QtGui.QColor(255, 128, 0, 100),    # Class 7: Orange
            QtGui.QColor(128, 0, 255, 100),    # Class 8: Purple
        ]
    
    def _mask_image(self):
        """The mask as an RGBA QImage.

        Rebuilt on every paint rather than cached: the brush writes into the
        mask array in place, so a cache keyed on the array would keep showing
        the stroke before last. Colouring a 256 x 256 mask is a single numpy
        indexing pass over a quarter of a megabyte, which is not what makes a
        redraw slow.

        The QImage borrows the numpy buffer, so the array is kept on the widget
        rather than left to be collected the moment this returns.
        """
        if self._mask is None:
            return None

        classes = self._mask.astype(np.intp, copy=False)
        rgba = np.zeros(classes.shape + (4,), dtype=np.uint8)
        painted = classes > 0
        if painted.any():
            table = np.array([[c.red(), c.green(), c.blue(), c.alpha()]
                              for c in self._colors], dtype=np.uint8)
            rgba[painted] = table[(classes[painted] - 1) % len(self._colors)]

        self._rgba = np.ascontiguousarray(rgba)
        ny, nx = classes.shape
        self._image = QtGui.QImage(self._rgba.data, nx, ny, 4 * nx,
                                   QtGui.QImage.Format_RGBA8888)
        return self._image

    def set_mask(self, mask: Optional[np.ndarray], xedges: Optional[np.ndarray] = None, yedges: Optional[np.ndarray] = None):
        """
        Set the mask to display.
        
        Parameters
        ----------
        mask : Optional[np.ndarray]
            Integer mask with class labels (H, W) or (ny, nx)
        xedges : Optional[np.ndarray]
            X bin edges
        yedges : Optional[np.ndarray]
            Y bin edges
        """
        self._mask = mask
        self._xedges = xedges
        self._yedges = yedges
        self.update()
    
    def clear_mask(self):
        """Clear the mask overlay."""
        self._mask = None
        self._xedges = None
        self._yedges = None
        self.update()
    
    def set_brush_radius(self, radius: int):
        """Set the brush radius for cursor preview."""
        self._brush_radius = radius
        self.update()
    
    def set_cursor_visible(self, visible: bool):
        """Set whether the cursor preview is visible."""
        self._show_cursor = visible
        self.update()

    def set_cursor_pos(self, pos: Optional[QtCore.QPoint]):
        self._cursor_pos = pos
        self.update()
    
    def mouseMoveEvent(self, event):
        """Track mouse position for cursor preview."""
        self._cursor_pos = event.pos()
        self.update()
        super().mouseMoveEvent(event)
    
    def enterEvent(self, event):
        """Show cursor when mouse enters widget."""
        self._show_cursor = True
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Hide cursor when mouse leaves widget."""
        self._show_cursor = False
        self._cursor_pos = None
        self.update()
        super().leaveEvent(event)
    
    def paintEvent(self, event):
        """Paint the mask overlay and cursor."""
        painter = QtGui.QPainter(self)
        
        try:
            # Get the plot and scale maps for perfect alignment
            # The parent is the canvas
            canvas = self.parent()
            
            # Check if using SimpleImageWidget or Qwt plot
            if hasattr(canvas, 'canvasMap'):
                # SimpleImageWidget or compatible widget
                xMap = canvas.canvasMap(0)  # xBottom
                yMap = canvas.canvasMap(1)  # yLeft
            elif hasattr(canvas, 'plot'):
                # Qwt canvas - get the plot first
                plot = canvas.plot()
                xMap = plot.canvasMap(plot.xBottom)
                yMap = plot.canvasMap(plot.yLeft)
            else:
                # Can't get coordinate mapping, skip drawing
                return
            
            # Draw mask overlay: one image, not one fillRect per painted bin.
            #
            # The loop this replaces ran a Python iteration and a QPainter call
            # for EVERY non-zero bin, so a brush stroke over a 256 x 256
            # histogram could ask Qt to fill tens of thousands of one-pixel
            # rectangles -- while the mouse was still moving, on every
            # paintEvent. Colouring the mask into an RGBA array and drawing it
            # once is the same picture, and the cost stops depending on how much
            # the user has painted.
            if self._mask is not None:
                painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
                painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, False)

                ny, nx = self._mask.shape
                image = self._mask_image()
                if image is not None:
                    x1, x2 = xMap.transform(0), xMap.transform(nx)
                    y1, y2 = yMap.transform(0), yMap.transform(ny)
                    painter.drawImage(
                        QtCore.QRectF(min(x1, x2), min(y1, y2),
                                      abs(x2 - x1), abs(y2 - y1)),
                        image)
            
            # Draw cursor circle
            if self._show_cursor and self._cursor_pos is not None:
                painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
                
                # Draw circle outline
                pen = QtGui.QPen(QtGui.QColor(255, 255, 255, 200))
                pen.setWidth(2)
                painter.setPen(pen)
                painter.setBrush(QtCore.Qt.NoBrush)
                
                # Draw outer circle (brush size)
                painter.drawEllipse(
                    self._cursor_pos,
                    self._brush_radius,  # Use radius directly, not *2
                    self._brush_radius
                )
                
                # Draw center crosshair
                pen.setWidth(1)
                painter.setPen(pen)
                crosshair_size = 3
                painter.drawLine(
                    self._cursor_pos.x() - crosshair_size,
                    self._cursor_pos.y(),
                    self._cursor_pos.x() + crosshair_size,
                    self._cursor_pos.y()
                )
                painter.drawLine(
                    self._cursor_pos.x(),
                    self._cursor_pos.y() - crosshair_size,
                    self._cursor_pos.x(),
                    self._cursor_pos.y() + crosshair_size
                )
        
        except Exception as e:
            # Silently fail to avoid breaking the UI
            pass
        
        finally:
            painter.end()
    
    def get_plot_coordinates(self, pos: QtCore.QPoint) -> Optional[tuple]:
        """
        Convert widget coordinates to plot coordinates.
        
        Parameters
        ----------
        pos : QtCore.QPoint
            Position in widget coordinates
            
        Returns
        -------
        coords : Optional[tuple]
            (x, y) in plot coordinates, or None if invalid
        """
        if self._mask_bounds is None:
            return None
        
        widget_width = self.width()
        widget_height = self.height()
        
        if widget_width <= 0 or widget_height <= 0:
            return None
        
        xmin, xmax, ymin, ymax = self._mask_bounds
        
        # Convert to plot coordinates
        x = xmin + (pos.x() / widget_width) * (xmax - xmin)
        y = ymin + (pos.y() / widget_height) * (ymax - ymin)
        
        return (x, y)
    
    def get_mask_indices(self, pos: QtCore.QPoint) -> Optional[tuple]:
        """
        Convert widget coordinates to mask array indices.
        
        Parameters
        ----------
        pos : QtCore.QPoint
            Position in widget coordinates
            
        Returns
        -------
        indices : Optional[tuple]
            (row, col) indices in mask array, or None if invalid
        """
        if self._mask is None:
            return None
        
        widget_width = self.width()
        widget_height = self.height()
        
        if widget_width <= 0 or widget_height <= 0:
            return None
        
        mask_height, mask_width = self._mask.shape
        
        # Convert to mask indices
        col = int(pos.x() * mask_width / widget_width)
        row = int(pos.y() * mask_height / widget_height)
        
        # Check bounds
        if 0 <= row < mask_height and 0 <= col < mask_width:
            return (row, col)
        
        return None
