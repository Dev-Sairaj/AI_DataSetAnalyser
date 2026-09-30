"""ADIP API."""

import os

# Reports are rendered off-screen in worker threads, so never try to open a GUI backend.
os.environ.setdefault("MPLBACKEND", "Agg")