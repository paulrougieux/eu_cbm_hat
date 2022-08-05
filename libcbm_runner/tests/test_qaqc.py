"""
Test QAQC methods

Execute the test suite from bash with py.test as follows:

    cd ~/repos/libcbm_runner/libcbm_runner
    pytest

"""

import numpy as np
import pandas
import pytest
from libcbm_runner.core.continent import continent
combo  = continent.combos['hat']
runner = combo.runners['ZZ'][-1]


