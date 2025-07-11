


# Order HWP function calls

Order of HWP method calls in eu_cbm_hat/post_processor/hwp.py

self = runner.post_processor.hwp
# Order of function calls
self.runner.output.pool_flux
self.fluxes_to_products
self.fluxes_to_irw
self.fluxes_by_age_to_dbh
self.fluxes_by_grade_dbh
self.fluxes_by_grade
self.fraction_semifinished_n_years_mean
self.fraction_semifinished_default
self.prod_from_dom_harv_sim
self.concat_1900_to_last_sim_year
self.prepare_decay_and_inflow
self.build_hwp_stock_since_1900
self.stock_sink_results



