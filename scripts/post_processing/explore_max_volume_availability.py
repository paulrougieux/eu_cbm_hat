#!/usr/bin/env python
# coding: utf-8
# %%
# Run "no_management" and "mws"
# Step 1. Run "no_management" scenario, i.e. harvest demands close to 0. 

# Step 2. Run "harvest_exp_prov_all_countries" script on the output of "no_management",subset  
# from the output file "harv_data.csv" the timeseries values of IRW ("tot_irw_vol_avail") 
# and FW ("tot_fw_vol_avail") as the demands for the first iteration (mws_iter_1), 
# they are saved as "mrw_iter_1/irw_demand.csv" and "mrw_iter_1/fw_demand". A new combo mws_iter_1 is needed. 
# The output table contains:
# a) "to_product" = "irw_to_product"+"fw_to_product" (implicit o.b.) as tC;
# b1) "harvest_prov_ub" = "irw_harvest_prov_ub" + "fw_harvest_prov_ub" as m3, and
# b2) "harvest_prov_ob" = "irw_harvest_prov_ob" + "fw_harvest_prov_ob" as m3
 
# Step 2. Run "mws_iter" scenario, i.e. harvest demands close to availability as of evennts_template. 
# Save the output of the runs as "harv_data_iter_1,2,3.csv"
# 
# Step 3. 


#Do Step1 again, save "harv_first_interation. csv", then Step2 again. In the reference file, to compare the values for "tot_irw_vol_avail"
# 
# Step4, Step 5, ..... until the difference between succesive outputs of "tot_irw_vol_avail" are within +/- 5% for entire time series. 

# # Iterations with IRW

# %% [markdown]
# # Run (Step 1, Step 3)

# %%
import pandas as pd

# %%
<<<<<<< HEAD
# #Explore solutions for harvest volume
# 
# Step1. Run "harvest_exp_prov_all_countries" script, save the output file "harv_reference.csv", 
# then extract the timeseries values: "tot_irw_vol_avail" and "tot_fw_vol_avail". Save the time series which will serve as input to 1st iteration in 
# eu_cbm_data/domestic_harvest/mws_iter_1/irw_demand.csv and /fw_demand.csv.





# Step2. Set the first iteration, mws_iter. Replace these values in 'eu_cbm_data/domestic_harvest/ / irw_demand.csv, and run again.
# 
# Step3. Do Step1 again, save "harv_first_interation. csv", then Step2 again. In the reference file, to compare the values for "tot_irw_vol_avail"
# 
# Step4, Step 5, ..... until the difference between succesive outputs of "tot_irw_vol_avail" are within +/- 5% for entire time series. 

# # Iterations with IRW
=======
from eu_cbm_hat.core.continent import continent
# define scenario to run
scenario = 'no_management'
#scenario = 'mws_iter_1'
# run next for the "no_management" reference data
runner = continent.combos[scenario].runners['FI'][-1]
# run next for the iterations
runner.post_processor.harvest.expected_provided("year")
>>>>>>> aeb06e69da6937369cfd805fe8da5d056ca63487

# %%
from eu_cbm_hat.core.continent import continent
from eu_cbm_hat.post_processor.agg_combos import harvest_exp_prov_all_countries
import pandas
pandas.set_option('display.precision', 0) # Display rounded numbers
harv_data = harvest_exp_prov_all_countries("no_management", "year")


# %%
# add an index to data
harv_data.columns 

# %%
#add iter_data to initial data
<<<<<<< HEAD
#harv_data.to_csv(continent.base_dir +'harvest_data_reference.csv', mode='w', index=False, header=True)
=======
harv_data.to_csv(continent.base_dir +'harvest_data.csv', mode='w', index=False, header=True)

# %%
harv_data

# %% [markdown]
# *** Step 2 to process only "no_management" ouput ***
>>>>>>> aeb06e69da6937369cfd805fe8da5d056ca63487

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

<<<<<<< HEAD
# %%

# %%

# %%

# %%

# %%

# %%

# %%
=======
# %% [markdown]
# * Step 4 to process only "no_management" ouput *

# %% [markdown]
# **Create the IRW demand for 1-n iterations**

# %%
iteration = 1

# %%
#keep only relevant columns with "tot_irw_vol_avail", and divide by 1000 
irw_data_iter = harv_data[['country', 'year', 'irw_harvest_prov_ub']]
irw_data_iter['irw_harvest_prov_ub']=irw_data_iter['irw_harvest_prov_ub']/1000

# %%
# keep only data after 2021
irw_data_iter=irw_data_iter[irw_data_iter['year']>= 2021]

# %%
irw_data_iter_wide = pd.pivot(irw_data_iter, index='country', columns='year', values='irw_harvest_prov_ub').fillna(0)
irw_data_iter_wide=irw_data_iter_wide.astype(int).reset_index()

# %%
# rename columns as required for inout files
irw_data_iter_wide.columns = ['country']+[f'value_{year}' for year in irw_data_iter_wide.columns[1:]]

# add missing elements
irw_data_iter_wide['faostat_name'] = 'Industrial roundwood'
irw_data_iter_wide['element'] = 'Production'
irw_data_iter_wide['unit'] = '1000m3'

#create the inopout file foir irw
irw_data_iter_wide.to_csv(continent.base_dir + '/domestic_harvest/mws_iter + f'{iteration}'/' + 'irw_harvest.csv', mode='w', index=False, header=True)

# %%
irw_data_iter_wide

# %% [markdown]
# **Create FW harvest input files for 1-n iterations**

# %%
#keep only relevant columns with "tot_irw_vol_avail", and divide by 1000 
fw_data_iter = harv_data_iter[['country', 'year', 'fw_harvest_prov_ub']]
fw_data_iter['fw_harvest_prov_ub']=fw_data_iter['fw_harvest_prov_ub']/1000

# %%
# keep only data after 2021
fw_data_iter=fw_data_iter[fw_data_iter['year']>= 2021]

# %%
fw_data_iter_wide = pd.pivot(fw_data_iter, index='country', columns='year', values='fw_harvest_prov_ub').fillna(0)
fw_data_iter_wide=fw_data_iter_wide.astype(int).reset_index()

# %%
# rename columns as required for inout files
fw_data_iter_wide.columns = ['country']+[f'value_{year}' for year in fw_data_iter_wide.columns[1:]]

# add missing elements
fw_data_iter_wide['faostat_name'] = 'Fuelwood'
fw_data_iter_wide['element'] = 'Production'
fw_data_iter_wide['unit'] = '1000m3'

#create the inopout file foir irw
fw_data_iter_wide.to_csv(continent.base_dir + '/domestic_harvest/mws_iter_1/' + 'fw_harvest.csv', mode='w', index=False, header=True)
>>>>>>> aeb06e69da6937369cfd805fe8da5d056ca63487

# %%

# %%




