# Show the depe


HWPCommonInput Class Dependency Flowchart
-----------------------------------------
(Note: Arrows indicate method calls or property dependencies. Properties are cached unless noted. Global helpers shown at top.)

Global Helpers:
- generate_dbh_intervals()  (standalone)
- backfill_avg_first_n_years(df, var, n)  (standalone, used in properties)

HWPCommonInput
├── __init__()
│   ├── Sets: common_dir, c_sw_*, n_years_for_backfill, no_export_no_import
│
├── decay_params (cached_property)
│   └── No direct calls
│
├── hwp_types (cached_property)
│   └── Reads CSV
│
├── eu_member_states (cached_property)
│   └── Reads CSV
│
├── faostat_bulk_data (cached_property)
│   └── Reads CSV
│
├── crf_stat (cached_property)
│   └── Reads CSV
│
├── ctf_unfccc (cached_property)
│   └── Reads CSV
│
├── subst_params (cached_property)
│   └── Reads CSV
│
├── hwp_fraction_semifinished_scenario (cached_property)
│   └── Reads CSV
│
├── split_wood_panels (cached_property)
│   └── Calls: self.fao_correction_factor
│
├── subst_ref (cached_property)
│   └── Reads CSV
│
├── silv_to_hwp (cached_property)
│   └── Reads CSV
│
├── irw_allocation_by_dbh (cached_property)
│   └── Calls: self.hwp_genus
│
├── hwp_genus (cached_property)
│   └── Reads CSV
│
├── nb_grading (cached_property)
│   └── Reads CSV
│
├── fao_correction_factor (cached_property)
│   ├── Calls: self.faostat_bulk_data
│   ├── Calls: self.hwp_types
│   └── Calls: self.eu_member_states
│
├── rw_export_correction_factor (cached_property)
│   └── Calls: self.fao_correction_factor
│
├── sw_con_broad_share (cached_property)
│   └── Calls: self.fao_correction_factor
│
├── crf_semifinished_data (cached_property)
│   ├── Calls: self.crf_stat
│   └── Calls: self.sw_con_broad_share
│
├── eu_semifinished_complete_series (cached_property)
│   └── Calls: self.crf_semifinished_data
│
├── prod_gap_filled (cached_property)
│   ├── Calls: self.crf_semifinished_data
│   └── Calls: self.eu_semifinished_complete_series
│
├── prod_backcast_to_1900 (cached_property)
│   └── Calls: self.prod_gap_filled
│
├── prod_from_dom_harv_stat (property, not cached)
│   ├── Calls: self.rw_export_correction_factor
│   ├── Calls: self.prod_backcast_to_1900
│   └── Calls: backfill_avg_first_n_years (global)
│
└── waste (cached_property)
    └── Reads CSV

HWP Class Dependency Flowchart
-------------------------------
(Note: Inter-file calls to HWPCommonInput shown with [External]. Properties may depend on runner/parent attributes.)

HWP
├── __init__(self, parent)
│   ├── Sets: self.parent, self.runner, etc.
│   ├── self.irw_frac = self.parent.irw_frac
│   └── self.pools_fluxes = self.runner.output.pool_flux
│
├── prod_from_dom_harv_stat (property)
│   └── Calls: hwp_common_input.prod_from_dom_harv_stat [External]
│
├── fluxes_to_products (cached_property)
│   ├── Calls: self.parent.irw_frac
│   └── Uses: self.pools_fluxes
│
├── fluxes_to_irw (cached_property)
│   ├── Calls: self.fluxes_to_products
│   └── Calls: self.parent.wood_density_bark_frac
│
├── fluxes_by_age_to_dbh (cached_property)
│   ├── Calls: hwp_common_input.irw_allocation_by_dbh [External]
│   └── Calls: self.fluxes_to_irw
│
├── fluxes_by_grade_dbh (cached_property)
│   ├── Calls: hwp_common_input.nb_grading [External]
│   └── Calls: self.fluxes_by_age_to_dbh
│
├── fluxes_by_grade (cached_property)
│   └── Calls: self.fluxes_by_grade_dbh
│
├── fraction_semifinished_n_years_mean (property)
│   ├── Calls: self.prod_from_dom_harv_stat
│   └── Calls: self.fluxes_by_grade
│
├── fraction_semifinished_default (property)
│   └── Calls: self.fraction_semifinished_n_years_mean
│
├── fraction_semifinished_scenario (property)
│   ├── Calls: self.fraction_semifinished_n_years_mean
│   └── Calls: hwp_common_input.hwp_fraction_semifinished_scenario [External]
│
├── fraction_semifinished (property)
│   └── Calls: self.fraction_semifinished_default or self.fraction_semifinished_scenario
│
├── prod_from_dom_harv_sim (property)
│   ├── Calls: self.fluxes_by_grade
│   ├── Calls: self.fraction_semifinished
│   └── Calls: hwp_common_input.c_wp, hwp_common_input.c_pp [External]
│
├── concat_1900_to_last_sim_year (property)
│   ├── Calls: self.prod_from_dom_harv_stat
│   └── Calls: self.prod_from_dom_harv_sim
│
├── prepare_decay_and_inflow (property)
│   ├── Calls: self.concat_1900_to_last_sim_year
│   └── Calls: hwp_common_input.decay_params [External]
│
├── build_hwp_stock_since_1900 (property)
│   └── Calls: self.prepare_decay_and_inflow
│
├── build_hwp_stock_since_1990 (property)
│   └── Calls: self.prepare_decay_and_inflow
│
├── fluxes_to_primary_fw (cached_property)
│   ├── Calls: self.fluxes_to_products
│   └── Calls: self.parent.wood_density_bark_frac
│
├── fluxes_to_secondary_fw (cached_property)
│   ├── Calls: self.fluxes_to_products
│   ├── Calls: self.parent.wood_density_bark_frac
│   ├── Calls: self.fluxes_by_grade
│   └── Calls: self.prod_from_dom_harv_sim
│
├── ghg_emissions_fw (cached_property)
│   ├── Calls: self.fluxes_to_primary_fw
│   └── Calls: self.fluxes_to_secondary_fw
│
├── ghg_emissions_waste (cached_property)
│   ├── Calls: hwp_common_input.waste [External]
│   └── Calls: hwp_common_input.decay_params [External]
│
├── ctf_unfccc (cached_property)
│   └── Calls: hwp_common_input.ctf_unfccc [External]
│
└── stock_sink_results (property)
    ├── Calls: self.ctf_unfccc
    ├── Calls: self.build_hwp_stock_since_1900
    ├── Calls: self.build_hwp_stock_since_1990
    ├── Calls: self.ghg_emissions_fw
    └── Calls: self.ghg_emissions_waste

Substitution functions
---------------------------------------------------------


- compute_substitution(runner, subst_scenario)  --> Calls: runner.post_processor.hwp.build_hwp_stock_since_1990, hwp_common_input.split_wood_panels, hwp_common_input.subst_params, runner.post_processor.hwp.ghg_emissions_fw

- compare_substitution(df_ref, df)  (standalone)

