""" The purpose of this script is to compare libcbm 1x and libcbm 2x

Warning: This script will only work on a development machine which has libcbm_py
and eu_cbm_hat installed from git repositories and given as a path through the
PYTHONPATH environment variable.

- Results are written to a parquet file in eu_cbm_hat/info/output_data.py
- This result dataframe is a merge of all results data frames from the cbm_output object
- These data frames are read in the `__getitem__` method of the class InternalData
- That `__getitem__` method calls `getattr(self.sim.cbm_output, item).to_pandas()`

For the selected countries and for the 2 different versions of the model,
backup these parquet files in a "comparison" directory inside the eu_cbm_data
directory.

"""

import shutil
import sys
import warnings

from pathlib import Path
import pandas
from eu_cbm_hat.core.continent import continent
import git


# Choose which libcbm version to run
RUN_LIBCBM_VERSION = None
# RUN_LIBCBM_VERSION = 1
# RUN_LIBCBM_VERSION = 2

# Destination directory to store and compare results
comp_dir = Path(continent.base_dir) / "output" / "comparison"
if not comp_dir.exists():
    comp_dir.mkdir()

# Find location of git repositories for libcbm_py and eu_cbm_hat
def find_sys_path(path_contains:str):
    """Find path that contains the given characters.
    Raise an error if there's not exactly one matching path"""
    matching_paths = [path for path in sys.path if path_contains in path]
    if len(matching_paths) != 1:
        msg = f"Expected one path containing {path_contains}, "
        msg += f"found {len(matching_paths)}\n"
        msg += f"{matching_paths}"
        raise ValueError(msg)
    return matching_paths[0]

repo_eu_cbm_hat = git.Repo(find_sys_path("eu_cbm_hat"))
repo_libcbm_py = git.Repo(find_sys_path("libcbm_py"))

def checkout_branch(git_repo:git.repo.base.Repo, branch_name:str):
    """Check if a repository has any changes and checkout the given branch
    """
    if git_repo.is_dirty(untracked_files=True):
        msg = f"There are changes in {git_repo}.\n"
        msg += f"Not checking out the '{branch_name}' branch."
        raise RuntimeError(msg)
    git_repo.git.checkout(branch_name)
    print(f"Checked out branch: {branch_name} of {git_repo}.")


# Create runners
r_at = continent.combos['reference'].runners['AT'][-1]
r_cz = continent.combos['reference'].runners['CZ'][-1]
r_se = continent.combos['reference'].runners['SE'][-1]
r_zz = continent.combos['reference'].runners['ZZ'][-1]

def run_and_store_comparison(runner, version):
    """Run the model and store results in parquet files for comparison purposes."""
    print(f"Running {runner}\nwith libcbm version {version}")
    runner.num_timesteps = 30
    runner.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)
    new_parquet_file = comp_dir / f"zz_output_libcbm_{version}.parquet"
    shutil.copy(runner.output.paths["results"], new_parquet_file)


######################################################################
# Run Libcbm version 1 and store results in the comparison directory #
######################################################################
if RUN_LIBCBM_VERSION == 1:
    warnings.warn("You need to restart the python shell between changes of libcbm version.")
    checkout_branch(repo_libcbm_py, "1.x")
    checkout_branch(repo_eu_cbm_hat, "main")
    assert repo_libcbm_py.active_branch.name == '1.x'
    assert repo_eu_cbm_hat.active_branch.name == 'main'

    # Old comment which may not be relevant now that we have the
    # checkout_branch function to checkout the required branches.
    # eu_cbm_hat v0.6.1 is compatible with libcbm version 1
    # Checkout the libcbm 1x branch and tag v0.6.1 of eu_cbm_hat
    # cd ~/repos/eu_cbm/libcbm_py/
    # git checkout 1.x
    # cd ~/repos/eu_cbm/eu_cbm_hat/
    # git checkout tags/v0.6.1

    # Run the models
    for this_runner in [r_zz]:
        run_and_store_comparison(this_runner, RUN_LIBCBM_VERSION)

######################################################################
# Run Libcbm version 2 and store results in the comparison directory #
######################################################################
if RUN_LIBCBM_VERSION == 2:
    warnings.warn("You need to restart the python shell between changes of libcbm version.")
    checkout_branch(repo_libcbm_py, "2.x")
    checkout_branch(repo_eu_cbm_hat, "libcbm2")
    assert repo_libcbm_py.active_branch.name == '2.x'
    assert repo_eu_cbm_hat.active_branch.name == 'libcbm2'
    # Run the models
    for this_runner in [r_zz]:
        run_and_store_comparison(this_runner, RUN_LIBCBM_VERSION)

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


#########################
# Aggregate and compare #
#########################
# Aggregate area and merchantable pool over
# only a few classifiers and disturbance type.
# Then compare version 1 and 2.
index = ["year", "forest_type", "region", "disturbance_type"]
agg_vars = ["area",
            "hardwood_merch",
            "softwood_merch",
            "softwood_merch_to_product",
            "hardwood_merch_to_product",
            ]
zz1_agg = zz1.groupby(index)[agg_vars].agg(sum).reset_index()
zz2_agg = zz2.groupby(index)[agg_vars].agg(sum).reset_index()

# Merge
zz5_agg = zz1_agg.merge(zz2_agg, on=index, how="outer")

# diff
zz5_agg["hwm_diff"]  = zz5_agg["hardwood_merch_y"] - zz5_agg["hardwood_merch_x"]
zz5_agg["swm_diff"]  = zz5_agg["softwood_merch_y"] - zz5_agg["softwood_merch_x"]
# zz5_agg.query("hwm_diff !=0 or swm_diff !=0").to_csv("/tmp/hwmdiff.csv", index=False)






####################################################################
# Make a reproducible data set that can be run with libcbm_py only #
####################################################################



