
# Introduction

This setup is for the Joint Research Centre JRC compute cluster called
[BDAP](https://jeodpp.jrc.ec.europa.eu/bdap/).

- See also the bdap guide inside obs3df_documents/tools/bdap/bdap_guide.md


# Create eu_cbm and load data

Some of the commands we used to configure the EU-CBM-HAT model on BDAP JEO-Desk:

- Start Applications / JEODPP / Jupyter Lab

- Start a bash terminal within Jupyter lab

- Move to the `/eos` user directory and create a `eu_cbm` directory there, then clone
  the repositories one by one. Use your gitlab user name and personal authentication
  token on the first clone (git will remember the token after that)

```
cd /eos/jeodpp/home/users/$USER
mkdir eu_cbm
cd eu_cbm
git clone https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_data.git
git clone https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_aidb.git
git clone https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_explore
```

- Move to the user `$HOME` directory and create a symbolic link to the `/eos` home
  directory (`$HOME/eu_cbm` is the default location of the `eu_cbm` data and aidb
  directories, as defined in
  [`eu_cbm_hat/__init__.py`](https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_hat/-/blob/main/eu_cbm_hat/__init__.py?ref_type=heads#L47)).
  Then move to the `/storage` directory and create a symbolic link to `eu_cbm` there as
  well (this is needed because `/storage` is the root of the Jupyter lab file browser
  for some unknown reason)

```
cd $HOME
ln -s /eos/jeodpp/home/users/$USER/eu_cbm eu_cbm
cd /storage/$USER
ln -s /eos/jeodpp/home/users/$USER/eu_cbm eu_cbm
```

# Setup conda and environment variables

-  Edit your `.profile` inside your user directory by entering the following in the file
   browser's address bar:  `/home/<your username>/.profile`. A file editor will open.
   Add this line of code at the end of the file and then save it (more details above).
   This will load the conda environment for jeo desk.

```
source /storage/SUSBIOM-TRADE/env_var/.env
```

- Add the parent directory of the use case environment susbiom_trade_env. Click on
  “Terminal Emulator” type

```
conda config --append envs_dirs /storage/SUSBIOM-TRADE/conda/
```

- Type this command and then press enter :

```
/storage/SUSBIOM-TRADE/conda/susbiom_trade_env/bin/python -m ipykernel install --user --name=susbiom_trade_kernel
```

- **Optional developer setup** `eu_cbm_hat` was installed by pip install inside the
  conda environment. But in case we choose to overwrite that version, we can clone the
  `eu_cbm_hat` repository as well and set the `PYTHONPATH` environment variable to load
  the development version of `eu_cbm_hat` first.

```
cd $HOME/eu_cbm
git clone https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_hat.git
# Edit .profile with a text editor and enter your actual user name
cd $HOME
vim .profile
export PYTHONPATH='/eos/jeodpp/home/users/USER_NAME/eu_cbm/eu_cbm_hat/':$PYTHONPATH
```


# Setup Jupyter Lab

Make the python program from the `susbiom_trade_env` available as an ipython kernel for
processing with jupyter lab:

    /storage/SUSBIOM-TRADE/conda/susbiom_trade_env/bin/python -m ipykernel install --user --name=susbiom_trade_kernel

Check that it is now available:

    jupyter kernelspec list


# Create AIDB symlinks


- To create AIDB symlinks. Press the big blue plus button in Jupyter lab to start a new
  launcher, then start a console with the `susbiom_trade_kernel`. In that console enter:

```
from eu_cbm_hat.core.continent import continent
for country in continent:
    country.aidb.symlink_all_aidb()
```

- **Note**: This setup uses the default location of  `eu_cbm_data` and `eu_cbm_aidb`, it
  is therefore not necessary to define the environment variables `EU_CBM_DATA` and
  `EU_CBM_AIDB`.


# Run the model

Try to run the model for one country in a python console:

```
from eu_cbm_hat.core.continent import continent
runner = continent.combos['reference'].runners['ZZ'][-1]
runner.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)
```

- Try a run for many countries by looking
  at `eu_cbm_hat/scripts/running/run_scenario_combo.py`


