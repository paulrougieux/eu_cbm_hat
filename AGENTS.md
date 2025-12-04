
# Development Workflow

- Follow NumPy docstrings, type hints, line length 88.
- Comments should explain scientific rationale. Include references to relevant
  literature and standards where applicable
- Use pandas for data manipulation, ensure reproducible code.
- External data repos: eu_cbm_data and eu_cbm_aidb need to be kept in sync.
- Use GitLab CI/CD for automated testing.


# Project Architecture

## Overall Structure

- **Root Directory**: Contains configuration files (.flake8, .gitlab-ci.yml),
  documentation (docs/), scripts for running and setup, and the main package
  `eu_cbm_hat/`.
- **Package Structure**:
  - `eu_cbm_hat/`: Main package directory.
    - `bud/`: Simplified runner for libcbm simulations.
    - `cbm/`: Core CBM logic, including dynamic modifications and simulation.
    - `core/`: Full runner implementation with continent, country, and runner classes.
    - `crcf/`: Runner for Carbon Removal and Carbon Farming simulations.
    - `post_processor/`: Modules for post-processing outputs (sink, stock, harvest, HWP,
      etc.).
    - Other submodules: combos (scenario definitions), info (data handling), launch,
      plot, pump, qaqc (quality assurance), tests.
- **Scripts Directory**: Contains scripts for running simulations, post-processing,
  setup, and conversion tools.
- **Notebooks**: Jupyter notebooks for specific analyses.
- **Docs**: Documentation files.

## Key Components

1. **Runners**: Three types of runners for different use cases:
   - `core/runner.py`: Full-featured runner requiring comprehensive EU data structure.
   - `bud/`: Lightweight runner for simple simulations.
   - `crcf/`: Specialized for carbon removal scenarios.

2. **Post-Processor**: Transforms libcbm outputs into usable indicators like carbon
   sink, stock, harvest allocation.

3. **CBM Module**: Interfaces with libcbm for simulations, includes dynamic features
   like harvest allocation tool (HAT) and climate growth modifiers.

4. **Combos**: YAML-defined scenario combinations for inputs.


## Dependencies

- **Internal**: autopaths, plumbing, pymarktex, pandas, pyyaml, tqdm, p_tqdm, pyarrow,
  numexpr, simplejson.

- **External**: libcbm_py (from GitHub), eu_cbm_data (private repo), eu_cbm_aidb
  (private repo).

- **Python Version**: >=3.8

# Setup and Installation

Refer to README.md for detailed instructions. Key points for all runner types (runner,
bud and crcf):

- Install via pip: `pip install eu_cbm_hat`
- Install libcbm: `pip install
  https://github.com/cat-cfs/libcbm_py/archive/refs/heads/main.tar.gz`


Additional EU data structure required for the core/runner.py runner type

- Clone eu_cbm_data (private repository) and eu_cbm_aidb (public repository)
- Set up data directories: eu_cbm_data and eu_cbm_aidb in ~/eu_cbm/ or via environment
  variables.
- Ensure AIDB symlinks are created after data setup.
- For development: Clone repos, use git for data repos.
- Run tests: Unit tests and ZZ country mock runs.




# Running the Model

- For test: Run ZZ country.
- For full scenarios: Use scripts/running/run_scenario_combo.py for combo simulations.


# Known Issues and TODOs

- CRCF module not fully documented.
- For the core/runner.py runner type, dependency on private repos (eu_cbm_data,
  eu_cbm_aidb) complicates open-source development .
- Performance: Large datasets may require optimization in post-processing.


**Version**: 2.1.2
**Last Updated**: 2025-10-14
**Contact**: Write issues in the GitLab repository.

## Agent Operations

### Task: Update HWP Plot Legend

- Operation: Modified plot_hwp_ils_facet_by_country in eu_cbm_hat/plot/hwp_plots.py to use full product names in the legend
- Details: Capitalized product names in PRODUCT_PALETTE, changed hue to display full names instead of abbreviated column names, updated palette accordingly
- Commit hash: ec5e869

### Task: Modify read_aidb_table_all_countries print statement

- Operation: Modified eu_cbm_hat/qaqc/aidb_all_countries.py to print table name only once and append country codes at each iteration
- Details: Changed the print statement in read_aidb_table_all_countries to display table name once followed by country codes appended on the same line
- Commit hash: 9b7d736

### Task: Fix ValueError in compare_one_country_to_all_others

- Operation: Modified eu_cbm_hat/qaqc/aidb_all_countries.py to fix DataFrame creation error
- Details: Changed pandas.DataFrame initialization to use list for scalar values, avoiding the "must pass an index" ValueError
- Commit hash: dfecc41

### Task: Complete compare_one_country_to_all_others_relative function

- Operation: Modified eu_cbm_hat/qaqc/aidb_all_countries.py to divide country columns by nrow column for relative values
- Details: Added code to divide all country columns by the nrow column to provide relative values in the compare_one_country_to_all_others_relative function
- Commit hash: 2fb19ad

### Task: Get unique values

- Operation: Modified scripts/comparison/share_eu_cbm_data_with_forest_navigator.py to get unique values from irw_frac_by_dist config and complete the share_eu_cbm_data function
- Details: Implemented collection of unique scenario values from config["irw_frac_by_dist"].values() across all combos using set(), completed the share_eu_cbm_data function to share EU CBM data by filtering CSV files for specified scenarios and countries
- Commit hash: f4839bb

