#!/usr/bin/env python
# coding: utf-8
# %%
"""Import FAO and CRF databases needed for HWP estimation. This will include all countries.


Usage: 

    >>> from eu_cbm_hat.post_processor.hwp_common_input import hwp_common_input
    >>> hwp_common_input.crf_semifinished_data

"""

import math
import re
import warnings
import numpy as np
import pandas as pd
import itertools
from functools import cached_property
from eu_cbm_hat.constants import eu_cbm_data_pathlib


def generate_dbh_intervals():
    """Generate DBH intervals for a dictionary mapping"""
    base_range = np.arange(0, 100, 2.5)
    intervals = [f"[{start:.1f}, {start+2.5:.1f})" for start in base_range]
    return {f"dbh_class_{i+1}": intervals[i] for i in range(1, 40)}


DBH_CLASSES = generate_dbh_intervals()


def backfill_avg_first_n_years(df, var, n):
    """Backfill with the average of the first n years

    Example

        >>> data = {
        ...     "area": ["Bulgaria", "Bulgaria", "Bulgaria", "Germany", "Germany", "Germany"],
        ...     "year": [1960, 1961, 1962, 1960, 1961, 1962],
        ...     "sw_prod_m3": [np.nan, np.nan, 1000, np.nan, 2000, 3000]
        ... }
        >>> df = pd.DataFrame(data)
        >>> df_filled2 = backfill_avg_first_n_years(df, var="sw_prod_m3", n=2)
        >>> df_filled1 = backfill_avg_first_n_years(df, var="sw_prod_m3", n=1)

    """
    index = ["area", "year"]
    df = df.sort_values(index)
    # Interpolate for the gaps between existing years of data (not at the beginning)
    df[var] = df.groupby("area")[var].transform(pd.Series.interpolate)
    # Compute the average of the first 2 years of data
    selector = ~df[var].isna()
    df2 = df.loc[selector, index + [var]].groupby(["area"]).head(n)
    df2 = df2.groupby("area").agg(mean=(var, "mean")).reset_index()
    df = df.merge(df2, on="area", how="left")
    # Use this to fill the remaining NA values at the beginning of the series
    df[var] = df[var].fillna(df["mean"])
    df.drop(columns="mean", inplace=True)
    return df


