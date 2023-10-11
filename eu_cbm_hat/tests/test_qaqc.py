"""
Test QAQC methods

Execute the test suite from bash with py.test as follows:

    cd ~/repos/eu_cbm_hat/eu_cbm_hat
    pytest

"""

import numpy as np
import pandas
import pytest
from eu_cbm_hat.core.continent import continent

runner = continent.combos['reference'].runners['ZZ'][-1]

