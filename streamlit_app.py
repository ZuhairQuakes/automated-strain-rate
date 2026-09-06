"""Streamlit Community Cloud entry point."""

import sys
from importlib import reload
from pathlib import Path

# Make the src-layout package importable when Streamlit executes this file
# directly, including fresh Community Cloud checkouts.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from automated_strain_rate import app

# Streamlit reruns this entry point in a persistent interpreter. Reload the local
# application module so edits are reflected without serving stale map code.
reload(app)
app.run()
