"""ndXplorer: multi-parameter fluorescence data exploration.

The GUI is the emtk app (:mod:`ndxplorer.app`); ``python -m ndxplorer`` opens
it. Nothing is imported with the package, so reading data and the analysis
helpers run in any process -- a batch job, a test, a browser.
"""

#: The licence the distribution ships under (pyproject ``license``); the About box
#: reads it from here so the two cannot drift (guarded by tests/test_license.py).
__license__ = "MIT"
