"""Test a bud object

Usage:

    ipython3 -i -- ~/repos/eu_cbm/eu_cbm_hat/scripts/running/run_zz_from_a_bud_object.py

Note: the test input data can be updated with a ZZ model run:

    ipython3 -i -- ~/repos/eu_cbm/eu_cbm_hat/scripts/running/run_zz.py

followed by a transfer of the input data to the bud test dir

    ipython -i ~/eu_cbm/eu_cbm_hat/scripts/setup/copy_zz_from_eu_cbm_data_to_bud_test_dir.py

"""

import eu_cbm_hat as ch
from eu_cbm_hat.bud.test_data import copy_input_to_temp_dir
data_dir = copy_input_to_temp_dir()
bud = ch.Bud(
    data_dir=data_dir,
    aidb_path=ch.eu_cbm_aidb_pathlib / "countries/ZZ/aidb.db"
)
bud.run()

