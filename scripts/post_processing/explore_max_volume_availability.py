#!/usr/bin/env python
# coding: utf-8
# %%
import pandas as pd

# %%
from eu_cbm_hat.core.continent import continent
runner = continent.combos['no_management'].runners['FI'][-1]
runner.post_processor.harvest.expected_provided("year")

# %%
# #Explore solutions for harvest volume
# 
# Step1. Run "harvest_exp_prov_all_countries" script, save the output file "harv_reference.csv", 
# then extract the timeseries values of IRW only, "tot_irw_vol_avail". 
# 
# Step2. Replace these values in 'eu_cbm_data/domestic_harvest/irw_demand.csv, and run again.
# 
# Step3. Do Step1 again, save "harv_first_interation. csv", then Step2 again. In the reference file, to compare the values for "tot_irw_vol_avail"
# 
# Step4, Step 5, ..... until the difference between succesive outputs of "tot_irw_vol_avail" are within +/- 5% for entire time series. 

# # Iterations with IRW

# %%
from eu_cbm_hat.core.continent import continent
from eu_cbm_hat.post_processor.agg_combos import harvest_exp_prov_all_countries
import pandas
pandas.set_option('display.precision', 0) # Display rounded numbers
harv_data = harvest_exp_prov_all_countries("no_management", "year")


# %%
import os

# %%
from eu_cbm_hat import eu_cbm_data_pathlib
eu_cbm_data_pathlib

# %%
# add an index to data
harv_data.columns 

# %%
#add iter_data to initial data
harv_data.to_csv(continent.base_dir +'harvest_data_reference.csv', mode='w', index=False, header=True)

# %%
harv_data

# %% [markdown]
# **Create the IRW demand input files for initial run**

# %%
#keep only relevant columns with "tot_irw_vol_avail", and divide by 1000 
irw_data = harv_data[['country', 'year', 'tot_irw_vol_avail']]
irw_data['tot_irw_vol_avail']=irw_data['tot_irw_vol_avail']/1000

# %%
# keep only data after 2021
irw_data=irw_data[irw_data['year']>= 2021]

# %%
irw_data_wide = pd.pivot(irw_data, index='country', columns='year', values='tot_irw_vol_avail').fillna(0)
irw_data_wide=irw_data_wide.astype(int).reset_index()

# %%
# rename columns as required for inout files
irw_data_wide.columns = ['country']+[f'value_{year}' for year in irw_data_wide.columns[1:]]

# add missing elements
irw_data_wide['faostat_name'] = 'Industrial roundwood'
irw_data_wide['element'] = 'Production'
irw_data_wide['unit'] = '1000m3'

#create the inopout file foir irw
irw_data_wide.to_csv(continent.base_dir + '/domestic_harvest/mws_iter_1/' + 'irw_harvest.csv', mode='w', index=False, header=True)

# %%
irw_data_wide

# %% [markdown]
# **Create FW harvest input files for initial run**

# %%
#keep only relevant columns with "tot_irw_vol_avail", and divide by 1000 
fw_data = harv_data[['country', 'year', 'tot_fw_vol_avail']]
fw_data['tot_fw_vol_avail']=fw_data['tot_fw_vol_avail']/1000

# %%
# keep only data after 2021
fw_data=fw_data[fw_data['year']>= 2021]

# %%
fw_data_wide = pd.pivot(fw_data, index='country', columns='year', values='tot_fw_vol_avail').fillna(0)
fw_data_wide=fw_data_wide.astype(int).reset_index()

# %%
# rename columns as required for inout files
fw_data_wide.columns = ['country']+[f'value_{year}' for year in fw_data_wide.columns[1:]]

# add missing elements
fw_data_wide['faostat_name'] = 'Fuelwood'
fw_data_wide['element'] = 'Production'
fw_data_wide['unit'] = '1000m3'

#create the inopout file foir irw
fw_data_wide.to_csv(continent.base_dir + '/domestic_harvest/mws_iter_1/' + 'fw_harvest.csv', mode='w', index=False, header=True)

# %%

# %%

# %%

# %%

# %%

# %%

# %%

# %%

# %%




