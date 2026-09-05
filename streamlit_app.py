"""Streamlit Community Cloud entry point."""

from importlib import reload

from automated_strain_rate import app

# Streamlit reruns this entry point in a persistent interpreter. Reload the local
# application module so edits are reflected without serving stale map code.
reload(app)
app.run()
