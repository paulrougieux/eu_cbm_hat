#!/usr/bin/env python
# coding: utf-8
# %%
# Run "no_management" first, then itarate "mws"

# METHOD "TWO CONSTRAINTS": 90% NAI + SILVICULTURAL PRACTICES
# Step 1. Run "no_management" scenario, i.e. harvest demands close to 0 (IRW = 1000m3, FW = 10m3), On the output run "my_query.ipynb" to aggregate in parquet files.
# NB: silv practices are all assumed as "irw_and_fw" in the events_template.csv, and those silvicultural practices corresponding to "fw_only" in reference scenario are assumed as providing only 0.01% of IRW.

# Step 2. With PRESENT script "explore_max_volume_availability.py", extract the "nai_agb" from "no_management" parquet files, then assume NAI as beeing 90% of "nai_agb" (as m3 ob/ub) for ForAWS only (ForNAWS excluded) 
# and further convert NAI to IRW_demand (m3) only. Meanwhile FW_demand = 10 m3, as for "no_management". These demands would be saved as mws_nai_iter1/irw_demand.csv and mws_nai_iter1/fw_demand.csv

# Step 3. Run of "mws_nai_iter_1 sceanrio with the demands from Step 2 and no_management assumptions for silvicultural practices (as of NB above).

# %% [markdown]
# # Runs (for initial & all iterations)

# %%
# just modify the run name below

# %%
import pandas as pd
import os
from eu_cbm_hat import eu_cbm_data_pathlib
from eu_cbm_hat.core.continent import continent
eu_cbm_data_pathlib

# %%
# select the applicable scenario according the iteration step, to aggregate the outputs from running the previous scenario
#scenario = 'no_management'
#scenario = 'mws_nai_iter_1'
scenario = 'reference'

# %% [markdown]
# **Extract the total increment as "nai_agb" (m3 ub/ob)**

# %% [markdown]
# Create a merged dataframe from "harv_data" with "nai_agb_data" to be used for all iterations. Note that nai_agb is m3 ob, but assume this has no impact on the quantity of IRW or FW demands given stock difference.

# %%
# import NAI data, to include both merch and OWC 
from eu_cbm_hat.post_processor.agg_combos import nai_all_countries
#nai_data = nai_all_countries (scenario, 'status')

# %%
#minimize the df, we keep status as NAI would apply only to FAWS
nai_agb_data = nai_data[['combo_name', 'iso2_code', 'country', 'year', 'status', 'nai_agb']]
nai_agb_data

# %%
# organize NAI for ForAWS and ForNAWS, as MWS would only apply to ForAWS
nai_agb_status_data = pd.pivot(nai_agb_data, index=['combo_name', 'iso2_code', 'country', 'year'], columns='status', values='nai_agb').fillna(0)
nai_agb_status_data=nai_agb_status_data.astype(int).reset_index()
nai_agb_status_data=nai_agb_status_data.rename(columns = {'ForAWS' : 'nai_agb_ForAWS', 'ForNAWS' : 'nai_agb_ForNAWS'})
nai_agb_status_data.head(2)

# %%
# keep only data after 2021
nai_agb_status_data=nai_agb_status_data[nai_agb_status_data['year']>= 2021]
nai_agb_status_data = nai_agb_status_data[['combo_name', 'iso2_code', 'country', 'year', 'nai_agb_ForAWS']]

# %%
len(nai_agb_status_data)

# %% [markdown]
# **Extract harvest data (RW, IRW, FW)**

# %%
from eu_cbm_hat.post_processor.agg_combos import harvest_exp_prov_all_countries
pd.set_option('display.precision', 0) # Display rounded numbers
harv_data = harvest_exp_prov_all_countries(scenario, "year")


# %%
# keep only data after 2021
harv_data=harv_data[harv_data['year']>= 2021]

# %%
# vizualize data
harv_data.to_csv(continent.base_dir + '/domestic_harvest/' + scenario + '/harv_data.csv', mode='w', index=False, header=True)

# %%
len(harv_data)

# %%
# merge "harv_data" with "nai_agb_data"
df = harv_data.merge (nai_agb_status_data, on = ['combo_name', 'iso2_code', 'country', 'year'])
df.to_csv(continent.base_dir + '/domestic_harvest/' + scenario + '/harvest_data_nai.csv', mode='w', index=False, header=True)

