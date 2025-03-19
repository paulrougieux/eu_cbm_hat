#!/usr/bin/env python
# coding: utf-8
# %%
# import FAO and CRF databases needed for HWP estimation. This will include all countries. 

# %%
from typing import Union, List
from functools import cached_property
from eu_cbm_hat import eu_cbm_data_pathlib
from eu_cbm_hat.post_processor.hwp_input import HWPInput
import numpy as np
import pandas as pd


# %%
class HWP(object):
    """Harvest Wood Products input and processing

    Usage:

        >>> from eu_cbm_hat.post_processor.hwp import HWP
        >>> hwp = HWP
        >>> hwp.rw_export_correction_factor

    """

    @cached_property
    def input(self):
        """Input data for HWP computations"""
        return HWPInput(self)

    
    @cached_property
    def rw_export_correction_factor(self):
        """ data 1961-2021 is from Forestry_E_Europe.csv
        this function allows the estimation of the factor "f" that represents the feedstock for the HWP of domestic origin, 
        after the correction for the export of roundwood, to be applied to eu_cbm_hat simulated IRW. 
        Even two types of fractions are calculated, fraction with string '_dom' is used further """
        """runner.post_processor.hwp.rw_export_correction_factor()"""

        # you should make this a method of HWP so that 
        # df_fao = self.faostat_bulk_data
        df_fao = self.input.faostat_bulk_data

        # remove rows which do not reffer to "quantity" from original data
        filter = df_fao['Element'].str.contains('Value')
        df_fao = df_fao[~filter].rename(columns = {'Item':'Item_orig', 'Element':'Element_orig'})

        # add lables used in the hwp scripts
        df = df_fao.merge(self.input.hwp_types, on = ['Item Code','Item_orig']).merge(self.input.eu_member_states, on = ['Area'])

        # Filter the columns that start with 'Y' and do not end with a letter
        keep_columns = ['Area Code', 'Area', 'Item Code','Item_orig', 'Item', 'Element Code', 'Element_orig', 'Unit']
        fao_stat = df.loc[:, keep_columns + df.columns[(df.columns.str.startswith('Y')) &
                                                       ~(df.columns.str.endswith(('F', 'N')))].tolist()]

        # Rename columns to remove 'Y' prefix for the year
        new_columns = {col: col[1:] if col.startswith('Y') else col for col in df.columns}
        fao_stat = fao_stat.rename(columns=new_columns)

        # reorganize table on long format
        fao_stat = fao_stat.melt(id_vars=['Area Code', 'Area', 'Item Code', 'Item_orig', 'Item','Element Code', 'Element_orig',
                                            'Unit'], var_name='year', value_name='Value')
        # add new labels on a new column for harmonization 

        shorts_mapping = {
                    'Production': 'prod',
                    'Import Quantity': 'imp',
                    'Export Quantity': 'exp'}
        fao_stat.loc[:,'Element'] = fao_stat.loc[:,'Element_orig'].map(shorts_mapping)

        #rename
        fao_stat=fao_stat.rename(columns = {'Area':'area'})  

        #aggregate on labels
        df_exp = (fao_stat
                    .groupby(['area', 'Element', 'year', 'Item'])
                    .agg(value = ('Value', 'sum'))
                    .reset_index()
                         )
        # create the input type
        df_exp ['type'] = df_exp ['Item'] .astype(str)+"_"+df_exp ['Element'].astype(str)

        # convert long to wide format
        df_exp= df_exp.pivot(index=['area', 'year'], columns=['type'], values=['value'])
        df_exp=df_exp.droplevel(None, axis=1).reset_index()

        # replacing NA to 0, so possible to make aritmetic operations
        df_exp=df_exp.fillna(0)

        # add con and broad aggregates, for information purpose only as split on con and broad is mantained
        # reduce to IRW
        df_exp['irw_prod'] = df_exp['irw_broad_prod'] + df_exp['irw_con_prod']
        df_exp['irw_exp'] = df_exp['irw_broad_exp'] + df_exp['irw_con_exp']
        df_exp['irw_imp'] = df_exp['irw_broad_imp'] + df_exp['irw_con_imp']

        #df_exp.to_csv('C:/CBM/exp.csv')
        # estimate the fractions of domestic in the country's feedstock: IRW, WP, PULP on con and broad
        #df_exp['fIRW_SW_WP_con'] = (df_exp['irw_con_prod']-df_exp['irw_con_exp'] )/(df_exp['irw_con_prod']+
        #                                                                            df_exp['irw_con_imp'] -
        #                                                                            df_exp['irw_con_exp'] )
        #df_exp['fIRW_SW_WP_broad'] = (df_exp['irw_broad_prod']-df_exp['irw_broad_exp'] )/(df_exp['irw_broad_prod']+
        #                                                                                  df_exp['irw_broad_imp'] - 
        #                                                                                  df_exp['irw_broad_exp'] )
        #df_exp['fPULP'] = (df_exp['wood_pulp_prod']-df_exp['wood_pulp_exp'] )/(df_exp['wood_pulp_prod']+
        #                                                                       df_exp['wood_pulp_imp'] -
        #                                                                       df_exp['wood_pulp_exp'] )

        df_exp['fIRW_SW_WP_con_dom'] = (df_exp['irw_con_prod']-df_exp['irw_con_exp'] )/df_exp['irw_con_prod']
        df_exp['fIRW_SW_WP_broad_dom'] = (df_exp['irw_broad_prod']-df_exp['irw_broad_exp'] )/df_exp['irw_con_prod']
        df_exp['fPULP_dom'] = (df_exp['wood_pulp_prod']-df_exp['wood_pulp_exp'] )/df_exp['irw_con_prod']

        # estimate the generic fraction of domestic feedstock
        df_exp['fIRW_SW_WP'] = (df_exp['irw_prod']-df_exp['irw_exp'] )/(df_exp['irw_prod']+
                                                                        df_exp['irw_imp'] -
                                                                        df_exp['irw_exp'] )

        # apply assumptions that f = 0 or f = 1 when f values are <0 or >1
        # when numerator is negative (export > production)
        # a value f =1 means entire amount corrected result as a domestic feedstock
        # a value f = 0 means there is no domestic contribution to the feedstock  
        #df_exp['fIRW_SW_WP_con'] = df_exp['fIRW_SW_WP_con'].mask(df_exp['fIRW_SW_WP_con']<0, 0)
        #df_exp['fIRW_SW_WP_broad'] = df_exp['fIRW_SW_WP_broad'].mask(df_exp['fIRW_SW_WP_broad']<0, 0)
        #df_exp ['fPULP']= df_exp['fPULP'].mask(df_exp['fPULP']<0, 0)

        df_exp['fIRW_SW_WP_con_dom'] = df_exp['fIRW_SW_WP_con_dom'].mask(df_exp['fIRW_SW_WP_con_dom']<0, 0)
        df_exp['fIRW_SW_WP_broad_dom'] = df_exp['fIRW_SW_WP_broad_dom'].mask(df_exp['fIRW_SW_WP_broad_dom']<0, 0)
        df_exp ['fPULP_dom']= df_exp['fPULP_dom'].mask(df_exp['fPULP_dom']<0, 0)

        # when both numerator and denominatore is negative (export > production & export > production + import)
        #df_exp['fIRW_SW_WP_con'] = df_exp['fIRW_SW_WP_con'].mask(df_exp['fIRW_SW_WP_con']>1, 0)
        #df_exp['fIRW_SW_WP_broad'] = df_exp['fIRW_SW_WP_broad'].mask(df_exp['fIRW_SW_WP_broad']>1, 0)
        #df_exp ['fPULP']= df_exp['fPULP'].mask(df_exp['fPULP']>1, 0)
        #df_exp['fIRW_SW_WP_con'] =df_exp['fIRW_SW_WP_con'].fillna(0)
        #df_exp['fIRW_SW_WP_broad'] =df_exp['fIRW_SW_WP_broad'].fillna(0)
        #df_exp['fPULP'] =df_exp['fPULP'].fillna(0)

        df_exp['fIRW_SW_WP_con_dom'] = df_exp['fIRW_SW_WP_con_dom'].mask(df_exp['fIRW_SW_WP_con_dom']>1, 0)
        df_exp['fIRW_SW_WP_broad_dom'] = df_exp['fIRW_SW_WP_broad_dom'].mask(df_exp['fIRW_SW_WP_broad_dom']>1, 0)
        df_exp ['fPULP_dom']= df_exp['fPULP_dom'].mask(df_exp['fPULP_dom']>1, 0)
        df_exp['fIRW_SW_WP_con_dom'] =df_exp['fIRW_SW_WP_con_dom'].fillna(0)
        df_exp['fIRW_SW_WP_broad_dom'] =df_exp['fIRW_SW_WP_broad_dom'].fillna(0)
        df_exp['fPULP_dom'] =df_exp['fPULP_dom'].fillna(0)

        
        # fractions of recycled paper feedstock, exports and exports
        df_exp['fREC_PAPER'] = (df_exp['recycled_paper_prod']-df_exp['recycled_paper_exp'] )/(df_exp['recycled_paper_prod']+
                                                                                    df_exp['recycled_paper_imp'] -
                                                                                    df_exp['recycled_paper_exp'] )

        #replacing NA to 0, so possible to make operations
        df_exp['fREC_PAPER'] =df_exp['fREC_PAPER'].fillna(0)
        df_exp['year'] =df_exp['year'].astype(int)
        return df_exp   


