

# Version

This report describes the changes made to the Harvested Wood Products component as of
April 23 2025.

  - Added a new HWP (Harvested Wood Product) object to the post processor.
  - Moved the HWP code to a common input section for better organization.
  - Loaded Nicola Bozzolan grading data.
  - Added a check to make sure proportions always sum to one.
  - Included examples of how to use the hwp code.
  - Added calculations for fluxes by grade.
  - Made the function crf_sminifinished_data a method in the common input module.
  - Added NB grading allocation calculations.
  - Calculated production from domestic wood using export correction factors.
  - Prepared the code to allow backing up export factors.
  - Added a function to fill gaps in production data based on EU wide values
  - Calculated domestic production in tons of carbon.
  - Added a function to fill missing production data back to the year 1900.
  - Added a function to fill gaps in export factors.
  - Added calculations for fractions of semi-finished products.
  - Combined different functions for simulation and decay/inflow calculations.
  - Plotted production from domestic harvest for both reported and simulated data.
  - Outputted the fraction of semi-finished products from the CBM (Carbon Budget Model).
  - Corrected recycling calculations for prod_from_dom_harv_sim and
    prod_from_dom_harv_stat.

# Version 0.7.1

- Compute sink and harvest expected provided, as well as harvest area in the post
  processor


# Version 0.7.0

- Add capability to change the disturbance matrix