# %%
#list(df.columns)

# %% [markdown]
# ## Step 2 to process only "no_management" ouput

# %% [markdown]
# At first iteration to keep FW = 10 m3, and assume IRW demand = 90% of nai_agb (in m3) resulted by running "no_management"in STEP1. Save the demands in domestic_harvest/mws_nai_iter_1, to be used for iteration 1. 

# %% [markdown]
# **Generate IRW demand for iteration 1**

# %%
# define the sub-folder scenario name for domestic_harvest
scenario_iter = 'mws_nai_iter_1'

# %%
#keep only relevant columns with "nai_agb_ForAWS", and divide by 1000 
from eu_cbm_hat import eu_cbm_data_pathlib
irw_data = df[['country', 'year', 'nai_agb_ForAWS']]
irw_data = irw_data.rename(columns = {'nai_agb_ForAWS' : 'tot_irw_vol_avail'})
# apply 90% of max wood supply as missing all NDs during the projected period, apply to aggregated values
irw_data['tot_irw_vol_avail']=0.9 *irw_data['tot_irw_vol_avail']/1000


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
irw_data_wide.to_csv(continent.base_dir + '/domestic_harvest/' + scenario_iter+ '/irw_harvest.csv', mode='w', index=False, header=True)

# %%
#irw_data_wide

# %% [markdown]
# **FW data for the iteration 1**

# %%
#keep the FW inputfrom "no_management" option, where FW = 1000 m3 per year
fw_data = pd.read_csv(continent.base_dir + '/domestic_harvest/' + scenario + '/fw_harvest.csv')
fw_data.to_csv(continent.base_dir + '/domestic_harvest/' + scenario_iter+ '/fw_harvest.csv', mode='w', index=False, header=True)

# %% [markdown]
# # STEP4. PROCESS the output of iteration 1, 2, ....

# %% [markdown]
# At second, third, etc iteration to keep FW = 10 m3, and assume IRW demand = 90% of nai_agb (in m3) resulted by running previous iterations. Save the demands in domestic_harvest/mws_nai_iter_x to be used for iteration x. 

# %% [markdown]
# Here the 'harvest_provided" would be corrected against 'nai_agb'

# %% [markdown]
# ## IRW

# %%
# define the sub-folder scenario name for domestic_harvest
scenario_iter = 'mws_nai_iter_2'
#scenario_iter = 'mws_nai_iter_3'

# %%
#keep only relevant columns with "nai_agb_ForAWS" from the output of previous uiteration, and divide by 1000 
from eu_cbm_hat import eu_cbm_data_pathlib
irw_data = df[['country', 'year', 'irw_harvest_prov_ub', 'irw_demand',  'nai_agb_ForAWS']]
# apply 90% of max wood supply as missing all NDs during the projected period
nai_agb_data['nai_agb_ForAWS'] = 0.9 * nai_agb_data['nai_agb_ForAWS']
irw_data = irw_data.rename(columns = {'nai_agb_ForAWS' : 'tot_irw_vol_avail'})
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
irw_data_wide.to_csv(continent.base_dir + '/domestic_harvest/' + scenario_iter+ '/irw_harvest.csv', mode='w', index=False, header=True)

# %% [markdown]
# ## FW

# %%
keep the FW inputfrom "no_management" option, where FW = 1000 m3 per year
fw_data = pd.read_csv(continent.base_dir + '/domestic_harvest/' + scenario + '/fw_harvest.csv')
fw_data.to_csv(continent.base_dir + '/domestic_harvest/' + scenario_iter+ '/fw_harvest.csv', mode='w', index=False, header=True)

# %%

# %%

# %%

# %%

# %%

# %%

