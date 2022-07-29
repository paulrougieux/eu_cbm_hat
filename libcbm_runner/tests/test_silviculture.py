"""
Test salvage logging methods

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

harvest_factors_1 = {'scenario': ['reference', 'reference', 'reference', 'no_skew', 'no_skew'],
                     'product_created': ['irw_and_fw', 'irw_and_fw', 'fw_only', 'irw_and_fw', 'fw_only'],
                     'forest_type': np.nan,
                     'mgmt_type': np.nan,
                     'con_broad': ['con', 'broad', np.nan, np.nan, np.nan],
                     'disturbance_type': np.nan,
                     'value_2015': [0.3, 0.7, 1.0, 1.0, 1.0]}
harvest_factors_1 = pandas.DataFrame(harvest_factors_1)

harvest_factors_2 = {'scenario': ['reference', 'reference', 'reference', 'no_skew', 'no_skew'],
                     'product_created': ['irw_and_fw', 'irw_and_fw', 'fw_only', 'irw_and_fw', 'fw_only'],
                     'forest_type': np.nan,
                     'mgmt_type': np.nan,
                     'con_broad': ['con', np.nan, np.nan, np.nan, np.nan],
                     'disturbance_type': np.nan,
                     'value_2015': [0.3, 0.7, 1.0, 1.0, 1.0]}
harvest_factors_2 = pandas.DataFrame(harvest_factors_2)

harvest_factors_3 = {'scenario': ['reference', 'reference', 'reference', 'no_skew', 'no_skew'],
                     'product_created': ['irw_and_fw', 'irw_and_fw', 'fw_only', 'irw_and_fw', 'fw_only'],
                     'forest_type': np.nan,
                     'mgmt_type': np.nan,
                     'con_broad': ['con', 'broad', np.nan, np.nan, np.nan],
                     'disturbance_type': np.nan,
                     'value_2015': [0.3, 0.8, 1.0, 1.0, 2.0]}
harvest_factors_3 = pandas.DataFrame(harvest_factors_3)

def test_correct_harvest_factors_input():
    """Test the function that checks harvest_factors input files, with correct input"""
    runner.silv.harvest.raw = harvest_factors_1
    runner.silv.harvest.extra_checks()

def test_incomplete_columns_returns_error():
    """Test the function that checks harvest_factors input files, with wrong input"""
    runner.silv.harvest.raw = harvest_factors_2
    with pytest.raises(ValueError) as excinfo:
        runner.silv.harvest.extra_checks()
    assert "cannot be incomplete" in str(excinfo.value)

def test_skew_factors_do_not_sum_to_one():
    """Test with a skew factor that do not sum to one"""
    runner.silv.harvest.raw = harvest_factors_3
    with pytest.raises(ValueError) as excinfo:
        runner.silv.harvest.extra_checks()
    assert "do not sum to one" in str(excinfo.value)