# %%
#initiate the class
hwp = HWP()

# These intermediate data frames are not needed,
# hwp.input.faostat_bulk_data can be called directly instead
faostat_bulk_data = hwp.input.faostat_bulk_data
hwp_types = hwp.input.hwp_types
eu_member_states = hwp.input.eu_member_states
euwrb_stat = hwp.input.euwrb_stat
fao_rw_prod_gapfilled = hwp.input.fao_rw_prod_gapfilled
crf_stat = hwp.input.crf_stat
subst_params = hwp.input.subst_params
subst_ref = hwp.input.subst_ref
silv_to_hwp = hwp.input.silv_to_hwp


# %%
# TODO remove this legacy function that just mirrors the HWP method
def rw_export_correction_factor():
    """Ugly function which should not exist"""
    return hwp.rw_export_correction_factor


# %%
def crf_semifinished_data():
        """ data 1961-2021 from common\hwp_crf_submission_2023.csv
        input timeseries of quantities of semifinshed products reported under the CRF"""
        df_crf=crf_stat.set_index(['area', 'year'])
        selector = '_crf'
        df_crf=df_crf.filter(regex=selector).reset_index()
        
        # remove strings in names
        df_crf.columns=df_crf.columns.str.replace(selector,'')
        df_crf=df_crf.set_index(['area', 'year'])
        
        # remove notation kew from CRF based data
        df_crf=df_crf.replace (["NO", 'NE', 'NA', 'NA,NE'], 0)
        df_crf=df_crf.fillna(0).astype(float)
        df_crf=df_crf.filter(regex='_prod').reset_index()
        df_crf['year'] =df_crf['year'].astype(int)
        return df_crf


