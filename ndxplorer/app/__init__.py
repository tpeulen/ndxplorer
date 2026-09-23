"""ndXplorer on emtk: the app that replaces the Qt window.

No toolkit is imported here or below: the app is an emtk control
(:class:`ndxplorer.app.frame.NdxApp`) that any emtk host draws -- a native
window, a Tk window, a browser page, or a headless capture.

``python -m ndxplorer --emtk [--file PATH]`` opens it.
"""
