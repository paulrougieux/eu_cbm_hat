
# EU-CBM-HAT Quick Start Guide on JRC BDAP

Get up and running with EU-CBM-HAT. This guide shows you how to install the model, set
up your data, and run your first forest carbon simulation.

Note: This setup is for the Joint Research Centre JRC compute cluster called
[BDAP](https://jeodpp.jrc.ec.europa.eu/bdap/). You will have to adapt the instructions
if you are running on another computer system.

- See also the bdap guide inside obs3df_documents/tools/bdap/bdap_guide.md


# What You'll Need

- Access to the JRC BDAP compute cluster (or a local Linux/Mac environment)
- A GitLab account with access to the eu_cbm repositories
- Basic familiarity with command line and Python


# Installation

EU-CBM-HAT requires three main components:

1. **eu_cbm_hat** - The Python package (the model itself)
2. **eu_cbm_data** - Country-specific input data (inventory, growth, disturbances)
3. **eu_cbm_aidb** - Archive Index Database (soil parameters, biomass factors)

Follow the steps to set up required input data.


## Step 1: Create a GitLab access token

You'll need an access token to download data from private repositories:

1. Log into your GitLab account at https://gitlab.com
2. Click your profile picture → **Preferences** → **Access Tokens**
3. Click **Add new token**
   - Name: `jrc_bdap` (or any name you prefer)
   - Expiration: Set 3-6 months from now
   - Scope: Check **read_repository** only
4. Click **Create personal access token**
5. **Important**: Copy and save the token immediately to your password manager (it won't be shown again)

## Step 2: Download the model's code and data

Open a terminal and create the directory structure:

```bash
# Navigate to your user directory
cd /eos/jeodpp/home/users/$USER

# Create main directory
mkdir eu_cbm
cd eu_cbm

# Clone the three required repositories
git clone https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_hat.git
git clone https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_aidb.git
# You'll be prompted for username and token on the first clone of the private repository
git clone https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_data.git
# Optional
git clone https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_explore.git
```

**When prompted:**
- Username: Your GitLab username
- Password: Paste the access token you created in Step 1. Git will remember the token
  for subsequent git pull operations.


## Step 3: Create symbolic links between user's home and the large storage space

The model expects to find data in `$HOME/eu_cbm`, so create symbolic links from the
user's home directory to the large storage space where the data will actually be located
(note `$HOME` will auto complete to the correct directory, no need to replace it in the
instructions below):

```bash
# Link from home directory
cd $HOME
ln -s /eos/jeodpp/home/users/$USER/eu_cbm eu_cbm

# Link from storage directory (for Jupyter Lab file browser)
cd /storage/$USER
ln -s /eos/jeodpp/home/users/$USER/eu_cbm eu_cbm
```

**Verify your setup:**
```bash
ls -l $HOME/eu_cbm
# You should see: eu_cbm_data, eu_cbm_aidb, eu_cbm_explore
```


## Step 4: Install eu_cbm_hat in a Conda environment

```bash
cd $HOME/eu_cbm/eu_cbm_hat
conda env create -f environment.yml
conda activate eu_cbm_hat
# Install the package
pip install -e .
```

Follow these instructions only in case of an update. **Ignore these instructions on the
first installation**, if you want a fresh start, remove the old environment, recreate
it, reinstall the package and the Jupyter kernel.

```bash
cd $HOME/eu_cbm/eu_cbm_hat
# Remove the old environment
conda deactivate
conda env remove -n eu_cbm_hat
# Recreate from environment.yml
conda env create -f environment.yml
# Reinstall the package
conda activate eu_cbm_hat
pip install -e .
# Reinstall the Jupyter kernel
python -m ipykernel install --user --name=eu_cbm_hat_kernel --display-name "Python (eu_cbm_hat)"
```


## Step 5: Configure Jupyter to find the eu_cbm_hat Conda environment

Configure jupyter to find the conda environment as a kernel:

```bash
conda activate eu_cbm_hat
# Install ipykernel in the environment (if not already installed)
conda install ipykernel -y
# Install the Jupyter kernel for eu_cbm_hat
python -m ipykernel install --user --name=eu_cbm_hat_kernel
# Verify installation
jupyter kernelspec list
```

### Outdated instructions for the susbiom trade environment pre-2025

**Please ignore this section**, as of November 2025, the following instructions should
not be necessary.

- See issue 134 https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_hat/-/issues/134

- Instruction below for the susbiom trade conda environment and associated jupyter
  kernel kept here temporarily in case there is a use case where you do need the susbiom
  trade environment.

Edit your profile to load the conda environment:

```bash
# Open your profile file
# In Jupyter Lab file browser, navigate to: /home/<username>/.profile
# Or use a text editor:
vim $HOME/.profile
```

Add this line at the end:
```bash
source /storage/SUSBIOM-TRADE/env_var/.env
```

Save and close the file, then reload it:
```bash
source $HOME/.profile
```

Configure jupyter to find the conda environment as a kernel:

```bash
# Add the environment directory
conda config --append envs_dirs /storage/SUSBIOM-TRADE/conda/

# Install the Jupyter kernel
/storage/SUSBIOM-TRADE/conda/susbiom_trade_env/bin/python -m ipykernel install --user --name=susbiom_trade_kernel

# Verify installation
jupyter kernelspec list
# You should see: susbiom_trade_kernel
```

## Step 6: Initialize the AIDB

Open Jupyter Lab and create a new console with the `eu_cbm_hat_kernel`:

```python
from eu_cbm_hat.core.continent import continent

# Create symbolic links for all country AIDBs
for country in continent:
    country.aidb.symlink_all_aidb()
```

This may take a few minutes. You should see progress messages for each country.

## Step 7: Run Your First Simulation

### Test Run: Single Country (ZZ - Test Country)

In a Python console or notebook with the `eu_cbm_hat_kernel`:

```python
from eu_cbm_hat.core.continent import continent

# Load the test country (ZZ) with the reference scenario
runner = continent.combos['reference'].runners['ZZ'][-1]

# Run the simulation
runner.run(keep_in_ram=True, verbose=True, interrupt_on_error=True)

# Check basic results
print(f"Simulation completed for {runner.country.country_code}")
print(f"Years simulated: {runner.country.base_year} to {runner.country.num_timesteps + runner.country.base_year}")
```

**What's happening:**
- `continent.combos['reference']` - Loads the reference scenario
- `.runners['ZZ'][-1]` - Gets the runner for country ZZ (last version)
- `keep_in_ram=True` - Stores results in memory for quick access
- `verbose=True` - Shows progress messages
- `interrupt_on_error=True` - Stops if errors occur

### Expected Output:

You should see progress messages about loading data, running timesteps, and completion
status. The test country ZZ typically completes in 1-2 minutes.

## Step 8: Access Your Results

After the run completes:

```python
# Access carbon stock data
stocks = runner.output.stock

# Access carbon sink (CO2 emissions/removals)
sink = runner.post_processor.sink.long

# View first few rows
print(sink.head())

# Get summary statistics
print(f"Total sink over simulation: {sink['Total'].sum():.2f} Mt CO2e")
```

# Running the model


## Running Real Countries

Once you've tested with ZZ, try a real country:

```python
# Example: Run Austria
runner_at = continent.combos['reference'].runners['AT'][-1]
runner_at.run(keep_in_ram=True, verbose=True)

# Compare with Germany
runner_de = continent.combos['reference'].runners['DE'][-1]
runner_de.run(keep_in_ram=True, verbose=True)
```

**Available countries:**
Check what's available with:
```python
print(list(continent.combos['reference'].runners.keys()))
```


## Running Multiple Countries in parallel

The scenario combination object has a run method to run a list of countries. If the list
of countries is not specified, run all countries. A convenient method that makes it
possible to run all countries inside a combination of scenarios. If one country fails to
run, the error will be kept in its log files but the other countries will continue to
run.

Note: this method makes use of the run_one_country() function above which will only run
one step inside the country. An update to that function will be needed in case your
simulation needs many steps. We typically only run one step normally. Here the meaning
of step is not that of yearly time steps, but bigger steps in terms of being able to
start and stop the model which were foreseen in a legacy version of the model.

For example the following code runs the "reference" scenario combination for many
countries:

```python
from eu_cbm_hat.core.continent import continent
# Run a list of countries
continent.combos["reference"].run(2050, ['LU','ZZ'])
# Run all countries with parallel cpus
continent.combos["reference"].run(2050)
# Run sequentially (not in parallel)
continent.combos["reference"].run(2050, parallel=False)
```

# Defining Scenarios

Scenarios are defined in YAML files located in `eu_cbm_data/combos/`. The 'reference'
scenario is the baseline. To see available scenarios:

```python
print(list(continent.combos.keys()))
```

To run a different scenario:
```python
# Example: high harvest scenario
runner = continent.combos['high_harvest'].runners['AT'][-1]
runner.run(keep_in_ram=True, verbose=True)
```

# Troubleshooting

**Problem:** `ModuleNotFoundError: No module named 'eu_cbm_hat'`
- **Solution:** Make sure you selected the `eu_cbm_hat_kernel` in Jupyter Lab

**Problem:** `FileNotFoundError` when accessing country data
- **Solution:** Verify symbolic links exist: `ls -l $HOME/eu_cbm`

**Problem:** GitLab authentication fails
- **Solution:** Regenerate your access token and try cloning again

**Problem:** AIDB symlinks fail
- **Solution:** Ensure you have write permissions in the aidb directory

# Next Steps

Now that you have the model running:

1. **Explore the output data structure** - See the [post_processor documentation](eu_cbm_hat/post_processor.html)
2. **Modify scenarios** - Learn about YAML scenario files in `eu_cbm_data/combos/`
3. **Analyze results** - Use `eu_cbm_explore` for visualization and analysis tools
4. **Run custom simulations** - See the [full documentation](https://bioeconomy.gitlab.io/eu_cbm/eu_cbm_hat/eu_cbm_hat.html)

# Getting Help

- **Documentation:** https://bioeconomy.gitlab.io/eu_cbm/eu_cbm_hat/eu_cbm_hat.html
- **Source code:** https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_hat
- **Issues:** Report problems on the GitLab issue tracker https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_hat/-/issues

# Developer Setup (Optional)

If you want to modify the `eu_cbm_hat` code itself:

```bash
# Clone the package repository
cd $HOME/eu_cbm
git clone https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_hat.git

# Edit your .profile to prioritize your development version
echo "export PYTHONPATH='/eos/jeodpp/home/users/$USER/eu_cbm/eu_cbm_hat/':$PYTHONPATH" >> $HOME/.profile

# Reload your profile
source $HOME/.profile
```

Now your local changes to `eu_cbm_hat` will be used instead of the conda-installed version.p