# %%
# these are the historical domestic feedstock (corrected for export)
def hist_domestic_semifinished_production():
        """this merges the export with semifinished inputs to generate HWP of domestic origin, 
        in original unit m3 or t for 1961-2021"""
        
        df_exp = rw_export_correction_factor()
        df_crf = crf_semifinished_data()
        df_dp = df_exp.merge(df_crf, on=['year', 'area'])
        # generic factor is used
        df_dp ['sw_prod'] = df_dp ['sw_prod_m3']*df_dp ['fIRW_SW_WP'].astype(float) 
        df_dp['wp_prod'] = df_dp ['wp_prod_m3']*df_dp ['fIRW_SW_WP'].astype(float)
        #_dom is used
        df_dp ['pp_prod'] = df_dp ['pp_prod_t']*df_dp ['fPULP_dom'].astype(float)
        df_dp =df_dp [['area', 'year','sw_prod', 'wp_prod', 'pp_prod']]
        return df_dp


# %%
#def gap_filling_ms_crf():
def gap_filling_eu_totals():

    """add a EU total excluding the countries with incomplete time series, 
       to be used as proxy for gap filling of missing data by ms
       in original unit m3 or t for 1961-2021"""
    """runner.post_processor.hwp.rw_export_correction_factor()"""
    
    df_dp = hist_domestic_semifinished_production()
    df_dp = df_dp[['year', 'area', 'sw_prod', 'wp_prod', 'pp_prod']]
    df_ms = df_dp.rename (columns = {'sw_prod':'sw_prod_ms','wp_prod':'wp_prod_ms','pp_prod':'pp_prod_ms'})
    
    # Group by Area, Item, and Element
    grouped = df_ms.groupby(['year', 'area'])
   
    complete_groups = grouped.filter(lambda x: 
                                  not ((x['sw_prod_ms'] == 0).any() or 
                                       (x['wp_prod_ms'] == 0).any() or
                                       (x['pp_prod_ms'] == 0).any()))
    
    # Group by Area, Item, and Element and sum the amount
    df_eu = complete_groups.groupby(['year'])[['sw_prod_ms','wp_prod_ms','pp_prod_ms']].sum().reset_index()
    df_eu = df_eu.rename(columns={
        'sw_prod_ms': 'sw_prod_eu',
        'wp_prod_ms': 'wp_prod_eu',
        'pp_prod_ms': 'pp_prod_eu'
    })
    
    df_eu['EU'] = 'EU'
    df_crf_eu = df_eu.merge(df_ms, on = ['year'])
    df_crf_eu = df_crf_eu.sort_values (by = ['year','area'] )
    df_crf_eu.replace(0, np.nan, inplace=True)
    #df_crf_eu.to_csv('C:/CBM/interpolated.csv')
    return df_crf_eu