# %%
irw_data[.head(2)

# %%
irw_data_wide = pd.pivot(irw_data, index='country', columns='year', values=['irw_harvest_prov_ub', 'irw_demand',  'nai_agb_ForAWS']).fillna(0)
irw_data_wide=irw_data_wide.astype(int).reset_index()

# %%
# correct the demand: 'irw_demand' <  'nai_agb_ForAWS', NB. nai_agb_ForAWS' is the new one after implementing theoretical mws from no_management

if 'irw_demand' > 'nai_agb_ForAWS'
    rez1 = 'nai_agb_ForAWS' - 'irw_demand'
    
    

# %%
# Calculate the last time series of irw_demand and fw_demand
def calculate_rev_d(row):
    
    if row['irw_demand'] > row['irw_harvest_prov_ub']:
        return row['irw_harvest_prov_ob']
    elif row['irw_harvest_prov_ob'] - row['irw_demand'] > 0:
        result = row['fw_harvest_prov_ob'] - (row['irw_harvest_prov_ob'] - row['irw_demand'])
        if result < 0 or result > row['fw_harvest_prov_ob']:
            return row['fw_harvest_prov'] == 0
        else:
            return row['fw_harvest_prov'] == result
    else:
        return 0

# Apply the function to each row
irw_data_iter['irw_harvest_prov'] = irw_data_iter.apply(calculate_rev_d, axis=1)
irw_data_iter['irw_harvest_prov'] = 1/1000*irw_data_iter['irw_harvest_prov_ob']

irw_data_iter

# %%
# keep only data after 2021
irw_data_iter=irw_data_iter[irw_data_iter['year']>= 2021]

# %%
irw_data_iter_wide = pd.pivot(irw_data_iter, index='country', columns='year', values='irw_harvest_prov').fillna(0)
irw_data_iter_wide=irw_data_iter_wide.astype(int).reset_index()

# %%
# rename columns as required for inout files
irw_data_iter_wide.columns = ['country']+[f'value_{year}' for year in irw_data_iter_wide.columns[1:]]

# add missing elements
irw_data_iter_wide['faostat_name'] = 'Industrial roundwood'
irw_data_iter_wide['element'] = 'Production'
irw_data_iter_wide['unit'] = '1000m3'

#create the inopout file foir irw
#irw_data_iter_wide.to_csv(continent.base_dir + '/domestic_harvest/' + scenario + '/irw_harvest.csv', mode='w', index=False, header=True)
irw_data_iter_wide.to_csv(continent.base_dir + '/domestic_harvest/' + '/mws_iter_3/'+ '/irw_harvest.csv', mode='w', index=False, header=True)


# %% [markdown]
# ## Last FW demand

# %%
#keep only relevant columns with "tot_irw_vol_avail", and divide by 1000 
#fw_data_iter = harv_data[['country', 'year', 'fw_harvest_prov_ob']]
#fw_data_iter['fw_harvest_prov'] = 1/1000*fw_data_iter['fw_harvest_prov_ob']

# %%
# Calculate the last time series of irw_demand and fw_demand
def calculate_rev_d(row):
    if row['irw_demand'] > row['irw_harvest_prov_ob']:
        return row['irw_harvest_prov_ob']
    elif row['irw_harvest_prov_ob'] - row['irw_demand'] > 0:
        result = row['fw_harvest_prov_ob'] - (row['irw_harvest_prov_ob'] - row['irw_demand'])
        if result < 0 or result > row['fw_harvest_prov_ob']:
            return 0
        else:
            return result
    else:
        return 0


# %%
# keep only data after 2021
fw_data_iter=irw_data_iter[irw_data_iter['year']>= 2021]
fw_data_iter['fw_harvest_prov_ob'] = 1/1000*fw_data_iter['fw_harvest_prov_ob']

# %%
fw_data_iter_wide = pd.pivot(fw_data_iter, index='country', columns='year', values='fw_harvest_prov_ob').fillna(0)
fw_data_iter_wide=fw_data_iter_wide.astype(int).reset_index()

# %%
# rename columns as required for inout files
fw_data_iter_wide.columns = ['country']+[f'value_{year}' for year in fw_data_iter_wide.columns[1:]]

# add missing elements
fw_data_iter_wide['faostat_name'] = 'Fuelwood'
fw_data_iter_wide['element'] = 'Production'
fw_data_iter_wide['unit'] = '1000m3'

#create the inopout file foir irw
fw_data_iter_wide.to_csv(continent.base_dir + '/domestic_harvest/' + '/mws_iter_3/'+ '/fw_harvest.csv', mode='w', index=False, header=True)

# %%
