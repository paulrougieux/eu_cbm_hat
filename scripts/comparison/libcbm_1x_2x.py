""" The purpose of this script is to compare libcbm 1x and libcbm 2x

- Results are written to a parquet file in eu_cbm_hat/info/output_data.py
- This result dataframe is a merge of all results data frames from the cbm_output object
- These data frames are read in the `__getitem__` method of the class InternalData
- That `__getitem__` method calls `getattr(self.sim.cbm_output, item).to_pandas()`

For the selected countries and for the 2 different versions of the model,
backup these parquet files in a "comparison" directory inside the eu_cbm_data
directory.

"""

import shutil
from pathlib import Path
import pandas
from eu_cbm_hat.core.continent import continent

# Destination directory to store and compare results
comp_dir = Path(continent.base_dir) / "output" / "comparison"
if not comp_dir.exists():
    comp_dir.mkdir()

# Create runners
r_at = continent.combos['hat'].runners['AT'][-1]
r_at.num_timesteps = 30
r_cz = continent.combos['hat'].runners['CZ'][-1]
r_cz.num_timesteps = 30
r_se = continent.combos['hat'].runners['SE'][-1]
r_se.num_timesteps = 30
r_zz = continent.combos['hat'].runners['ZZ'][-1]
r_zz.num_timesteps = 30


######################################################################
# Run Libcbm version 1 and store results in the comparison directory #
######################################################################
# Checkout the libcbm 1x branch and tag v of eu_cbm_hat
# cd ~/repos/eu_cbm/libcbm_py/
# git checkout 1.x
# cd ~/repos/eu_cbm/eu_cbm_hat/
# git checkout main

# Run the models
r_at.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)
r_cz.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)
r_se.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)
r_zz.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)



# Copy resulting parquet files to a specific folder in eu_cbm_data

######################################################################
# Run Libcbm version 2 and store results in the comparison directory #
######################################################################
# Checkout the libcm 2x branch and the libcbm 2 branch of eu_cbm_hat
# cd ~/repos/eu_cbm/libcbm_py/
# git checkout 2.x
# cd ~/repos/eu_cbm/eu_cbm_hat/
# git checkout libcbm2

# Run the models
r_at.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)
r_cz.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)
r_se.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)
r_zz.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)

# Copy resulting parquet files to a specific folder in eu_cbm_data
shutil.copy(r_zz.output.paths["results"], comp_dir / "zz_output_libcbm_2.parquet")


###################
# Compare results #
###################
# Compare the resulting parquet files

zzout1 = pandas.read_parquet(comp_dir / "zz_output_libcbm_1.parquet")
zzout2 = pandas.read_parquet(comp_dir / "zz_output_libcbm_2.parquet")