# %%
def gapfill_hwp_ms_backward(df):
    # Copy the original DataFrame to avoid modifying the original data for 1961-2021
    interpolated_ms = df.copy()
    
    # Calculate the ratio of irw_eu for each row to the next row
    interpolated_ms['sw_ratio'] = interpolated_ms['sw_prod_eu'].shift(-1) / interpolated_ms['sw_prod_eu']
    interpolated_ms['wp_ratio'] = interpolated_ms['wp_prod_eu'].shift(-1) / interpolated_ms['wp_prod_eu']
    interpolated_ms['pp_ratio'] = interpolated_ms['pp_prod_eu'].shift(-1) / interpolated_ms['pp_prod_eu']
    
    # Reset the index to ensure consecutive integers
    interpolated_ms.reset_index(drop=True, inplace=True)
    
    # Reverse the DataFrame to fill missing values in reverse order
    interpolated_ms = interpolated_ms.iloc[::-1]
    
    # Fill missing values in new_irw_ms using the ratio
    for index, row in interpolated_ms.iterrows():
        if pd.isnull(row['sw_prod_ms']):
            next_value = interpolated_ms.at[index + 1, 'new_sw_ms']
            if not pd.isnull(next_value):
                interpolated_ms.at[index, 'new_sw_ms'] = int(next_value / row['sw_ratio'])
            else:
                interpolated_ms.at[index, 'new_sw_ms'] = next_value  # Keep NaN if next value is NaN
        else:
            interpolated_ms.at[index, 'new_sw_ms'] = row['sw_prod_ms']
       
    for index, row in interpolated_ms.iterrows():
        if pd.isnull(row['wp_prod_ms']):
            next_value = interpolated_ms.at[index + 1, 'new_wp_ms']
            if not pd.isnull(next_value):
                interpolated_ms.at[index, 'new_wp_ms'] = int(next_value / row['wp_ratio'])
            else:
                interpolated_ms.at[index, 'new_wp_ms'] = next_value  # Keep NaN if next value is NaN
        else:
            interpolated_ms.at[index, 'new_wp_ms'] = row['wp_prod_ms']
            
    for index, row in interpolated_ms.iterrows():
        if pd.isnull(row['pp_prod_ms']):
            next_value = interpolated_ms.at[index + 1, 'new_pp_ms']
            if not pd.isnull(next_value):
                interpolated_ms.at[index, 'new_pp_ms'] = int(next_value / row['pp_ratio'])
            else:
                interpolated_ms.at[index, 'new_pp_ms'] = next_value  # Keep NaN if next value is NaN
        else:
            interpolated_ms.at[index, 'new_pp_ms'] = row['pp_prod_ms']       
    
         
    #for col in ['sw_ratio', 'wp_ratio', 'pp_ratio']:
    #    for index, row in interpolated_ms.iterrows():
    #        if pd.isnull(row[col]):
    #            next_value = interpolated_ms.at[index + 1, f'new_{col[:-6]}_ms']
    #            if not pd.isnull(next_value):
    #                interpolated_ms.at[index, f'new_{col[:-6]}_ms'] = int(next_value / row[col])
    #            else:
    #                interpolated_ms.at[index, f'new_{col[:-6]}_ms'] = next_value  # Keep NaN if next value is NaN
    #        else:
    #            interpolated_ms.at[index, f'new_{col[:-6]}_ms'] = row[col]
    
    # Reverse the DataFrame back to the original order
    interpolated_ms = interpolated_ms.iloc[::-1]
    c_sw = 0.225
    c_pw = 0.294
    c_pp = 0.450
    interpolated_ms['sw_domestic_tc'] = c_sw * interpolated_ms['new_sw_ms']
    interpolated_ms['wp_domestic_tc'] = c_pw * interpolated_ms['new_wp_ms']
    interpolated_ms['pp_domestic_tc'] = c_pp * interpolated_ms['new_pp_ms']
    
    # Drop the temporary 'ratio' column as it's no longer needed
    columns_to_drop = ['sw_ratio', 'wp_ratio', 'pp_ratio']
    interpolated_ms.drop(columns=columns_to_drop, inplace=True)
    
    # Convert 'new_irw_ms' column to integer
    #interpolated_ms#['new_sw_ms'] = interpolated_sw['new_sw_ms'].astype(int)
   
    return interpolated_ms


# %%
def fao_sw_to_irw ():
    """this estimates the average amount of sawnwood produced as average of 2021 and 2022 """
    """runner.post_processor.hwp.rw_export_correction_factor()"""
    #df_faostat = faostat_bulk_data
   
    # remove rows which do not reffer to "quantity" from original data
    filter = faostat_bulk_data['Element'].str.contains('Value')
    df_fao = faostat_bulk_data[~filter].rename(columns = {'Item':'Item_orig', 'Element':'Element_orig'})
   
    
    # add lables used in the hwp scripts
    df = df_fao.merge(hwp_types, on = ['Item Code','Item_orig']).merge(eu_member_states, on = ['Area'])
    
    # Filter the columns that start with 'Y' and do not end with a letter
    keep_columns = ['Area Code', 'Area', 'Item Code','Item_orig', 'Item', 'Element Code', 'Element_orig', 'Unit']
    df = df.loc[:, keep_columns + df.columns[(df.columns.str.startswith('Y')) & ~(df.columns.str.endswith(('F', 'N')))].tolist()]
    
    
    # Rename columns to remove 'Y' prefix for the year
    new_columns = {col: col[1:] if col.startswith('Y') else col for col in df.columns}
    df = df.rename(columns=new_columns)
    
    df_ms = df.query('Item == "sawnwood_broad" | Item == "sawnwood_con" ').copy()
    
    shorts_mapping = {
                'Production': 'prod',
                'Import Quantity': 'imp',
                'Export Quantity': 'exp'}
    df_ms.loc[:, 'Element_ms'] = df_ms.loc[:,'Element_orig'].map(shorts_mapping)
    
    first_year = 2021
    last_year = 2023
    df_ms = df_ms.loc[:, ['Area', 'Item', 'Element_ms'] + [str(year) for year in range(first_year, last_year)]]
    
    df_ms = pd.melt(df_ms, id_vars=['Area', 'Item', 'Element_ms'], var_name='Year', value_name='Value')
    
    df_ms = df_ms.groupby(['Area', 'Item', 'Element_ms', 'Year']).agg(
                            irw_ms=('Value', 'sum'),
    ).reset_index()
    
    # keep only 2021 and 2022
    df_ms=df_ms.query ('Element_ms == "prod" ')
    df_ms = df_ms.query('Year == "2021" | Year == "2022" ')
    
    average_sw_ms = df_ms.groupby(['Area', 'Item'])['irw_ms'].mean().reset_index()
    
    average_sw_ms = average_sw_ms.pivot(index= 'Area', columns='Item', values='irw_ms').reset_index()
    
    # add the share of sawnwood expected from the final cut
    average_sw_ms['final_cut_share_broad'] = 0.9
    average_sw_ms['final_cut_share_con'] = 0.95
        
    return average_sw_ms


