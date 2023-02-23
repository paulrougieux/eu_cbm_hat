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
# eu_cbm_hat v0.6.1 is compatible with libcbm version 1
# Checkout the libcbm 1x branch and tag v0.6.1 of eu_cbm_hat
# cd ~/repos/eu_cbm/libcbm_py/
# git checkout 1.x
# cd ~/repos/eu_cbm/eu_cbm_hat/
# git checkout tags/v0.6.1

# Run the models
r_at.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)
r_cz.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)
r_se.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)
r_zz.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)



# Copy resulting parquet files to a specific folder in eu_cbm_data
shutil.copy(r_zz.output.paths["results"], comp_dir / "zz_output_libcbm_1.parquet")

######################################################################
# Run Libcbm version 2 and store results in the comparison directory #
######################################################################
# Checkout the libcm 2x branch and the libcbm2 branch of eu_cbm_hat
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

zz1 = pandas.read_parquet(comp_dir / "zz_output_libcbm_1.parquet")
zz2 = pandas.read_parquet(comp_dir / "zz_output_libcbm_2.parquet")


#################################
# Dumb comparison line for line #
#################################
# Check the ones with different disturbance types
zz3 = zz2.copy()
zz3["diff"] = zz1["disturbance_type"] - zz2["disturbance_type"]
zz3["disturbance_type_v1"] = zz1["disturbance_type"]
zz3["disturbance_type_v2"] = zz2["disturbance_type"]
zz3.query("diff!=0")
# It seems the data frames are not aligned

index = ['timestep',
         'disturbance_type',
         'status',
         'forest_type',
         'region',
         'mgmt_type',
         'mgmt_strategy',
         'climate',
         'con_broad',
         'site_index',
         'growth_period',
         'year',
         'age_class',
        ]
# Sort values by the index
zz1.sort_values(index, inplace=True)
zz1.reset_index(inplace=True, drop=True)
zz2.sort_values(index, inplace=True)
zz2.reset_index(inplace=True, drop=True)

# There are less differences now
zz4 = zz2.copy()
zz4["diff"] = zz1["disturbance_type"] - zz2["disturbance_type"]
zz4["disturbance_type_v1"] = zz1["disturbance_type"]
zz4["disturbance_type_v2"] = zz2["disturbance_type"]
zz4.query("diff!=0")
# zz4.query("diff!=0").to_csv("/tmp/zz4.csv")


print("zz1.equals(zz2):", zz1.equals(zz2))

for col in zz1.columns:
    if pandas.api.types.is_numeric_dtype(zz1[col]):
        diff = zz1[col] - zz2[col]
        print(f"\n{col}:", diff.abs().sum() / zz1[col].sum())
        print(diff)
    else:
        print(f"{col} is of string type")


############################
# Summarise by index variables and merge #
############################
# Aggregate
variables = ['hardwood_merch',
             'softwood_merch',
             'softwood_merch_to_product',
             'hardwood_merch_to_product',
            ]
zz1_agg = zz1.groupby(index)[variables].agg(sum).reset_index()
zz2_agg = zz2.groupby(index)[variables].agg(sum).reset_index()

# Merge
zz5_agg = zz1_agg.merge(zz2_agg, on=index, how="outer")

# diff 
zz5_agg["hwm_diff"]  = zz5_agg["hardwood_merch_y"] - zz5_agg["hardwood_merch_x"]
# zz5_agg.query("hwm_diff !=0").to_csv("/tmp/hwmdiff.csv")





