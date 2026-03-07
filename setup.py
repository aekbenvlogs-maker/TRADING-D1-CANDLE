# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : setup.py
# DESCRIPTION  : Compilation des extensions Cython
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# WORKFLOW     : VSCode + Claude + Copilot Pro + File Engineering
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

from setuptools import setup
from Cython.Build import cythonize
import numpy as np

setup(
    name="TRADING-D1-BOUGIE",
    ext_modules=cythonize(
        "trading_d1_bougie/core/*.pyx",
        compiler_directives={"language_level": "3"},
    ),
    include_dirs=[np.get_include()],
)