# %%
def fao_wp_to_irw ():
    """this estimates the average amount of sawnwood produced as average of 2021 and 2022 """
    """runner.post_processor.hwp.rw_export_correction_factor()"""
    #df_faostat = faostat_bulk_data
   
    # remove rows which do not reffer to "quantity" from original data
    filter = faostat_bulk_data['Element'].str.contains('Value')
    df_fao = faostat_bulk_data[~filter].rename(columns = {'Item':'Item_orig', 'Element':'Element_orig'})
   
    
    # add lables used in the hwp scripts
    df = df_fao.merge(hwp_types, on = ['Item Code','Item_orig']).merge(eu_member_states, on = ['Area'])
    
    # Filter the columns that start with 'Y' and do not end with a letter
    keep_columns = ['Area Code', 'Area', 'Item Code','Item_orig', 'Item', 'Element Code', 'Element_orig', 'Unit']
    df = df.loc[:, keep_columns + df.columns[(df.columns.str.startswith('Y')) & ~(df.columns.str.endswith(('F', 'N')))].tolist()]
    
    
    # Rename columns to remove 'Y' prefix for the year
    new_columns = {col: col[1:] if col.startswith('Y') else col for col in df.columns}
    df = df.rename(columns=new_columns)
    
    df_ms = df.query(' Item == "wood_panels" ').copy()
    
    shorts_mapping = {
                'Production': 'prod',
                'Import Quantity': 'imp',
                'Export Quantity': 'exp'}
    df_ms.loc[:,'Element_ms'] = df_ms.loc[:,'Element_orig'].map(shorts_mapping)
    
    first_year = 2021
    last_year = 2023
    df_ms = df_ms.loc[:, ['Area', 'Item', 'Element_ms'] + [str(year) for year in range(first_year, last_year)]]
    
    df_ms = pd.melt(df_ms, id_vars=['Area', 'Item', 'Element_ms'], var_name='Year', value_name='Value')
    
    df_ms = df_ms.groupby(['Area', 'Item', 'Element_ms', 'Year']).agg(
                            irw_ms=('Value', 'sum'),
    ).reset_index()
    
    # keep only 2021 and 2022
    df_ms=df_ms.query ('Element_ms == "prod" ')
    df_ms = df_ms.query('Year == "2021" | Year == "2022" ')
    
    average_wp_ms = df_ms.groupby(['Area', 'Item'])['irw_ms'].mean().reset_index()
    
    average_wp_ms = average_wp_ms.pivot(index= 'Area', columns='Item', values='irw_ms').reset_index()
    
        
    return average_wp_ms


# %%
def fao_pulp_to_irw ():
    """this estimates the average amount of sawnwood produced as average of 2021 and 2022 """
    """runner.post_processor.hwp.rw_export_correction_factor()"""
    #df_faostat = faostat_bulk_data
   
    # remove rows which do not reffer to "quantity" from original data
    filter = faostat_bulk_data['Element'].str.contains('Value')
    df_fao = faostat_bulk_data[~filter].rename(columns = {'Item':'Item_orig', 'Element':'Element_orig'})
   
    
    # add lables used in the hwp scripts
    df = df_fao.merge(hwp_types, on = ['Item Code','Item_orig']).merge(eu_member_states, on = ['Area'])
    
    # Filter the columns that start with 'Y' and do not end with a letter
    keep_columns = ['Area Code', 'Area', 'Item Code','Item_orig', 'Item', 'Element Code', 'Element_orig', 'Unit']
    df = df.loc[:, keep_columns + df.columns[(df.columns.str.startswith('Y')) & ~(df.columns.str.endswith(('F', 'N')))].tolist()]
    
    
    # Rename columns to remove 'Y' prefix for the year
    new_columns = {col: col[1:] if col.startswith('Y') else col for col in df.columns}
    df = df.rename(columns=new_columns)
    
    df_ms = df.query('Item == "wood_pulp" ').copy()
    
    shorts_mapping = {
                'Production': 'prod',
                'Import Quantity': 'imp',
                'Export Quantity': 'exp'}
    df_ms.loc[:,'Element_ms'] = df_ms.loc[:,'Element_orig'].map(shorts_mapping)
    
    first_year = 2021
    last_year = 2023
    df_ms = df_ms.loc[:, ['Area', 'Item', 'Element_ms'] + [str(year) for year in range(first_year, last_year)]]
       
    df_ms = pd.melt(df_ms, id_vars=['Area', 'Item', 'Element_ms'], var_name='Year', value_name='Value')
    
    df_ms = df_ms.groupby(['Area', 'Item', 'Element_ms', 'Year']).agg(
                            irw_ms=('Value', 'sum'),
    ).reset_index()
    
    # keep only 2021 and 2022
    df_ms=df_ms.query ('Element_ms == "prod" ')
    df_ms = df_ms.query('Year == "2021" | Year == "2022" ')
    
    average_pulp_ms = df_ms.groupby(['Area', 'Item'])['irw_ms'].mean().reset_index()
    
    average_pulp_ms = average_pulp_ms.pivot(index= 'Area', columns='Item', values='irw_ms').reset_index()
        
    return average_pulp_ms


