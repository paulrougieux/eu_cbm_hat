"""Test python code examples from the documentation

Test python examples in the documentation of the 'info' directory with pytest
directly at the command line:

    cd ~/rp/eu_cbm/eu_cbm_hat/eu_cbm_hat/info
    pytest clim_adjust_common_input.py --doctest-modules -k 'mean_npp_by_model_country_clu_con_broad' -k 'mean_npp' -v

Test examples with this function from a python REPL

    cd ~/rp/eu_cbm/eu_cbm_hat/scripts/tests/
    ipython

    >>> from test_docstring_examples import run_doctests
    >>> run_doctests("info",
    >>>     [
    >>>     'mean_npp_by_model_country_clu_con_broad',
    >>>     'mean_npp'
    >>> ])

"""

import pytest

# List of function and method names to filter which doctests to run
from eu_cbm_hat import module_dir_pathlib


def run_doctests(subdir, functions_and_methods):
    """Test the python code examples in the given functions and methods.
    """
    subdir = module_dir_pathlib / subdir
    # Build the expression for -k option
    k_expr = " or ".join(functions_and_methods)
    # Arguments for pytest run
    pytest_args = [
        str(subdir),
        "--doctest-modules",
        "-k",
        k_expr,
        "-v",  # verbose output
    ]
    # Run pytest with specified arguments
    return_code = pytest.main(pytest_args)
    return return_code


if __name__ == "__main__":
    run_doctests("info", ["mean_npp_by_model_country_clu_con_broad", "mean_npp"])
