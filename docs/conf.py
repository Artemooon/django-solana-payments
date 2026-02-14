import os
import sys

sys.path.insert(0, os.path.abspath(".."))

# Required for autodoc modules that import Django models/settings.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_solana_payments.tests.settings")

import django  # noqa: E402

django.setup()

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "django-solana-payments"
copyright = "2026, Artemooon"
author = "Artemooon"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_rtd_theme",
]

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# Keep the RTD sidebar navigation expanded and sticky so items don't disappear
html_theme_options = {
    "collapse_navigation": False,
    "sticky_navigation": True,
    "navigation_depth": 4,
}