# %%
def substitution_factors ():
        "this merges the export with seminished inputs to generate HWP of domestic origin"
        df_subst_factors = subst_params.rename(columns={'Area': 'area'}) 
        return df_subst_factors


# %%
def gap_filling_irw_faostat():
    """this function allows the gapfilling of production, import and export of roundwood based on FAOSTAT data, 
    i.e., applied to the a quantity result in the domestic amount"""
    """runner.post_processor.hwp.rw_export_correction_factor()"""
    #df_faostat = faostat_bulk_data
   
    # remove rows which do not reffer to "quantity" from original data
    filter = faostat_bulk_data['Element'].str.contains('Value')
    df_fao = faostat_bulk_data[~filter].rename(columns = {'Item':'Item_orig', 'Element':'Element_orig'})
   
    
    # add lables used in the hwp scripts
    df = df_fao.merge(hwp_types, on = ['Item Code','Item_orig']).merge(eu_member_states, on = ['Area'])
    
    # Filter the columns that start with 'Y' and do not end with a letter
    keep_columns = ['Area Code', 'Area', 'Item Code','Item_orig', 'Item', 'Element Code', 'Element_orig', 'Unit']
    df = df.loc[:, keep_columns + df.columns[(df.columns.str.startswith('Y')) & ~(df.columns.str.endswith(('F', 'N')))].tolist()]
    
    
    # Rename columns to remove 'Y' prefix for the year
    new_columns = {col: col[1:] if col.startswith('Y') else col for col in df.columns}
    df = df.rename(columns=new_columns)
   
    df_ms = df.query('Item == "irw_broad" | Item == "irw_con" ').copy()
    
    shorts_mapping = {
                'Production': 'prod',
                'Import Quantity': 'imp',
                'Export Quantity': 'exp'}
    df_ms.loc[:,'Element_ms'] = df_ms.loc[:,'Element_orig'].map(shorts_mapping)
    
    df_ms = df_ms[[ 'Area', 'Item', 'Element_ms','1961', '1962', '1963', '1964', '1965', '1966',
       '1967', '1968', '1969', '1970', '1971', '1972', '1973', '1974', '1975',
       '1976', '1977', '1978', '1979', '1980', '1981', '1982', '1983', '1984',
       '1985', '1986', '1987', '1988', '1989', '1990', '1991', '1992', '1993',
       '1994', '1995', '1996', '1997', '1998', '1999', '2000', '2001', '2002',
       '2003', '2004', '2005', '2006', '2007', '2008', '2009', '2010', '2011',
       '2012', '2013', '2014', '2015', '2016', '2017', '2018', '2019', '2020',
       '2021', '2022']]
    
    df_ms = pd.melt(df_ms, id_vars=['Area', 'Item', 'Element_ms'], var_name='Year', value_name='Value')
    
    df_ms = df_ms.groupby(['Area', 'Item', 'Element_ms', 'Year']).agg(
                            irw_ms=('Value', 'sum'),
    ).reset_index()
    
    #df_ms.to_csv('C:/CBM/df_ms.csv')
    
    # Group by Area, Item, and Element
    grouped = df_ms.groupby(['Area', 'Item', 'Element_ms'])

    # Filter out groups where any value is zero within the time series
    complete_groups = grouped.filter(lambda x: not (x['irw_ms'] == 0).any())

    # Group by Area, Item, and Element and sum the amount
    df_eu = complete_groups.groupby(['Item', 'Element_ms', 'Year'])['irw_ms'].sum().reset_index()
    df_eu =df_eu.rename(columns = {'irw_ms':'irw_eu', 'Element_ms':'Element_eu'})
    
    df_faostat = df_ms.merge(df_eu, on = ['Item','Year'])
    #df_faostat = df_faostat.sort_values (by = ['Area','Item', 'Element', 'Year'] )
    df_faostat.replace(0, np.nan, inplace=True)
        
    #df_faostat.to_csv('C:/CBM/df_faostat.csv')
    return df_faostat


