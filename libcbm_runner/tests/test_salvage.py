"""
Test salvage logging methods

Execute the test suite from bash with py.test as follows:

    cd ~/repos/libcbm_runner/libcbm_runner
    py.test

Inspired by the use in pandas
https://github.com/pandas-dev/pandas/blob/main/pandas/tests/strings/test_find_replace.py
"""

from libcbm_runner.core.continent import continent

combo  = continent.combos['hat']
runner = combo.runners['ZZ'][-1]

# runner.num_timesteps = 30
# runner.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)

def test_dist_4_followed_by_29():
    """Disturbance 4 followed by disturbance 29 salvage logging. Prepare input
    data for ZZ Trying to overwrite as much as possible of the input data with
    these data frames """
    # Overwrite the natural disturbance activity
    # events, inventory, growth curves and transitions


    # check the method "__call__" in "info/input_data.py" to see
    # who the data is copied from libcbm_data/countries/zz
    # to libcbm_data/output/hat/ZZ/0/input/csv before the model run
    # Some files are transformed from wide to long format in this process.

    # Overwrite the events template
    # reference	For	PA	LU00	H	E	35	con	1	Cur	irw_and_fw	1	FALSE	0	5	0	5
    # reference	For	PA	LU00	H	E	45	con	1	Cur	irw_and_fw	1	FALSE	0	5	0	5

    # Run the model


    # Check output
    print(runner.input_data["events"])

    # assert [1,2] == [1,2]
    # assert (np.array([1,2]) == np.array([1,2])).all()
    # np.testing.assert_allclose(np.array([1,2]),np.array([1,3]))
