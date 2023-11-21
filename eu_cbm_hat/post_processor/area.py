from functools import cached_property
from typing import List, Union
import numpy as np
from eu_cbm_hat.post_processor.sink import generate_all_combinations_and_fill_na

class Area:
    """Compute the area changes through time and across classifiers

    Usage

        >>> from eu_cbm_hat.core.continent import continent
        >>> import matplotlib.pyplot as plt
        >>> runner = continent.combos['reference'].runners['LU'][-1]
        >>> df = runner.post_processor.area.df

    Total area stays constant through time

        >>> total_area = df.groupby("year")["area"].sum()
        >>> total_area.round().unique()

    The status changes through time

        >>> area_cols = df.columns[df.columns.str.contains("area")].to_list()
        >>> area_st = df.groupby(["year", "status"])[area_cols].sum().reset_index()
        >>> area_st_wide = area_st.pivot(columns="status", index="year", values="area")
        >>> area_st_wide.plot()
        >>> plt.show()

    Is the area stable or changing across each of the other classifiers?

        >>> cols = runner.post_processor.classifiers.columns.to_list()
        >>> cols = [x for x in cols if x not in ["identifier", "year"]]
        >>> for cl in cols:
        >>>     print(cl)
        >>>     df_cl = df.groupby([cl, "year"])["area"].sum().reset_index()
        >>>     print(df_cl["area"].round().unique())

    Area grouped by classifiers

        >>> df_agg_cl = runner.post_processor.area.df_agg_by_classifiers

    Group area by status and check if the diff in area is explained by afforestation and deforestation

        >>> area_st = runner.post_processor.area.df_agg(["year", "status"])
        >>> area_st["area_diff"] = area_st["area"] - area_st["area_tm1"]

    Investigate issues with area changes. Is the diff in ForAWS and ForNAWS
    area equal to deforestation + afforestation?

        >>> df_st = runner.post_processor.area.df_agg(["year", "status"])
        >>> df_st.query("year in [2021, 2022, 2023]")
        >>> df_st["area_diff"] = df_st["area"] - df_st["area_tm1"]

    Group by "time_since..." variables

        >>> index = ["year", "status", "last_disturbance_type", 'time_since_last_disturbance']
        >>> index += ["time_since_land_class_change", "land_class"]
        >>> cols = ["area", "area_deforested_current_year", "area_afforested_current_year"]
        >>> df3 = df.query("year in [2021, 2022, 2023]").groupby(index)[cols].agg("sum")

    
    Why do we need to group by classifiers first?

        >>> index = runner.post_processor.classifiers.columns.to_list()
        >>> index.remove("identifier")
        >>> df.value_counts(index, sort=False)

    At the end of the simulation a given set of classifiers can be repeated a
    thousand times with different values of time since last disturbance, last
    disturbance type, age class etc.

    Group by region, climate and status

        >>> area_reclst = df.groupby(runner.post_processor.sink.groupby_sink)["area"].sum().reset_index()

    """

    def __init__(self, parent):
        self.parent = parent
        self.runner = parent.runner

    @cached_property
    def df(self):
        """Area  at the most level of details available"""
        df = self.parent.pools
        selected_cols = ['identifier',
                         'timestep',
                         'year',
                         'status',
                         'forest_type',
                         'region',
                         'mgmt_type',
                         'mgmt_strategy',
                         'climate',
                         'con_broad',
                         'site_index',
                         'growth_period',
                         'last_disturbance_type',
                         'time_since_last_disturbance',
                         'time_since_land_class_change',
                         'growth_enabled',
                         'enabled',
                         'land_class',
                         'age',
                         'growth_multiplier',
                         'regeneration_delay']
        selected_cols += df.columns[df.columns.str.contains("area")].to_list()
        return df

    @cached_property
    def df_agg_by_classifiers(self):
        """Area t at the classifier level"""
        index = self.parent.classifiers.columns.to_list()
        index.remove("identifier")
        area_columns = self.df.columns[self.df.columns.str.contains("area")].to_list()
        df_agg = self.df.groupby(index)[area_columns].agg("sum").reset_index()
        return df_agg

    def df_agg(self, groupby: Union[List[str], str] = None):
        """Area aggregated by the given grouping variables and area t-1  """
        if isinstance(groupby, str):
            groupby = [groupby]
        df = self.df_agg_by_classifiers
        # Aggregate by the given groupby variables
        area_columns = df.columns[df.columns.str.contains("area")].to_list()
        df_agg = df.groupby(groupby)[area_columns].agg("sum").reset_index()
        # Index to compute the area at t-1
        time_columns = ["identifier", "year", "timestep"]
        index = [col for col in groupby if col not in time_columns]
        # Arrange by group variable with year last to prepare for shift()
        df_agg.sort_values(index + ["year"], inplace=True)
        df_agg["area_tm1"] = df_agg.groupby(index)["area"].transform(lambda x: x.shift())
        return df_agg

    def afforestation_deforestation(self, check=True, rtol=1e-3):
        """Check afforestation and deforestation area changes recorded in
        post_processor.pools correspond to the diff in area

        If check is False do not enforce the consistency check. Use for
        debugging purposes.

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
        if check:
            np.testing.assert_allclose(df_agg["area_afforested_current_year"],
                                       df_agg["diff_AR"], rtol=rtol)
        return df_agg