# %%
def gapfill_irw_ms_backward(df):
    # Copy the original DataFrame to avoid modifying the original data
    interpolated_df = df.copy()
    interpolated_df=interpolated_df.sort_values(by = ['Year'], ascending=True).sort_values(by = ['Item','Element_ms'])
    
    # Calculate the ratio of irw_eu for each row to the next row
    interpolated_df['ratio'] = interpolated_df['irw_eu'].shift(-1) / interpolated_df['irw_eu']
    
    # Reset the index to ensure consecutive integers
    interpolated_df.reset_index(drop=True, inplace=True)
    
    # Reverse the DataFrame to fill missing values in reverse order
    interpolated_df = interpolated_df.iloc[::-1]
    
    # Fill missing values in new_irw_ms using the ratio
    for index, row in interpolated_df.iterrows():
        if pd.isnull(row['irw_ms']):
            next_value = interpolated_df.at[index + 1, 'new_irw_ms']
            if not pd.isnull(next_value):
                interpolated_df.at[index, 'new_irw_ms'] = int(next_value / row['ratio'])
            else:
                interpolated_df.at[index, 'new_irw_ms'] = next_value  # Keep NaN if next value is NaN
        else:
            interpolated_df.at[index, 'new_irw_ms'] = row['irw_ms']
    
    # Reverse the DataFrame back to the original order
    interpolated_df = interpolated_df.iloc[::-1]
    
    # Drop the temporary 'ratio' column as it's no longer needed
    interpolated_df.drop(columns=['ratio'], inplace=True)
    
    # Convert 'new_irw_ms' column to integer
    interpolated_df['new_irw_ms'] = interpolated_df['new_irw_ms'].astype(int)
    #interpolated_df.to_csv('C:/CBM/interpolated.csv')
    
    return interpolated_df