class HWPCommonInput:
    """Input data for Harvested Wood Product sink computation

    Test a change in n year back fill

        >>> from eu_cbm_hat.post_processor.hwp_common_input import hwp_common_input
        >>> # Print the default value and keep it for this first display of the df
        >>> print("Default value of n_years_for_backfill:", hwp_common_input.n_years_for_backfill)
        >>> print(hwp_common_input.prod_from_dom_harv_stat)
        >>> # Change the number of first years used for the average and backfill
        >>> hwp_common_input.n_years_for_backfill = 10
        >>> print(hwp_common_input.prod_from_dom_harv_stat)

    Set export import factors to one  equivalent to setting export and import
    values to zero in the estimation of the production from domestic harvest.
    In other words, assume that all secondary products production is made from
    domestic industrial roundwood harvest.

        >>> from eu_cbm_hat.post_processor.hwp_common_input import hwp_common_input
        >>> print("no_export_no_import:", hwp_common_input.no_export_no_import)
        >>> print(hwp_common_input.rw_export_correction_factor)
        >>> print(hwp_common_input.prod_from_dom_harv_stat)
        >>> # Change the export import factors to one
        >>> hwp_common_input.no_export_no_import = True
        >>> print(hwp_common_input.rw_export_correction_factor)
        >>> print(hwp_common_input.prod_from_dom_harv_stat)

    """

    def __init__(self):
        self.common_dir = eu_cbm_data_pathlib / "common"
        # Constant Carbon Conversion Factors for semi finished products
        self.c_sw_broad = 0.225
        self.c_sw_con = 0.225
        self.c_wp = 0.294
        self.c_pp = 0.450
        # correct for humidity for recycled wood products, as the reported amounts are in t of fresh matter of collected material 
        self.humid_corr_wood = 0.15 # correction from conversion from reported fresh to dry 
        self.humid_corr_paper = 0.10 # correction from conversion from reported fresh to dry
        self.c_rwp = 0.5 # as of dry matter
        self.c_rpp = 0.7 # as of dry matter
        # N year parameter for the backfill_avg_first_n_years
        self.n_years_for_backfill = 3

    @cached_property
    def decay_params(self):
        """Decay parameters"""
        # Define half life in years
        hl_sw = 35
        hl_wp = 25
        hl_pp = 2
        hl_sw_wp = 30
        df = pd.DataFrame(
            {
                "log_2": [np.log(2)],
                "hl_sw": [hl_sw],
                "hl_wp": [hl_wp],
                "hl_pp": [hl_pp],
                "hl_sw_wp": [hl_sw_wp],
            }
        )
        # Prepare the params according the needs in HWP calcualtions
        # calculate **k_** the decay constant for each of SW, WP, PP
        df = df.assign(
            k_sw=(df.log_2 / df.hl_sw),
            k_wp=(df.log_2 / df.hl_wp),
            k_pp=(df.log_2 / df.hl_pp),
            k_sw_wp=(df.log_2 / df.hl_sw_wp),
        )
        # Calculate **e_** the remaining C stock from the historical stock
        # e-k (see see eq. 2.8.5 (gpg)),
        df = df.assign(
            e_sw=np.exp(-df.k_sw),
            e_wp=np.exp(-df.k_wp),
            e_pp=np.exp(-df.k_pp),
            e_sw_wp=np.exp(-df.k_sw_wp),
        )
        # Calculate **k1_** the remaining from the current year inflow
        # k1=(1-e-k)/k (see eq. 2.8.2 (gpg))
        df = df.assign(
            k1_sw=(1 - df.e_sw) / df.k_sw,
            k1_wp=(1 - df.e_wp) / df.k_wp,
            k1_pp=(1 - df.e_pp) / df.k_pp,
        )
        return df

    @cached_property
    def hwp_types(self):
        # this is the types of wood use data to be retrieved from FAOSTAT
        HWP_types = pd.read_csv(eu_cbm_data_pathlib / "common/hwp_types.csv")
        return HWP_types

    @cached_property
    def eu_member_states(self):
        """Data frame of EU MS"""
        df = pd.read_csv(eu_cbm_data_pathlib / "common/country_codes.csv")
        df = df[["country"]]
        df = df.rename(columns={"country": "Area"})
        return df

    @cached_property
    def faostat_bulk_data(self):
        """faostat as downloaded as bulk from FAOSTAT, namely
        "Forestry_E_Europe" is a bulk download from  FAOSTAT."""
        df = pd.read_csv(
            eu_cbm_data_pathlib / "common/Forestry_E_Europe.csv", low_memory=False
        )
        # Replace Item from 'OSB' to 'Oriented strand board (OSB)' as of latest FAOSTAT download
        # Replace 'OSB' with 'Oriented strand board (OSB)'
        df['Item'] = df['Item'].replace({'Oriented strand board (OSB)':'OSB', 'Sawnwood, non-coniferous all':'Sawnwood, non-coniferous'})
        # Rename countries
        area_dict = {"Netherlands (Kingdom of the)": "Netherlands"}
        df["Area"] = df["Area"].replace(area_dict)
        return df

    @cached_property
    def crf_stat(self):
        """crf sumbissions"""
        df = pd.read_csv(eu_cbm_data_pathlib / "common/hwp_crf_submission.csv")
        df = df.rename(columns={"country": "area"})
        # remove columns which have information purpose only, i.e. change compared to previous submission to unfccc
        df = df[['area', 'year', 'sw_prod_m3_crf', 'sw_imp_m3_crf', 'sw_exp_m3_crf',
                 'wp_prod_m3_crf', 'wp_imp_m3_crf', 'wp_exp_m3_crf', 'pp_prod_t_crf', 
                 'pp_imp_t_crf', 'pp_exp_t_crf']]
        # Convert other columns to numerical
        cols = df.columns.to_list()
        for col in cols[2:]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    @cached_property
    def ctf_unfccc(self):
        """Common Reporting Format CRF submissions of green house gas reported
        by the countries to the UNFCCC.

        Note: the old name  of the input table was Common Reporting Format, the
        new name is CTF for Common Table Format.
        """
        # Import data from CRF database, remove NaNs. Remove also the plots with 0 vol, but with agb
        df_wide = pd.read_csv(eu_cbm_data_pathlib / "common/crf_data.csv")
        indicator = "crf_hwp_tco2"
        selector = df_wide["indicator"] == indicator
        df_wide = df_wide[selector].copy()
        # Reshape to long format
        df = df_wide.melt(
            id_vars=["member_state", "indicator"], var_name="year", value_name=indicator
        )
        # convert to numeric
        df[indicator] = pd.to_numeric(df[indicator], errors="coerce")
        # Convert kilo tons to tons
        df[indicator] = df[indicator] * 1000
        return df

    @cached_property
    def subst_params(self):
        """Substitution parameters

        There are two types of variables:
        - the fraction variables mean how much is replaced.
        - the factor variables mean the actual GHG saving due to the
          substitution of that material.

        | Wood semi-finished product | Expected functionality                                         | Expected substitute    | Code     |
        |----------------------------|----------------------------------------------------------------|------------------------|----------|
        | Particle board             | Construction materials (e.g., structure)                       | Steel*                 | wp_pb_st |
        | Particle board             | Construction materials (e.g., floorings, interior decorations) | Cement and concrete**  | wp_pb_ce |
        | Particle board             | Other (e.g., furniture)                                        | Oil-based materials*** | wp_pb_om |
        | Fibre board                | Construction materials (e.g., structure)                       | Steel                  | wp_fb_st |
        | Fibre board                | Construction materials (e.g., insulation)                      | Cement and concrete    | wp_fb_ce |
        | Fibre board                | Other (e.g., floorings, interiors decorations)                 | Oil-based materials    | wp_fb_om |
        | Plywood and veneer         | Construction materials (e.g., floorings, interiors)            | Steel                  | wp_py_om |
        | Plywood and veneer         | Other (e.g., furniture)                                        | Cement and concrete    | wp_vn_om |
        | Sawnwood                   | Construction materials (e.g., structure)                       | Steel                  | sw_st    |
        | Sawnwood                   | Construction materials (e.g., structure)                       | Cement and concrete    | sw_ce    |
        | Sawnwood                   | Construction materials (e.g., floorings, insulation)           | Oil-based materials    | sw_fi_om |
        | Sawnwood                   | Other (e.g., furniture, interiors decorations, accents)        | Oil-based materials    | sw_fd_om |
        | Pulp and paper             | Other (e.g., domestic use)                                     | Oil-based materials    | pp_du_om |
        | Pulp and paper             | Other (e.g., textile)                                          | Oil-based materials    | pp_pp_tx |
        | Pulp and paper             | Other (e.g., packaging)                                        | Oil-based materials    | pp_pk_om |
        | Pulp and paper             | Other (e.g., furniture, interiors decorations)                 | Oil-based materials    | pp_fd_om |
        | Woodfuel                   | Other (e.g., materials obtained from biomass)                  | Oil-based materials    | wf_om    |
        | Woodfuel                   | Other (e.g., textile)                                          | Textile                | wf_tx    |
        | Woodfuel                   | Bioenergy (e.g., fuelmix)                                      | Oil-based materials    | wf_fu    |

        See report on HWP for more information.
        """
        df = pd.read_csv(eu_cbm_data_pathlib / "common/substitution_params.csv")
        return df

    @cached_property
    def hwp_fraction_semifinished_scenario(self):
        """Scenario of fraction of semi finished products"""
        df = pd.read_csv(
            eu_cbm_data_pathlib / "common/hwp_fraction_semifinished_scenario.csv"
        )
        return df

    @cached_property
    def split_wood_panels(self):
        """Split wood panels amount between particle board, fibre board and veneer.

        Keep only the average of the last 3 years.
        """

        df = self.fao_correction_factor.copy()
        selected_cols = [
            "wood_panels_prod",
            "fibboa_prod",
            "partboa_prod",
            "veneer_prod",  # reported by FAOSTAT as separate category, i.e., under sawnwood, but the life time is similar to partboa and fibboa
        ]
        selector = df["year"] > df["year"].max() - 3
        df = df.loc[selector, ["area", "year"] + selected_cols]
        # Compute the average
        df = df.groupby(["area"])[selected_cols].agg("mean").reset_index()
        # Compute the fraction
        df["fwp_fibboa"] = df["fibboa_prod"] / df["wood_panels_prod"]
        df["fwp_partboa"] = df["partboa_prod"] / df["wood_panels_prod"]

        # Note Veneer is not part of particle board and OSB
        # df["fwp_pv"] = df["veneer_prod"] / df["wood_panels_prod"]
        # Assert that the ratio sums to one
        cols = ["fwp_fibboa", "fwp_partboa"]  # , "fwp_pv"]
        sum_frac = df[cols].sum(axis=1)
        selector = np.isclose(sum_frac, 1)
        selector = (selector) | (sum_frac == 0)
        if not all(selector):
            msg = "The wood panels ratios do not sum to one. Check:\n"
            msg += f"{df.loc[~selector]}"
            raise ValueError(msg)
        return df

    @cached_property
    def subst_ref(self):
        """substitution reference scenario"""
        Subst_ref = pd.read_csv(
            eu_cbm_data_pathlib / "common/substitution_reference_scenario.csv"
        )
        return Subst_ref

    @cached_property
    def silv_to_hwp(self):
        # substitution reference scenario
        Silv_to_hwp = pd.read_csv(
            eu_cbm_data_pathlib / "common/silv_practices_to_hwp.csv"
        )
        return Silv_to_hwp

    @cached_property
    def irw_allocation_by_dbh(self):
        """IRW fraction by DBH classes with genus and forest type information

        Merge with the genus table to obtain the forest type information.

        DBH structure: (in cm) and threshold values:

             'dbh_class_1': (0.0, 2.5),
             'dbh_class_2': (2.6, 5.0),
             'dbh_class_3': (5.1, 7.5),
             'dbh_class_4': (7.6, 10.0),
             'dbh_class_5': (10.1, 12.5),
             'dbh_class_6': (12.6, 15.0), * threshold limit for pulplogs (100% pulpwood) for con and broad
             'dbh_class_7': (15.1, 17.5),
             'dbh_class_8': (17.6, 20.0),
             'dbh_class_9': (20.1, 22.5),
             'dbh_class_10': (22.6, 25.0),* threshold limit for sawlogs (<100% sawlog + <100% pulpood) for con
             'dbh_class_11': (25.1, 27.5),
             'dbh_class_12': (27.6, 30.0),
             'dbh_class_13': (30.1, 32.5),
             'dbh_class_14': (32.6, 35.0),
             'dbh_class_15': (35.1, 37.5),
             'dbh_class_16': (37.6, 40.0),
             'dbh_class_17': (40.1, 42.5),
             'dbh_class_18': (42.6, 45.0),* threshold limit for sawlogs (<100% sawlog + <100% pulpood) for broad
             'dbh_class_19': (45.1, 47.5),
             'dbh_class_20': (47.6, 50.0),
             .............................
             'dbh_class_38': (92.6, 95.0),
             'dbh_class_39': (95.1, 97.5),
             'dbh_class_40': (97.6, 100.0)

        """
        csv_path = eu_cbm_data_pathlib / "common" / "irw_allocation_by_dbh.csv"
        df = pd.read_csv(csv_path)
        df = df.merge(self.hwp_genus, on=["country", "genus"], how="left")

        # Check that proportions sum to one over the forest type and age class
        index = ["country", "mgmt_type", "mgmt_strategy", "forest_type", "age_class"]
        df_agg = (
            df.groupby(index)["fraction_theoretical_volume"].agg("sum").reset_index()
        )
        selector = ~np.isclose(df_agg["fraction_theoretical_volume"], 1)
        if any(selector):
            msg = "Some proportion in irw_allocation_by_dbh do not sum to one\n"
            msg += f"over the index: {index}\n"
            msg += f"CSV file path: {csv_path}\n"
            msg += f"{df_agg.loc[selector]}"
            raise ValueError(msg)
        return df

    @cached_property
    def hwp_genus(self):
        """IRW fraction by DBH classes"""
        df = pd.read_csv(self.common_dir / "hwp_genus.csv")
        return df

    @cached_property
    def nb_grading(self):
        """Grading Nicolas Bozzolan
        Keep only sawlogs and pulpwood from that grading table.

            >>> from eu_cbm_hat.post_processor.hwp_common_input import hwp_common_input
            >>> df = hwp_common_input.nb_grading

        """
        df_wide = pd.read_csv(self.common_dir / "nb_grading.csv")
        selector = df_wide["grade"].isin(["sawlogs", "pulpwood"])
        df_wide = df_wide.loc[selector]
        # Reshape to long format
        index = ["country", "genus", "species", "mgmt_type", "mgmt_strategy", "grade"]
        df = df_wide.melt(id_vars=index, var_name="dbh_class", value_name="proportion")
        df["dbh_class"] = df["dbh_class"].map(DBH_CLASSES)
        # Check that proportions sum to either zero or one
        index = [
            "country",
            "genus",
            "species",
            "mgmt_type",
            "mgmt_strategy",
            "dbh_class",
        ]
        df_agg = df.groupby(index)["proportion"].agg("sum").reset_index()
        zero = np.isclose(df_agg["proportion"], 0)
        one = np.isclose(df_agg["proportion"], 1)
        zero_or_one = zero | one
        if any(~zero_or_one):
            msg = "Proportions do not sum to zero or one for the following lines\n"
            msg += f"{df_agg.loc[~zero_or_one]}"
            raise ValueError(msg)
        return df

    @cached_property
    def fao_correction_factor(self):
        """Data 1961-LRY is from Forestry_E_Europe.csv this function
        Prepare the FAO correction factor data

        Usage:

            >>> from eu_cbm_hat.post_processor.hwp_common_input import hwp_common_input
            >>> hwp_common_input.fao_correction_factor

        """
        df_fao = self.faostat_bulk_data
        # remove rows which do not reffer to "quantity" from original data
        df_fao["Element"] = df_fao["Element"].astype(str)       
        selector = df_fao["Element"].str.contains("value")
        df_fao = df_fao[~selector].rename(
            columns={"Item": "Item_orig", "Element": "Element_orig"}
        )
        # Add labels used in the hwp scripts, keep only Items in the hwp_types table
        df = df_fao.merge(self.hwp_types, on=["Item Code", "Item_orig"]).merge(
            self.eu_member_states, on=["Area"], how="inner"
        )
        # Filter the columns that start with 'Y' and do not end with a letter
        keep_columns = [
            "Area Code",
            "Area",
            "Item Code",
            "Item_orig",
            "Item",
            "Element Code",
            "Element_orig",
            "Unit",
        ]
        fao_stat = df.loc[
            :,
            keep_columns
            + df.columns[
                (df.columns.str.startswith("Y"))
                & ~(df.columns.str.endswith(("F", "N")))
            ].tolist(),
        ]

        # Rename columns to remove 'Y' prefix for the year
        new_columns = {
            col: col[1:] if col.startswith("Y") else col for col in df.columns
        }
        fao_stat = fao_stat.rename(columns=new_columns)
        # reorganize table on long format
        fao_stat = fao_stat.melt(
            id_vars=[
                "Area Code",
                "Area",
                "Item Code",
                "Item_orig",
                "Item",
                "Element Code",
                "Element_orig",
                "Unit",
            ],
            var_name="year",
            value_name="Value",
        )
        # add new labels on a new column for harmonization

        shorts_mapping = {
            "Production": "prod",
            "Import quantity": "imp",
            "Export quantity": "exp",
        }
        fao_stat.loc[:, "Element"] = fao_stat.loc[:, "Element_orig"].map(shorts_mapping)
        # rename
        fao_stat = fao_stat.rename(columns={"Area": "area"})
        fao_stat["year"] = fao_stat["year"].astype(int)

        # Aggregate on labels
        index = ["area", "Element", "year", "Item"]
        # The min_count argument requires at least one value otherwise the sum will be NA
        df_exp = fao_stat.groupby(index).sum(min_count=1).reset_index()
        df_exp = df_exp.rename(columns={"Value": "value"})
        # create the input type
        df_exp["type"] = (
            df_exp["Item"].astype(str) + "_" + df_exp["Element"].astype(str)
        )
        df = df_exp.pivot(index=["area", "year"], columns=["type"], values=["value"])
        df = df.droplevel(None, axis=1).reset_index()
        df["year"] = df["year"].astype(int)
        # Sum up Particle board values with OSB
        # Sum all 3 columns together for each variable
        for var in ["exp", "imp", "prod"]:
            cols = ["partboa_and_osb", "partboa_original", "osb"]
            cols_var = [x + "_" + var for x in cols]
            # To avoid double counting assert that there is no value in
            # "partboa_and_osb" when there is a value in partboa_original
            # column and in the osb column the sum of colvars value should be
            # one or 2 not 3
            df["check_" + var] = (df[cols_var] > 0).sum(axis=1)
            selector = df["check_" + var] > 2
            if any(selector):
                msg = "Double counting for Particle Board and OSB. Check:\n"
                msg += f"{df.loc[selector, ['area', 'year'] + cols_var]}"
                raise ValueError(msg)
            # Compute the sum
            df["partboa_" + var] = df[cols_var].sum(axis=1)

        # Convert year to an integer
        df["year"] = df["year"].astype(int)
        return df

    @cached_property
    def rw_export_correction_factor(self):
        """data 1961-LRY is from Forestry_E_Europe.csv this function allows
        the estimation of the factor "f" that represents the feedstock for the
        HWP of domestic origin, after the correction for the export of
        roundwood, to be applied to eu_cbm_hat simulated IRW.

        The factor "fIRW_SW_con" estimates how much production from total
        production can be assumed to be from domestic roundwood production.
        Excerpt from the code beow that estimates the fractions of domestic in
        the country's roundwood feedstock

            >>> df_exp["fIRW_SW_con"] = (df_exp["irw_con_prod"] - df_exp["irw_con_exp"]) / (
            >>> df_exp["irw_con_prod"] + df_exp["irw_con_imp"] - df_exp["irw_con_exp"])

        Plot export correction factors by country

            >>> import seaborn
            >>> import matplotlib.pyplot as plt
            >>> from eu_cbm_hat.post_processor.hwp_common_input import hwp_common_input
            >>> df = hwp_common_input.rw_export_correction_factor
            >>> g = seaborn.relplot( data=df, x="year", y="fIRW_WP",
            ...                     col="area", kind="line", col_wrap=4,
            ...                     height=3, facet_kws={'sharey': True,
            ...                                          'sharex': True})

        """
        df_exp = self.fao_correction_factor
        # estimate the fractions of domestic in the country's feedstock on con and broad: IRW, WP, PULP on con and broad
        df_exp["fIRW_SW_con"] = (df_exp["irw_con_prod"] - df_exp["irw_con_exp"]) / (
            df_exp["irw_con_prod"] + df_exp["irw_con_imp"] - df_exp["irw_con_exp"]
        )


        
        df_exp["fIRW_SW_broad"] = (
            df_exp["irw_broad_prod"] - df_exp["irw_broad_exp"]
        ) / (
            df_exp["irw_broad_prod"] + df_exp["irw_broad_imp"] - df_exp["irw_broad_exp"]
        )

        # average for a generic value
        # df_exp['fIRW_WP'] =(df_exp['fIRW_SW_con'] + df_exp['fIRW_SW_broad'])/2
        # ALTERNATIVELY, estimate the generic fraction of domestic feedstock, i.e., no con/broad split

        df_exp["fIRW_WP"] = (df_exp["irw_prod"] - df_exp["irw_exp"]) / (
            df_exp["irw_prod"] + df_exp["irw_imp"] - df_exp["irw_exp"]
        )
        df_exp["fPULP"] = (
            df_exp["fIRW_WP"]
            * (df_exp["wood_pulp_prod"] - df_exp["wood_pulp_exp"])
            / (
                df_exp["wood_pulp_prod"]
                + df_exp["wood_pulp_imp"]
                - df_exp["wood_pulp_exp"]
            )
        )

        # f values on con and broad
        df_exp["fIRW_SW_con"] = df_exp["fIRW_SW_con"].mask(
            df_exp["fIRW_SW_con"] < 0, 0
        )
        df_exp["fIRW_SW_broad"] = df_exp["fIRW_SW_broad"].mask(
            df_exp["fIRW_SW_broad"] < 0, 0
        )
        df_exp["fPULP"] = df_exp["fPULP"].mask(df_exp["fPULP"] < 0, 0)

        # apply assumptions that fIRW_WP = 0 when ratio <0
        df_exp["fIRW_WP"] = df_exp["fIRW_WP"].mask(df_exp["fIRW_WP"] < 0, 0)

        # fractions of recycled paper feedstock, exports and exports
        df_exp["fREC_PAPER"] = (
            df_exp["recycled_paper_prod"] - df_exp["recycled_paper_exp"]
        ) / (
            df_exp["recycled_paper_prod"]
            + df_exp["recycled_paper_imp"]
            - df_exp["recycled_paper_exp"]
        )

        # apply assumptions that f = 0 when ratio < 0
        df_exp["fREC_PAPER"] = df_exp["fREC_PAPER"].mask(df_exp["fREC_PAPER"] < 0, 0)
        df_exp["year"] = df_exp["year"].astype(int)        
        return df_exp

    @cached_property
    def sw_con_broad_share(self):
        """Compute the share of con and broad in sawnwood production from the
        FAOSTAT data to be applied to CRF data.

        The reason is that the CRF data crf_semifinished_data is not
        distinguished by con broad. We want to keep CRF data because it's a
        better data source updated more frequently by the reporting countries
        compared to FAOSTAT. To add con and broad in formation we can compute
        the share of con and broad from FAOSTAT.
        """
        selected_cols = ["sawnwood_broad_prod", "sawnwood_con_prod", "sawnwood_prod"]
        df = self.fao_correction_factor[["area", "year"] + selected_cols].copy()
        # Check that the sum is correct
        df_check = df.loc[~df["sawnwood_broad_prod"].isna()]
        dontsum = (
            df_check["sawnwood_broad_prod"] + df_check["sawnwood_con_prod"]
        ) != df_check["sawnwood_prod"]
        if any(dontsum):
            msg = "Some places don't sum to reported value"
            msg += f"{df_check.loc[dontsum]}"
            raise ValueError(msg)
        # Compute the share of broad
        df["sw_share_broad"] = df["sawnwood_broad_prod"] / df["sawnwood_prod"]
        # Share in 1960 is equal to 1961
        df_1960 = df.loc[df["year"] == 1961].copy()
        df_1960["year"] = 1960
        df = (
            pd.concat([df_1960, df])
            .sort_values(["area", "year"])
            .reset_index(drop=True)
        )
        return df

    @cached_property
    def crf_semifinished_data(self):
        """data 1961-LRY from common/hwp_crf_submission.csv
        input timeseries of quantities of semifinshed products reported under the CRF

        Split the sw_prod_m3 column by con and broad before the gap filling
        using the fraction from the function sw_prod_m3. --> note the fraction
        might not be available for all years. So we have to do that before the
        gap fill. We area here in crf_semifinished_data before the gap fill.

        """
        df = self.crf_stat.set_index(["area", "year"])
        selector = "_crf"
        df = df.filter(regex=selector).reset_index()
        # remove strings in names
        df.columns = df.columns.str.replace(selector, "")
        df = df.set_index(["area", "year"])
        # remove notation kew from CRF based data
        df = df.replace(["NO", "NE", "NA", "NA,NE"], np.nan)
        # df = df.fillna(0).astype(float)
        df = df.filter(regex="_prod").reset_index()
        # Split the sw_prod_m3 column by con and broad
        df = df.merge(
            self.sw_con_broad_share[["area", "year", "sw_share_broad"]],
            on=["area", "year"],
            how="left",
        )
        df["sw_broad_prod_m3"] = df["sw_prod_m3"] * df["sw_share_broad"]
        df["sw_con_prod_m3"] = df["sw_prod_m3"] * (1 - df["sw_share_broad"])
        # Remove the share
        df.drop(columns="sw_share_broad", inplace=True)
        df["year"] = df["year"].astype(int)
        return df

    @cached_property
    def eu_semifinished_complete_series(self):
        """Filter countries which have complete time series, compute the total
        values and compute the backward rate of change from the current year to
        the previous year.

        Add a EU total excluding the countries with incomplete time series. To
        be used as proxy for gap filling of missing data by ms in original unit
        m3 or t for 1961-LRY

        Plot ratio columns:

            >>> from eu_cbm_hat.post_processor.hwp_common_input import hwp_common_input
            >>> import matplotlib.pyplot as plt
            >>> df = hwp_common_input.eu_semifinished_complete_series
            >>> ratio_cols = df.columns[df.columns.str.contains("ratio")]
            >>> df.set_index("year")[ratio_cols].plot()
            >>> plt.show()
            >>> sw_cols = ['sw_eu_ratio', 'sw_broad_eu_ratio', 'sw_con_eu_ratio']
            >>> df.set_index("year")[sw_cols].query("year>1962").plot()
            >>> plt.show()

        """
        selected_cols = [
            "sw_prod_m3",
            "wp_prod_m3",
            "pp_prod_t",
            "sw_broad_prod_m3",
            "sw_con_prod_m3",
        ]
        df_ms = self.crf_semifinished_data
        df_ms = df_ms[["year", "area"] + selected_cols]
        # Keep only countries which have the complete time series for all products
        complete_groups = df_ms.groupby(["area"]).filter(
            lambda x: not (
                (x["sw_prod_m3"] == 0).any()
                or (x["wp_prod_m3"] == 0).any()
                or (x["pp_prod_t"] == 0).any()
            )
        )
        # Aggregate, sum for the whole EU countries which have data
        df = complete_groups.groupby(["year"])[selected_cols].sum().reset_index()
        # Calculate the ratio of change from the current year to the previous
        # year, i.e. 1999 vs. 2000 irw_eu for each row to the next row. It's a
        # ratio that goes backward in time
        for col in selected_cols:
            ratio_col = re.sub("prod_m3|prod_t", "eu_ratio", col)
            df[ratio_col] = df[col] / df[col].shift(-1)
        # Rename quantities columns to indicate eu wide trend aggregates
        df.rename(
            columns=lambda x: re.sub(r"prod_m3$|prod_t$", "eu_prod", x), inplace=True
        )
        return df

    @cached_property
    def prod_gap_filled(self):
        """Gap fill member state production values Gap

        This function fills sw_prod_m3, wp_prod_m3 and pp_prod_t using the
        change rate from EU totals. It computes back the production in the current
        year based on the value of the next year multiplied by the EU change
        rate from the next year to the current year.

        Show which countries have been gap filled:

        >>> from eu_cbm_hat.post_processor.hwp_common_input import hwp_common_input
        >>> # Before
        >>> crf = hwp_common_input.crf_semifinished_data
        >>> crf.loc[crf["sw_broad_prod_m3"].isna()]
        >>> # After
        >>> df = hwp_common_input.prod_gap_filled
        >>> df.loc[df["sw_broad_prod_m3"].isna()]

        """
        df_ratio = self.eu_semifinished_complete_series
        ratio_cols = df_ratio.columns[df_ratio.columns.str.contains("ratio")].to_list()
        df = self.crf_semifinished_data.merge(
            df_ratio[["year"] + ratio_cols],
            on="year",
            how="left",
        )
        prod_cols = df.columns[df.columns.str.contains("prod")].to_list()
        df.replace(0, np.nan, inplace=True)
        # Arrange by country and year, reset index
        df = df.sort_values(["area", "year"]).reset_index(drop=True)
        # Reverse the DataFrame to fill missing values in reverse order
        df = df.iloc[::-1].copy()

        # Fill missing values using the ratio
        for index, row in df.iterrows():
            # Skip the highest index
            if index > len(df) - 2:
                continue
            # Skip to next row if we are not in the same country
            if df.at[index, "area"] != df.at[index + 1, "area"]:
                continue
            # Back compute the production in the current year
            for col in prod_cols:
                ratio_col = re.sub("prod_m3|prod_t", "eu_ratio", col)
                if pd.isnull(row[col]):
                    next_value = df.at[index + 1, col]
                    df.at[index, col] = next_value * row[ratio_col]
        # Reverse the DataFrame back to the original order
        df = df.iloc[::-1]
        # Drop the temporary 'ratio' columns as they are no longer needed
        df.drop(columns=ratio_cols, inplace=True)
        return df

    @cached_property
    def prod_backcast_to_1900(self):
        """Backcast production values to 1900
        # apply U value
        #TABLE 12.3 ESTIMATED ANNUAL RATES OF INCREASE FOR INDUSTRIAL ROUNDWOOD
        PRODUCTION (HARVEST) BY WORLD REGION FOR THE PERIOD 1900 TO 1961
        u_const = 0.0151

        Plot backcast production by country

            >>> import seaborn
            >>> import matplotlib.pyplot as plt
            >>> from eu_cbm_hat.post_processor.hwp_common_input import hwp_common_input
            >>> df = hwp_common_input.prod_backcast_to_1900
            >>> var = "sw_prod_m3"
            >>> g = seaborn.relplot( data=df, x="year", y=var,
            ...                     col="area", kind="line", col_wrap=4,
            ...                     height=3, facet_kws={'sharey': False,
            ...                                          'sharex': True})
            >>> plt.show()

        Check divergence between estimated sawnwood con and broad production
        compared to total sawnwood for early years

            >>> df = self.prod_backcast_to_1900
            >>> df["sw_prod_check"] = df[['sw_broad_prod_m3', 'sw_con_prod_m3']].sum(axis=1)
            >>> df.query("area=='Slovenia'")
            >>> df.query("area=='Austria'")

        """
        df = self.prod_gap_filled.copy()
        # Get the value for the first year
        first_year = df["year"].min()
        print(f"Backcasting from {first_year} to 1900")
        # Extract the first value to be used to initiate the backcast to 1900
        selector = df["year"] == first_year
        df1 = df.loc[selector].copy()
        # Production columns
        cols = df.columns[df.columns.str.contains("prod")].to_list()
        cols_1 = [c + "_1" for c in cols]
        col_dict = dict(zip(cols, cols_1))
        df1.rename(columns=col_dict, inplace=True)
        df1.drop(columns="year", inplace=True)
        # Backcast between 1900 and first_year
        area = df["area"].unique()
        year = range(1900, first_year)
        expand_grid = list(itertools.product(area, year))
        df_back = pd.DataFrame(expand_grid, columns=("area", "year"))
        index = ["area", "year"]
        # Generate the time series
        df_back = df_back.merge(df1, on="area", how="left")
        for var in cols:
            u_const = 0.0151
            df_back[var] = df_back[var + "_1"] * math.e ** (
                u_const * (df_back["year"] - first_year)
            )
        df_back.drop(columns=cols_1, inplace=True)
        # concatenate with the later years
        df = pd.concat([df, df_back])
        df.sort_values(index, inplace=True)
        df.reset_index(drop=True, inplace=True)
        # fillna with 0, i.e., no production
        df = df.fillna(0)
        return df

    @property  # Don't cache, in case we change the number of years
    def prod_from_dom_harv_stat(self):
        """Compute production from domestic harvest
        Use export correction factors to compute the sawnwood, panel and paper
        production from domestic roundwood harvest
        These are the historical domestic feedstock (corrected for export)
        this merges the export with semifinished inputs to generate HWP of
        domestic origin, in original unit m3 or t for 1961-LRY

        Replace NA recycling values by zero if and only if they have NA in all
        years. In other words NA values for the recycled_paper_prod and
        recycled_wood_prod will be replaced by zeros if there are NA everywhere
        for all  years of the series. Otherwise the latest values will be
        backfilled.

        Example use:

            >>> from eu_cbm_hat.post_processor.hwp_common_input import hwp_common_input
            >>> hwp_common_input.rw_export_correction_factor
            >>> hwp_common_input.prod_from_dom_harv_stat

        Plot wood panel production in a selected country:

            >>> import matplotlib.pyplot as plt
            >>> df = hwp_common_input.prod_from_dom_harv_stat
            >>> df.query("area =='Austria'").set_index("year")["wp_prod_m3"].plot()
            >>> plt.show()

        """
        index = ["area", "year"]
        factor_cols = [
            "fPULP",
            "fIRW_WP",
            'fIRW_SW_con',
            'fIRW_SW_broad',
        ]
        recycle_cols = [
            "recycled_paper_prod",
            "recycled_wood_prod",
        ]
        selected_cols = index + factor_cols + recycle_cols
        exp_fact = self.rw_export_correction_factor[selected_cols].copy()
        # Set the export import factors to one i.e. equivalent to setting
        # export and import values to zero in the estimation of the production
        # from domestic harvest. In other words, assume that all secondary
        # products production is made from domestic industrial roundwood
        # harvest.
        if self.no_export_no_import:
            for col in factor_cols:
                exp_fact[col] = 1
        # Merge production data with export factors data
        df = self.prod_backcast_to_1900.merge(exp_fact, on=index, how="left")
        no_data = (
            df.groupby("area")
            .agg(
                no_value=("fIRW_WP", lambda x: all(x.isna())),
                recycled_paper_prod=("recycled_paper_prod", lambda x: all(x.isna())),
                recycled_wood_prod=("recycled_wood_prod", lambda x: all(x.isna())),
            )
            .reset_index()
        )
       # Warn about countries which don't have factors data at all
        country_with_no_data = no_data.loc[no_data.no_value, "area"].to_list()
        if any(country_with_no_data):
            msg = "\nNo export correction factor data for these countries:"
            msg += f"\n{country_with_no_data}"
            warnings.warn(msg)

        # Replace NA recycling values by zero if and only if they have NA in all years
        for var in ["recycled_paper_prod", "recycled_wood_prod"]:
            selector = no_data[var]
            if any(selector):
                df_replace_zero = no_data.loc[selector, ["area"]].copy()
                df_replace_zero["replace"] = 0
                df2 = df.merge(df_replace_zero, on="area", how="left")
                df[var] = df[var].fillna(df2["replace"])

        # Gap fill export correction factors
        n_years = self.n_years_for_backfill
        for col in factor_cols + recycle_cols:
            df = backfill_avg_first_n_years(df, var=col, n=n_years)
       # DO zero recycled_wood_prod and recycled_wood_paper for period before 2017
        # Define the columns to process
        columns_to_zero = ['recycled_paper_prod', 'recycled_wood_prod']
        
        # Set years 1900-2016 to zero
        df.loc[(df['year'] >= 1900) & (df['year'] <= 2016), columns_to_zero] = 0
        
        # Define the range
        start_year = 2018
        end_year = 1980  # 2018 - 30 = 1988 (30 years including 2018)
        
        # Iterate through each area
        for area in df['area'].unique():
            # Create mask for current area
            area_mask = df['area'] == area
            
            # Get initial values for 2018 for this specific area
            initial_values = df.loc[(df['year'] == start_year) & area_mask, columns_to_zero].iloc[0]
            
            # Create a mask for years 1988-2018 for this area
            years_mask = (df['year'] >= end_year) & (df['year'] <= start_year) & area_mask
            
            # Calculate factors for all years at once
            years_array = df.loc[years_mask, 'year'].values
            factors = (years_array - end_year) / (start_year - end_year)
            
            # Apply the factors for each column
            for col in columns_to_zero:
                df.loc[years_mask, col] = initial_values[col] * factors

       # Compute production from domestic roundwood
        df["sw_broad_dom_m3"] = df["sw_broad_prod_m3"] * df["fIRW_SW_broad"]
        df["sw_con_dom_m3"] = df["sw_con_prod_m3"] * df["fIRW_SW_con"]
        df["wp_dom_m3"] = df["wp_prod_m3"] * df["fIRW_WP"]
        df["pp_dom_t"] = df["pp_prod_t"] * df["fPULP"]
        # Compute values in Tons of Carbon
        # Note: the carbon fraction of biomass should be adapted to the species
        # mix in the inventory in each country. It should be a country specific
        # value.
        df["sw_broad_dom_tc"] = self.c_sw_broad * df["sw_broad_dom_m3"]
        df["sw_con_dom_tc"] = self.c_sw_con * df["sw_con_dom_m3"]
        df["wp_dom_tc"] = self.c_wp * df["wp_dom_m3"]
        df["pp_dom_tc"] = self.c_pp * df["pp_dom_t"]

        # update from tons of fresh matter to C dry matter
        df["recycled_wood_prod_tc"] =  df["recycled_wood_prod"] * (1 - self.humid_corr_wood)*self.c_rwp
        df["recycled_paper_prod_tc"] = df["recycled_paper_prod"] * (1 - self.humid_corr_paper)* self.c_rpp
        
        # Correct for recycled wood panel and paper amounts
        df["wp_dom_tc"] = df["wp_dom_tc"] - df["recycled_wood_prod_tc"]
        df["pp_dom_tc"] = df["pp_dom_tc"] - df["recycled_paper_prod_tc"]

        # In some countries the recycled paper production is higher than pp_dom_tc
        # Then in that case set it to zero
        selector = df["pp_dom_tc"] < 0
        df.loc[selector, "pp_dom_tc"] = 0

        # Production of WP may turn negative toward the start of the century
        # Then in that case set it to zero
        selector = df["wp_dom_tc"] < 0
        df.loc[selector, "wp_dom_tc"] = 0
        return df

    @cached_property
    def waste(self):
        """Waste treatment data from EUROSTAT

        All emissions factors are based on wet material, then we apply the
        humidity correction to convert to dry matter.
        """
        df = pd.read_csv(eu_cbm_data_pathlib / "common/eu_waste_treatment.csv")
        # Sum the 3 waste types values per year and per country
        df = (
            df.groupby(["geo", "TIME_PERIOD"])
            .agg(wood_landfill_tfm=("OBS_VALUE", "sum"))
            .reset_index()
        )
        df.rename(columns={"geo": "country_iso2", "TIME_PERIOD": "year"}, inplace=True)
        # In the resulting sum, replace zeros by NA values. So that the
        # interpolation in hwp.py will work only on available values.
        df["wood_landfill_tfm"] = df["wood_landfill_tfm"].replace(0, np.nan)

        # Apply humidity correction
        h_corr = 0.15
        df["w_annual_wood_landfill_tdm"] = (1 - h_corr) * df["wood_landfill_tfm"]
        return df

# Initiate the class
hwp_common_input = HWPCommonInput()
