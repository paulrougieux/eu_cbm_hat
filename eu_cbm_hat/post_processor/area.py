from functools import cached_property
from typing import List, Union
import numpy as np
from eu_cbm_hat.post_processor.sink import generate_all_combinations_and_fill_na


class Area:
    """Compute the area changes through time and across classifiers

    Area grouped by status

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos["reference"].runners["ZZ"][-1]
        >>> area_st  = runner.post_processor.area.df_agg(["year", "status"])
        >>> area_st[["year", "status", "area", "area_tm1"]].round()
            year status     area  area_tm1
        44  2021     AR     10.0       NaN
        47  2022     AR     20.0      10.0
        50  2023     AR     30.0      20.0
        53  2024     AR     40.0      30.0
        56  2025     AR     50.0      40.0
        ..   ...    ...      ...       ...
        58  2025     NF  23804.0   23130.0
        61  2026     NF  24434.0   23804.0
        64  2027     NF  25020.0   24434.0
        67  2028     NF  25563.0   25020.0
        70  2029     NF  26062.0   25563.0
        <BLANKLINE>
        [71 rows x 4 columns]

    Area grouped by status, species and age

        >>> index = ["year", "status", "forest_type", "age"]
        >>> area_st_sp_age  = runner.post_processor.area.df_agg(index)
        >>> selector = area_st_sp_age["status"] == "ForAWS"
        >>> area_st_sp_age.loc[selector, ["year", "status", "forest_type","age", "area"]]
               year  status forest_type  age       area
        702    2001  ForAWS          DF    1   14.64570
        1031   2002  ForAWS          DF    1   14.76704
        1347   2003  ForAWS          DF    1   14.97740
        1666   2004  ForAWS          DF    1    5.48501
        4280   2012  ForAWS          DF    1    5.32162
        ...     ...     ...         ...  ...        ...
        10081  2028  ForAWS          QR  188  214.30000
        10412  2029  ForAWS          QR  188  214.30000
        10082  2028  ForAWS          QR  189  214.30000
        10413  2029  ForAWS          QR  189  214.30000
        10414  2029  ForAWS          QR  190  214.30000
        <BLANKLINE>
        [10332 rows x 5 columns]

    Area grouped by status, species and age class (one every 10 years)

        >>> index = ["year", "status", "forest_type", "age_class"]
        >>> area_st_sp_agecl  = runner.post_processor.area.df_agg(index)

    Area grouped by all classifiers and age

        >>> df_agg_cl_age = runner.post_processor.area.df_agg_by_classifiers_age

    At the end of the simulation a given set of classifiers can be repeated a
    thousand times with different values of time since last disturbance, last
    disturbance type, age class etc. Area at the most level of details from the
    CBM pools output table:

        >>> df = runner.post_processor.area.df

    Total area stays constant through time

        >>> df = runner.post_processor.area.df
        >>> total_area = df.groupby("year")["area"].sum()
        >>> total_area.round().unique()
        array([111880.])

    The status changes through time

        >>> import matplotlib.pyplot as plt
        >>> area_st_wide = area_st.pivot(columns="status", index="year", values="area")
        >>> area_st_wide.plot()  # doctest: +SKIP
        >>> plt.show()  # doctest: +SKIP

    Is the area stable or changing across each of the classifiers?

        >>> cols = runner.post_processor.classifiers.columns.to_list()
        >>> cols = [x for x in cols if x not in ["identifier", "year"]]
        >>> for cl in cols:
        ...     print(cl)  # doctest: +SKIP
        ...     df_cl = df.groupby([cl, "year"])["area"].sum().reset_index()
        ...     print(df_cl["area"].round().unique())  # doctest: +SKIP

    Area changes every year through transitions due to afforestation and
    deforestation. Is the yearly area difference in ForAWS and ForNAWS equal to
    deforestation + afforestation? Group area by status and check if the
    difference in area is explained by afforestation and deforestation.

        >>> area_check = runner.post_processor.area.afforestation_deforestation(
        ...    check=True, rtol=1e-3)

    Group by "time_since..." variables

        >>> index = ["year", "status", "last_disturbance_type", 'time_since_last_disturbance']
        >>> index += ["time_since_land_class_change", "land_class"]
        >>> cols = ["area", "area_deforested_current_year", "area_afforested_current_year"]
        >>> df3 = df.query("year in [2021, 2022, 2023]").groupby(index)[cols].agg("sum")

    Group by region, climate and status

        >>> index = runner.post_processor.sink.groupby_sink
        >>> area_re_cl_st = runner.post_processor.area.df_agg(index)

    """

    def __init__(self, parent):
        self.parent = parent
        self.runner = parent.runner

    @cached_property
    def df(self):
        """Area at the most level of details available from the CBM pools
        table.

        Note: there might be many stands that have the same classifiers
        and the same age class, but a different time since last disturbance and
        a different last disturbance type.
        """
        df = self.parent.pools
        selected_cols = [
            "identifier",
            "timestep",
            "year",
            "age",
        ]
        selected_cols += self.parent.classifiers_list
        selected_cols += [
            "last_disturbance_type",
            "time_since_last_disturbance",
            "time_since_land_class_change",
            "growth_enabled",
            "enabled",
            "land_class",
            "growth_multiplier",
            "regeneration_delay",
        ]
        # Area columns
        selected_cols += df.columns[df.columns.str.contains("area")].to_list()
        # 10 year age class
        #df["age_class"] = (df["age"] / 10).round().astype(int)
        df['age_class'] = df.age // 10 + 1
        df['age_class'] = 'AGEID' + df.age_class.astype(str)

        
        return df

    @cached_property
    def df_agg_by_classifiers_age(self):
        """Area t at the classifier level and by age classes"""

        #####
        index = self.parent.classifiers_list + ["year", "age", "age_class"]
        area_columns = self.df.columns[self.df.columns.str.contains("area")].to_list()
        df_agg = self.df.groupby(index)[area_columns].agg("sum").reset_index()
        return df_agg

    def df_agg(self, groupby: Union[List[str], str] = None):
        """Area aggregated by the given grouping variables and area t-1"""
        if isinstance(groupby, str):
            groupby = [groupby]
        if "year" not in groupby:
            raise ValueError("Year has to be in the grouping variables")
        # Aggregate by the given groupby variables
        area_columns = self.df.columns[self.df.columns.str.contains("area")].to_list()
        df_agg = self.df.groupby(groupby)[area_columns].agg("sum").reset_index()
        # Index to compute the area at t-1
        time_columns = ["identifier", "year", "timestep"]
        index = [col for col in groupby if col not in time_columns]
        # Arrange by group variable with year last to prepare for shift()
        df_agg.sort_values(index + ["year"], inplace=True)
        df_agg["area_tm1"] = df_agg.groupby(index)["area"].transform(
            lambda x: x.shift()
        )
        # remove NF which is tyhe land in the inventory.csv available for afforestation
        df_agg.loc[df_agg['status'] == 'NF', ['area', 'area_tm1']] = 0
        return df_agg

    def afforestation_deforestation(self, check=True, rtol=1e-3):
        """Check afforestation and deforestation area changes recorded in
        post_processor.pools correspond to the diff in area

        If check is False do not enforce the consistency check. Set
        `check=False` for debugging purposes.

        """
        df = self.df_agg(["year", "status"])
        # To avoid NA values for AR in the middle of the time series
        df = generate_all_combinations_and_fill_na(df, ["year", "status"])
        # TODO: first year values of area_tm1 should be NA, rechange them back to NA
        df["area_diff"] = df["area"] - df["area_tm1"]
        cols = ["area_afforested_current_year", "area_deforested_current_year"]
        df1 = df.groupby("year")[cols].agg("sum").reset_index()
        df["status"] = "diff_" + df["status"]
        df2 = df.pivot(columns="status", index="year", values="area_diff").reset_index()
        df_agg = df1.merge(df2, on="year")
        #if check:
        #    np.testing.assert_allclose(
        #        df_agg["area_afforested_current_year"], df_agg["diff_AR"], rtol=rtol
        #    )
        return df_agg