# %%
def eu_wrb():
    
    sankey_rw_prod_in = euwrb_stat
    
    #retain only rows relevant for production of hwp
    sankey_rw_prod_in_hwp=sankey_rw_prod_in[sankey_rw_prod_in['label']!= 'trade']
    
    #load quantities from orih=ginal database
    sankey_rw_prod_in_hwp= sankey_rw_prod_in_hwp[['scenario','country','year', 'label', 'data']].dropna()
    
    sankey_rw_prod_in_hwp =sankey_rw_prod_in_hwp.pivot(index=['scenario','country','year'], columns='label', values='data').reset_index()
   
    sankey_rw_prod_in_hwp=sankey_rw_prod_in_hwp.reset_index()
    
    #sankey_rw_prod_in_hwp.to_csv('C:/CBM/hwp.csv')   
    
    # the sum of all semifinshed products converted to C
    c_sw = 0.225
    c_pw = 0.294
    c_pp = 0.450
    wd_con_broad = 0.5
    c_fraction = 0.5
    sankey_rw_prod_in_hwp['c_hwp_fao'] = 1*(sankey_rw_prod_in_hwp['pan_ind2fibboa']*c_pw+
                                            sankey_rw_prod_in_hwp['pan_ind2partboa']*c_pw+
                                            sankey_rw_prod_in_hwp['pan_ind2plyven']*c_pw+
                                            sankey_rw_prod_in_hwp['rw4mat2pu_ind']*c_pp+
                                            sankey_rw_prod_in_hwp['saw_ind2sawnw']*c_sw)
    
    #keep only the total C in all semifinished products
    sankey_c_semifinshed_faostat = sankey_rw_prod_in_hwp[['country','year','c_hwp_fao' ]]
    
    #extract the share of sawnwood in total solid production
    sankey_rw_prod_in_hwp['fSW']  =  sankey_rw_prod_in_hwp['saw_ind2sawnw']/sankey_rw_prod_in_hwp['rw_tot2rw4mat']
    
    # production of paper in total solid production, original excel formula: PP = if(rw4mat2pu_ind = 0,0, pu4pa2pap_ind)
    sankey_rw_prod_in_hwp['fPP']=sankey_rw_prod_in_hwp['rw4mat2pu_ind']/sankey_rw_prod_in_hwp['rw_tot2rw4mat']
    
    # deduct the inflow of recycled wood
    # 1st step, define the share of fibboa and partboa in their total
    sankey_rw_prod_in_hwp['fibboa_share'] = sankey_rw_prod_in_hwp['pan_ind2fibboa']/(sankey_rw_prod_in_hwp['pan_ind2fibboa']+sankey_rw_prod_in_hwp['pan_ind2partboa'])
    sankey_rw_prod_in_hwp['partboa_share'] = sankey_rw_prod_in_hwp['pan_ind2partboa']/(sankey_rw_prod_in_hwp['pan_ind2fibboa']+sankey_rw_prod_in_hwp['pan_ind2partboa'])
    
    # 2nd step, further split the total rec wood panels on the two destinations, fibboa and partboa
    sankey_rw_prod_in_hwp['Qfibboa']= sankey_rw_prod_in_hwp['pcw2pan_ind'] * sankey_rw_prod_in_hwp['fibboa_share']
    sankey_rw_prod_in_hwp['Qpartboa']= sankey_rw_prod_in_hwp['pcw2pan_ind'] * sankey_rw_prod_in_hwp['partboa_share']
    
    # 3rd step, estimate production of panels from domestic roundwood, excluding PWC feedstock
    sankey_rw_prod_in_hwp['wp_sum']=sankey_rw_prod_in_hwp['pan_ind2fibboa'] + (sankey_rw_prod_in_hwp['pan_ind2partboa']-sankey_rw_prod_in_hwp['Qpartboa'])+ (sankey_rw_prod_in_hwp['pan_ind2plyven']-sankey_rw_prod_in_hwp['Qfibboa'])
    sankey_rw_prod_in_hwp['wp_sum']
    
    #finally estimate the share of WP in total solid production
    sankey_rw_prod_in_hwp['fWP'] = sankey_rw_prod_in_hwp['wp_sum']/sankey_rw_prod_in_hwp['rw_tot2rw4mat']
    
    
    #sankey_rw_prod_in_hwp
    # # keep the use of post_consumer wood in panels, as it is used in substitution later
    #shares of panels types within WP
    sankey_rw_prod_in_hwp['fWP_fibboa'] = sankey_rw_prod_in_hwp['pan_ind2fibboa']/sankey_rw_prod_in_hwp['wp_sum']
    sankey_rw_prod_in_hwp['fWP_partboa'] = sankey_rw_prod_in_hwp['pan_ind2partboa']/sankey_rw_prod_in_hwp['wp_sum']
    sankey_rw_prod_in_hwp['fWP_pv'] = sankey_rw_prod_in_hwp['pan_ind2plyven']/sankey_rw_prod_in_hwp['wp_sum']
    
    # load recyled wood and paper
    sankey_rw_prod_in_hwp['rec_wood_swe_m3']=sankey_rw_prod_in_hwp['pcw2pan_ind']
    sankey_rw_prod_in_hwp['rec_paper_swe_m3']=sankey_rw_prod_in_hwp['recpap2pap_ind']
    
    # load the export of roundwood
    #retain only rows relevant for production of hwp
    
    
    
    sankey_rw_prod_in_exp=sankey_rw_prod_in[(sankey_rw_prod_in['label'] == 'rw_tot2rw4mat') | (sankey_rw_prod_in['label'] == 'pu4pa2pap_ind')]
    sankey_rw_prod_in_exp=sankey_rw_prod_in_exp[['scenario','country','year', 'data', 'unit', 'label']]
    sankey_rw_prod_in_exp=sankey_rw_prod_in_exp.pivot(index= ['scenario','country','year'] , columns='label' , values='data')
    sankey_rw_prod_in_exp ['rw_export'] =  sankey_rw_prod_in_exp['rw_tot2rw4mat']+sankey_rw_prod_in_exp['pu4pa2pap_ind']

    #sankey_rw_prod_in_exp
    #assess_shares = sankey_rw_prod_in_hwp[['fSW', 'fWP','fPP']]
    
    # complete the db with needed information 
    #fSW = assess_shares.loc['cumulated_values', 'fSW']
    #fWP = assess_shares.loc['cumulated_values', 'fWP']
    #fPP = assess_shares.loc['cumulated_values', 'fPP']
    #fFW = assess_shares.loc['cumulated_values', 'fFW']
    #rec_wood_swe_m3 = sankey_rw_prod_in_hwp.rec_wood_swe_m3.mean()
    #rec_paper_swe_m3 = sankey_rw_prod_in_hwp.rec_paper_swe_m3.mean()
    
    # add further data needed for recycling later
    fWP_fibboa = sankey_rw_prod_in_hwp['fWP_fibboa'].mean()
    fWP_partboa = sankey_rw_prod_in_hwp['fWP_partboa'].mean()
    fWP_pv = sankey_rw_prod_in_hwp['fWP_pv'].mean()
    
    #reorganize 
    sankey_rw_prod = sankey_rw_prod_in_hwp[['scenario','country','year','fSW','fPP','fWP','fWP_fibboa','fWP_partboa','fWP_pv','rec_wood_swe_m3','rec_paper_swe_m3']].copy()
   
    #add absolute amounts of export of roundwood
    rw_export_thou_swe_m3= sankey_rw_prod_in_exp.rw_export.mean()
    sankey_rw_prod.loc[:, 'rw_export_thou_swe_m3'] = rw_export_thou_swe_m3
    
    # convert Sankey volume data to carbon, by taking into account the share of con to broad, and wd
    sankey_rw_prod['rw_export_tc']= 1000*wd_con_broad*c_fraction*sankey_rw_prod['rw_export_thou_swe_m3']

    # estimate the correction
    #retain only rows relevant with annual data on irw_amount allocated to products
    sankey_irw_solid=sankey_rw_prod_in[sankey_rw_prod_in['label'] == 'rw_tot2rw4mat']
    #sankey_irw_solid
    
    return sankey_rw_prod


# %%
def silv_grouping_to_hwp():
    Silv_grouping_to_hwp = silv_to_hwp
    Silv_grouping_to_hwp=Silv_grouping_to_hwp.rename(columns = {'dist_type_name':'disturbance_type'})
    return Silv_grouping_to_hwp
