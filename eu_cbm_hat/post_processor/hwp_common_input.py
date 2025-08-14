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
    df[var].fillna(df["mean"], inplace=True)
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
        # N year parameter for the backfill_avg_first_n_years
        self.n_years_for_backfill = 3
        # Set export import factors to one
        self.no_export_no_import = False

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
        # Rename countries
        area_dict = {"Netherlands (Kingdom of the)": "Netherlands"}
        df["Area"] = df["Area"].replace(area_dict)
        return df

    @cached_property
    def crf_stat(self):
        """crf sumbissions"""
        df = pd.read_csv(eu_cbm_data_pathlib / "common/hwp_crf_submission.csv")
        df = df.rename(columns={"country": "area"})
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

            >>>
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
        """Data 1961-2021 is from Forestry_E_Europe.csv this function
        Prepare the FAO correction factor data

        Usage:

            >>> from eu_cbm_hat.post_processor.hwp_common_input import hwp_common_input
            >>> hwp_common_input.fao_correction_factor

        """
        df_fao = self.faostat_bulk_data
        # remove rows which do not reffer to "quantity" from original data
        selector = df_fao["Element"].str.contains("Value")
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
            "Import Quantity": "imp",
            "Export Quantity": "exp",
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

        # convert long to wide format
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
        # average for a generic value
        #df_exp["irw_prod"] = df_exp["irw_broad_prod"] + df_exp["irw_con_prod"]
        #df_exp["irw_exp"] = df_exp["irw_broad_exp"] + df_exp["irw_con_exp"]
        #df_exp["irw_imp"] = df_exp["irw_broad_imp"] + df_exp["irw_con_imp"]

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
        """data 1961-2021 from common/hwp_crf_submission.csv
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
        m3 or t for 1961-2021

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
        domestic origin, in original unit m3 or t for 1961-2021

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
        for var in ["recycled_wood_prod", "recycled_wood_prod"]:
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
        # Correct for recycled wood panel and paper amounts
        df["wp_dom_tc"] = df["wp_dom_tc"] - df["recycled_wood_prod"] * self.c_wp
        df["pp_dom_tc"] = df["pp_dom_tc"] - df["recycled_paper_prod"] * self.c_pp
        # In some countries the recycled paper production is higher than pp_dom_tc
        # Then in that case set it to zero
        selector = df["pp_dom_tc"] < 0
        df.loc[selector, "pp_dom_tc"] = 0
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






















###### OLD 

# Initiate the class
hwp_common_input = HWPCommonInput()


# %%
# def gap_filling_ms_crf():


# %%
def gapfill_hwp_ms_backward(df):
    # Copy the original DataFrame to avoid modifying the original data for 1961-2021
    interpolated_ms = df.copy()

    # Calculate the ratio of irw_eu for each row to the next row
    interpolated_ms["sw_ratio"] = (
        interpolated_ms["sw_prod_eu"].shift(-1) / interpolated_ms["sw_prod_eu"]
    )
    interpolated_ms["wp_ratio"] = (
        interpolated_ms["wp_prod_eu"].shift(-1) / interpolated_ms["wp_prod_eu"]
    )
    interpolated_ms["pp_ratio"] = (
        interpolated_ms["pp_prod_eu"].shift(-1) / interpolated_ms["pp_prod_eu"]
    )

    # Reset the index to ensure consecutive integers
    interpolated_ms.reset_index(drop=True, inplace=True)

    # Reverse the DataFrame to fill missing values in reverse order
    interpolated_ms = interpolated_ms.iloc[::-1]

    # Fill missing values in new_irw_ms using the ratio
    for index, row in interpolated_ms.iterrows():
        if pd.isnull(row["sw_prod_ms"]):
            next_value = interpolated_ms.at[index + 1, "new_sw_ms"]
            if not pd.isnull(next_value):
                interpolated_ms.at[index, "new_sw_ms"] = int(
                    next_value / row["sw_ratio"]
                )
            else:
                interpolated_ms.at[
                    index, "new_sw_ms"
                ] = next_value  # Keep NaN if next value is NaN
        else:
            interpolated_ms.at[index, "new_sw_ms"] = row["sw_prod_ms"]

    for index, row in interpolated_ms.iterrows():
        if pd.isnull(row["wp_prod_ms"]):
            next_value = interpolated_ms.at[index + 1, "new_wp_ms"]
            if not pd.isnull(next_value):
                interpolated_ms.at[index, "new_wp_ms"] = int(
                    next_value / row["wp_ratio"]
                )
            else:
                interpolated_ms.at[
                    index, "new_wp_ms"
                ] = next_value  # Keep NaN if next value is NaN
        else:
            interpolated_ms.at[index, "new_wp_ms"] = row["wp_prod_ms"]

    for index, row in interpolated_ms.iterrows():
        if pd.isnull(row["pp_prod_ms"]):
            next_value = interpolated_ms.at[index + 1, "new_pp_ms"]
            if not pd.isnull(next_value):
                interpolated_ms.at[index, "new_pp_ms"] = int(
                    next_value / row["pp_ratio"]
                )
            else:
                interpolated_ms.at[
                    index, "new_pp_ms"
                ] = next_value  # Keep NaN if next value is NaN
        else:
            interpolated_ms.at[index, "new_pp_ms"] = row["pp_prod_ms"]

    # for col in ['sw_ratio', 'wp_ratio', 'pp_ratio']:
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
    interpolated_ms["sw_domestic_tc"] = c_sw * interpolated_ms["new_sw_ms"]
    interpolated_ms["wp_domestic_tc"] = c_pw * interpolated_ms["new_wp_ms"]
    interpolated_ms["pp_domestic_tc"] = c_pp * interpolated_ms["new_pp_ms"]

    # Drop the temporary 'ratio' column as it's no longer needed
    columns_to_drop = ["sw_ratio", "wp_ratio", "pp_ratio"]
    interpolated_ms.drop(columns=columns_to_drop, inplace=True)

    # Convert 'new_irw_ms' column to integer
    # interpolated_ms#['new_sw_ms'] = interpolated_sw['new_sw_ms'].astype(int)

    return interpolated_ms


# %%
def fao_sw_to_irw():
    """this estimates the average amount of sawnwood produced as average of 2021 and 2022"""
    """runner.post_processor.hwp.rw_export_correction_factor()"""
    # df_faostat = faostat_bulk_data

    # remove rows which do not reffer to "quantity" from original data
    filter = faostat_bulk_data["Element"].str.contains("Value")
    df_fao = faostat_bulk_data[~filter].rename(
        columns={"Item": "Item_orig", "Element": "Element_orig"}
    )

    # add lables used in the hwp scripts
    df = df_fao.merge(hwp_types, on=["Item Code", "Item_orig"]).merge(
        eu_member_states, on=["Area"]
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
    df = df.loc[
        :,
        keep_columns
        + df.columns[
            (df.columns.str.startswith("Y")) & ~(df.columns.str.endswith(("F", "N")))
        ].tolist(),
    ]

    # Rename columns to remove 'Y' prefix for the year
    new_columns = {col: col[1:] if col.startswith("Y") else col for col in df.columns}
    df = df.rename(columns=new_columns)

    df_ms = df.query('Item == "sawnwood_broad" | Item == "sawnwood_con" ').copy()

    shorts_mapping = {
        "Production": "prod",
        "Import Quantity": "imp",
        "Export Quantity": "exp",
    }
    df_ms.loc[:, "Element_ms"] = df_ms.loc[:, "Element_orig"].map(shorts_mapping)

    first_year = 2021
    last_year = 2023
    df_ms = df_ms.loc[
        :,
        ["Area", "Item", "Element_ms"]
        + [str(year) for year in range(first_year, last_year)],
    ]

    df_ms = pd.melt(
        df_ms,
        id_vars=["Area", "Item", "Element_ms"],
        var_name="Year",
        value_name="Value",
    )

    df_ms = (
        df_ms.groupby(["Area", "Item", "Element_ms", "Year"])
        .agg(
            irw_ms=("Value", "sum"),
        )
        .reset_index()
    )

    # keep only 2021 and 2022
    df_ms = df_ms.query('Element_ms == "prod" ')
    df_ms = df_ms.query('Year == "2021" | Year == "2022" ')

    average_sw_ms = df_ms.groupby(["Area", "Item"])["irw_ms"].mean().reset_index()

    average_sw_ms = average_sw_ms.pivot(
        index="Area", columns="Item", values="irw_ms"
    ).reset_index()

    # add the share of sawnwood expected from the final cut
    average_sw_ms["final_cut_share_broad"] = 0.9
    average_sw_ms["final_cut_share_con"] = 0.95

    return average_sw_ms


# %%
def fao_wp_to_irw():
    """this estimates the average amount of sawnwood produced as average of 2021 and 2022"""
    """runner.post_processor.hwp.rw_export_correction_factor()"""
    # df_faostat = faostat_bulk_data

    # remove rows which do not reffer to "quantity" from original data
    filter = faostat_bulk_data["Element"].str.contains("Value")
    df_fao = faostat_bulk_data[~filter].rename(
        columns={"Item": "Item_orig", "Element": "Element_orig"}
    )

    # add lables used in the hwp scripts
    df = df_fao.merge(hwp_types, on=["Item Code", "Item_orig"]).merge(
        eu_member_states, on=["Area"]
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
    df = df.loc[
        :,
        keep_columns
        + df.columns[
            (df.columns.str.startswith("Y")) & ~(df.columns.str.endswith(("F", "N")))
        ].tolist(),
    ]

    # Rename columns to remove 'Y' prefix for the year
    new_columns = {col: col[1:] if col.startswith("Y") else col for col in df.columns}
    df = df.rename(columns=new_columns)

    df_ms = df.query(' Item == "wood_panels" ').copy()

    shorts_mapping = {
        "Production": "prod",
        "Import Quantity": "imp",
        "Export Quantity": "exp",
    }
    df_ms.loc[:, "Element_ms"] = df_ms.loc[:, "Element_orig"].map(shorts_mapping)

    first_year = 2021
    last_year = 2023
    df_ms = df_ms.loc[
        :,
        ["Area", "Item", "Element_ms"]
        + [str(year) for year in range(first_year, last_year)],
    ]

    df_ms = pd.melt(
        df_ms,
        id_vars=["Area", "Item", "Element_ms"],
        var_name="Year",
        value_name="Value",
    )

    df_ms = (
        df_ms.groupby(["Area", "Item", "Element_ms", "Year"])
        .agg(
            irw_ms=("Value", "sum"),
        )
        .reset_index()
    )

    # keep only 2021 and 2022
    df_ms = df_ms.query('Element_ms == "prod" ')
    df_ms = df_ms.query('Year == "2021" | Year == "2022" ')

    average_wp_ms = df_ms.groupby(["Area", "Item"])["irw_ms"].mean().reset_index()

    average_wp_ms = average_wp_ms.pivot(
        index="Area", columns="Item", values="irw_ms"
    ).reset_index()

    return average_wp_ms


# %%
def fao_pulp_to_irw():
    """this estimates the average amount of sawnwood produced as average of 2021 and 2022"""
    """runner.post_processor.hwp.rw_export_correction_factor()"""
    # df_faostat = faostat_bulk_data

    # remove rows which do not reffer to "quantity" from original data
    filter = faostat_bulk_data["Element"].str.contains("Value")
    df_fao = faostat_bulk_data[~filter].rename(
        columns={"Item": "Item_orig", "Element": "Element_orig"}
    )

    # add lables used in the hwp scripts
    df = df_fao.merge(hwp_types, on=["Item Code", "Item_orig"]).merge(
        eu_member_states, on=["Area"]
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
    df = df.loc[
        :,
        keep_columns
        + df.columns[
            (df.columns.str.startswith("Y")) & ~(df.columns.str.endswith(("F", "N")))
        ].tolist(),
    ]

    # Rename columns to remove 'Y' prefix for the year
    new_columns = {col: col[1:] if col.startswith("Y") else col for col in df.columns}
    df = df.rename(columns=new_columns)

    df_ms = df.query('Item == "wood_pulp" ').copy()

    shorts_mapping = {
        "Production": "prod",
        "Import Quantity": "imp",
        "Export Quantity": "exp",
    }
    df_ms.loc[:, "Element_ms"] = df_ms.loc[:, "Element_orig"].map(shorts_mapping)

    first_year = 2021
    last_year = 2023
    df_ms = df_ms.loc[
        :,
        ["Area", "Item", "Element_ms"]
        + [str(year) for year in range(first_year, last_year)],
    ]

    df_ms = pd.melt(
        df_ms,
        id_vars=["Area", "Item", "Element_ms"],
        var_name="Year",
        value_name="Value",
    )

    df_ms = (
        df_ms.groupby(["Area", "Item", "Element_ms", "Year"])
        .agg(
            irw_ms=("Value", "sum"),
        )
        .reset_index()
    )

    # keep only 2021 and 2022
    df_ms = df_ms.query('Element_ms == "prod" ')
    df_ms = df_ms.query('Year == "2021" | Year == "2022" ')

    average_pulp_ms = df_ms.groupby(["Area", "Item"])["irw_ms"].mean().reset_index()

    average_pulp_ms = average_pulp_ms.pivot(
        index="Area", columns="Item", values="irw_ms"
    ).reset_index()

    return average_pulp_ms


# %%
def gap_filling_irw_faostat():
    """this function allows the gapfilling of production, import and export of roundwood based on FAOSTAT data,
    i.e., applied to the a quantity result in the domestic amount"""
    """runner.post_processor.hwp.rw_export_correction_factor()"""
    # df_faostat = faostat_bulk_data

    # remove rows which do not reffer to "quantity" from original data
    filter = faostat_bulk_data["Element"].str.contains("Value")
    df_fao = faostat_bulk_data[~filter].rename(
        columns={"Item": "Item_orig", "Element": "Element_orig"}
    )

    # add lables used in the hwp scripts
    df = df_fao.merge(hwp_types, on=["Item Code", "Item_orig"]).merge(
        eu_member_states, on=["Area"]
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
    df = df.loc[
        :,
        keep_columns
        + df.columns[
            (df.columns.str.startswith("Y")) & ~(df.columns.str.endswith(("F", "N")))
        ].tolist(),
    ]

    # Rename columns to remove 'Y' prefix for the year
    new_columns = {col: col[1:] if col.startswith("Y") else col for col in df.columns}
    df = df.rename(columns=new_columns)

    df_ms = df.query('Item == "irw_broad" | Item == "irw_con" ').copy()

    shorts_mapping = {
        "Production": "prod",
        "Import Quantity": "imp",
        "Export Quantity": "exp",
    }
    df_ms.loc[:, "Element_ms"] = df_ms.loc[:, "Element_orig"].map(shorts_mapping)

    df_ms = df_ms[
        [
            "Area",
            "Item",
            "Element_ms",
            "1961",
            "1962",
            "1963",
            "1964",
            "1965",
            "1966",
            "1967",
            "1968",
            "1969",
            "1970",
            "1971",
            "1972",
            "1973",
            "1974",
            "1975",
            "1976",
            "1977",
            "1978",
            "1979",
            "1980",
            "1981",
            "1982",
            "1983",
            "1984",
            "1985",
            "1986",
            "1987",
            "1988",
            "1989",
            "1990",
            "1991",
            "1992",
            "1993",
            "1994",
            "1995",
            "1996",
            "1997",
            "1998",
            "1999",
            "2000",
            "2001",
            "2002",
            "2003",
            "2004",
            "2005",
            "2006",
            "2007",
            "2008",
            "2009",
            "2010",
            "2011",
            "2012",
            "2013",
            "2014",
            "2015",
            "2016",
            "2017",
            "2018",
            "2019",
            "2020",
            "2021",
            "2022",
        ]
    ]

    df_ms = pd.melt(
        df_ms,
        id_vars=["Area", "Item", "Element_ms"],
        var_name="Year",
        value_name="Value",
    )

    df_ms = (
        df_ms.groupby(["Area", "Item", "Element_ms", "Year"])
        .agg(
            irw_ms=("Value", "sum"),
        )
        .reset_index()
    )

    # df_ms.to_csv('C:/CBM/df_ms.csv')

    # Group by Area, Item, and Element
    grouped = df_ms.groupby(["Area", "Item", "Element_ms"])

    # Filter out groups where any value is zero within the time series
    complete_groups = grouped.filter(lambda x: not (x["irw_ms"] == 0).any())

    # Group by Area, Item, and Element and sum the amount
    df_eu = (
        complete_groups.groupby(["Item", "Element_ms", "Year"])["irw_ms"]
        .sum()
        .reset_index()
    )
    df_eu = df_eu.rename(columns={"irw_ms": "irw_eu", "Element_ms": "Element_eu"})

    df_faostat = df_ms.merge(df_eu, on=["Item", "Year"])
    # df_faostat = df_faostat.sort_values (by = ['Area','Item', 'Element', 'Year'] )
    df_faostat.replace(0, np.nan, inplace=True)

    # df_faostat.to_csv('C:/CBM/df_faostat.csv')
    return df_faostat


# %%
def gapfill_irw_ms_backward(df):
    # Copy the original DataFrame to avoid modifying the original data
    interpolated_df = df.copy()
    interpolated_df = interpolated_df.sort_values(
        by=["Year"], ascending=True
    ).sort_values(by=["Item", "Element_ms"])

    # Calculate the ratio of irw_eu for each row to the next row
    interpolated_df["ratio"] = (
        interpolated_df["irw_eu"].shift(-1) / interpolated_df["irw_eu"]
    )

    # Reset the index to ensure consecutive integers
    interpolated_df.reset_index(drop=True, inplace=True)

    # Reverse the DataFrame to fill missing values in reverse order
    interpolated_df = interpolated_df.iloc[::-1]

    # Fill missing values in new_irw_ms using the ratio
    for index, row in interpolated_df.iterrows():
        if pd.isnull(row["irw_ms"]):
            next_value = interpolated_df.at[index + 1, "new_irw_ms"]
            if not pd.isnull(next_value):
                interpolated_df.at[index, "new_irw_ms"] = int(next_value / row["ratio"])
            else:
                interpolated_df.at[
                    index, "new_irw_ms"
                ] = next_value  # Keep NaN if next value is NaN
        else:
            interpolated_df.at[index, "new_irw_ms"] = row["irw_ms"]

    # Reverse the DataFrame back to the original order
    interpolated_df = interpolated_df.iloc[::-1]

    # Drop the temporary 'ratio' column as it's no longer needed
    interpolated_df.drop(columns=["ratio"], inplace=True)

    # Convert 'new_irw_ms' column to integer
    interpolated_df["new_irw_ms"] = interpolated_df["new_irw_ms"].astype(int)
    # interpolated_df.to_csv('C:/CBM/interpolated.csv')

    return interpolated_df


# %%
def eu_wrb():
    sankey_rw_prod_in = euwrb_stat

    # retain only rows relevant for production of hwp
    sankey_rw_prod_in_hwp = sankey_rw_prod_in[sankey_rw_prod_in["label"] != "trade"]

    # load quantities from orih=ginal database
    sankey_rw_prod_in_hwp = sankey_rw_prod_in_hwp[
        ["scenario", "country", "year", "label", "data"]
    ].dropna()

    sankey_rw_prod_in_hwp = sankey_rw_prod_in_hwp.pivot(
        index=["scenario", "country", "year"], columns="label", values="data"
    ).reset_index()

    sankey_rw_prod_in_hwp = sankey_rw_prod_in_hwp.reset_index()

    # sankey_rw_prod_in_hwp.to_csv('C:/CBM/hwp.csv')

    # the sum of all semifinshed products converted to C
    c_sw = 0.225
    c_pw = 0.294
    c_pp = 0.450
    wd_con_broad = 0.5
    c_fraction = 0.5
    sankey_rw_prod_in_hwp["c_hwp_fao"] = 1 * (
        sankey_rw_prod_in_hwp["pan_ind2fibboa"] * c_pw
        + sankey_rw_prod_in_hwp["pan_ind2partboa"] * c_pw
        + sankey_rw_prod_in_hwp["pan_ind2plyven"] * c_pw
        + sankey_rw_prod_in_hwp["rw4mat2pu_ind"] * c_pp
        + sankey_rw_prod_in_hwp["saw_ind2sawnw"] * c_sw
    )

    # keep only the total C in all semifinished products
    sankey_c_semifinshed_faostat = sankey_rw_prod_in_hwp[
        ["country", "year", "c_hwp_fao"]
    ]

    # extract the share of sawnwood in total solid production
    sankey_rw_prod_in_hwp["fSW"] = (
        sankey_rw_prod_in_hwp["saw_ind2sawnw"] / sankey_rw_prod_in_hwp["rw_tot2rw4mat"]
    )

    # production of paper in total solid production, original excel formula: PP = if(rw4mat2pu_ind = 0,0, pu4pa2pap_ind)
    sankey_rw_prod_in_hwp["fPP"] = (
        sankey_rw_prod_in_hwp["rw4mat2pu_ind"] / sankey_rw_prod_in_hwp["rw_tot2rw4mat"]
    )

    # deduct the inflow of recycled wood
    # 1st step, define the share of fibboa and partboa in their total
    sankey_rw_prod_in_hwp["fibboa_share"] = sankey_rw_prod_in_hwp["pan_ind2fibboa"] / (
        sankey_rw_prod_in_hwp["pan_ind2fibboa"]
        + sankey_rw_prod_in_hwp["pan_ind2partboa"]
    )
    sankey_rw_prod_in_hwp["partboa_share"] = sankey_rw_prod_in_hwp[
        "pan_ind2partboa"
    ] / (
        sankey_rw_prod_in_hwp["pan_ind2fibboa"]
        + sankey_rw_prod_in_hwp["pan_ind2partboa"]
    )

    # 2nd step, further split the total rec wood panels on the two destinations, fibboa and partboa
    sankey_rw_prod_in_hwp["Qfibboa"] = (
        sankey_rw_prod_in_hwp["pcw2pan_ind"] * sankey_rw_prod_in_hwp["fibboa_share"]
    )
    sankey_rw_prod_in_hwp["Qpartboa"] = (
        sankey_rw_prod_in_hwp["pcw2pan_ind"] * sankey_rw_prod_in_hwp["partboa_share"]
    )

    # 3rd step, estimate production of panels from domestic roundwood, excluding PWC feedstock
    sankey_rw_prod_in_hwp["wp_sum"] = (
        sankey_rw_prod_in_hwp["pan_ind2fibboa"]
        + (sankey_rw_prod_in_hwp["pan_ind2partboa"] - sankey_rw_prod_in_hwp["Qpartboa"])
        + (sankey_rw_prod_in_hwp["pan_ind2plyven"] - sankey_rw_prod_in_hwp["Qfibboa"])
    )
    sankey_rw_prod_in_hwp["wp_sum"]

    # finally estimate the share of WP in total solid production
    sankey_rw_prod_in_hwp["fWP"] = (
        sankey_rw_prod_in_hwp["wp_sum"] / sankey_rw_prod_in_hwp["rw_tot2rw4mat"]
    )

    # sankey_rw_prod_in_hwp
    # # keep the use of post_consumer wood in panels, as it is used in substitution later
    # shares of panels types within WP
    sankey_rw_prod_in_hwp["fWP_fibboa"] = (
        sankey_rw_prod_in_hwp["pan_ind2fibboa"] / sankey_rw_prod_in_hwp["wp_sum"]
    )
    sankey_rw_prod_in_hwp["fWP_partboa"] = (
        sankey_rw_prod_in_hwp["pan_ind2partboa"] / sankey_rw_prod_in_hwp["wp_sum"]
    )
    sankey_rw_prod_in_hwp["fWP_pv"] = (
        sankey_rw_prod_in_hwp["pan_ind2plyven"] / sankey_rw_prod_in_hwp["wp_sum"]
    )

    # load recyled wood and paper
    sankey_rw_prod_in_hwp["rec_wood_swe_m3"] = sankey_rw_prod_in_hwp["pcw2pan_ind"]
    sankey_rw_prod_in_hwp["rec_paper_swe_m3"] = sankey_rw_prod_in_hwp["recpap2pap_ind"]

    # load the export of roundwood
    # retain only rows relevant for production of hwp

    sankey_rw_prod_in_exp = sankey_rw_prod_in[
        (sankey_rw_prod_in["label"] == "rw_tot2rw4mat")
        | (sankey_rw_prod_in["label"] == "pu4pa2pap_ind")
    ]
    sankey_rw_prod_in_exp = sankey_rw_prod_in_exp[
        ["scenario", "country", "year", "data", "unit", "label"]
    ]
    sankey_rw_prod_in_exp = sankey_rw_prod_in_exp.pivot(
        index=["scenario", "country", "year"], columns="label", values="data"
    )
    sankey_rw_prod_in_exp["rw_export"] = (
        sankey_rw_prod_in_exp["rw_tot2rw4mat"] + sankey_rw_prod_in_exp["pu4pa2pap_ind"]
    )

    # sankey_rw_prod_in_exp
    # assess_shares = sankey_rw_prod_in_hwp[['fSW', 'fWP','fPP']]

    # complete the db with needed information
    # fSW = assess_shares.loc['cumulated_values', 'fSW']
    # fWP = assess_shares.loc['cumulated_values', 'fWP']
    # fPP = assess_shares.loc['cumulated_values', 'fPP']
    # fFW = assess_shares.loc['cumulated_values', 'fFW']
    # rec_wood_swe_m3 = sankey_rw_prod_in_hwp.rec_wood_swe_m3.mean()
    # rec_paper_swe_m3 = sankey_rw_prod_in_hwp.rec_paper_swe_m3.mean()

    # add further data needed for recycling later
    fWP_fibboa = sankey_rw_prod_in_hwp["fWP_fibboa"].mean()
    fWP_partboa = sankey_rw_prod_in_hwp["fWP_partboa"].mean()
    fWP_pv = sankey_rw_prod_in_hwp["fWP_pv"].mean()

    # reorganize
    sankey_rw_prod = sankey_rw_prod_in_hwp[
        [
            "scenario",
            "country",
            "year",
            "fSW",
            "fPP",
            "fWP",
            "fWP_fibboa",
            "fWP_partboa",
            "fWP_pv",
            "rec_wood_swe_m3",
            "rec_paper_swe_m3",
        ]
    ].copy()

    # add absolute amounts of export of roundwood
    rw_export_thou_swe_m3 = sankey_rw_prod_in_exp.rw_export.mean()
    sankey_rw_prod.loc[:, "rw_export_thou_swe_m3"] = rw_export_thou_swe_m3

    # convert Sankey volume data to carbon, by taking into account the share of con to broad, and wd
    sankey_rw_prod["rw_export_tc"] = (
        1000 * wd_con_broad * c_fraction * sankey_rw_prod["rw_export_thou_swe_m3"]
    )

    # estimate the correction
    # retain only rows relevant with annual data on irw_amount allocated to products
    sankey_irw_solid = sankey_rw_prod_in[sankey_rw_prod_in["label"] == "rw_tot2rw4mat"]
    # sankey_irw_solid

    return sankey_rw_prod


# %%
def silv_grouping_to_hwp():
    Silv_grouping_to_hwp = silv_to_hwp
    Silv_grouping_to_hwp = Silv_grouping_to_hwp.rename(
        columns={"dist_type_name": "disturbance_type"}
    )
    return Silv_grouping_to_hwp
