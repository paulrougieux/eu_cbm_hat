from functools import cached_property
from typing import List, Union

class Area:
    """Compute the area changes through time and across classifiers


    Investigate issues with area changes

        >>> from eu_cbm_hat.core.continent import continent
        >>> import matplotlib.pyplot as plt
        >>> runner = continent.combos['reference'].runners['LU'][-1]
        >>> area = runner.post_processor.area.df

    Total area stays constant through time

        >>> total_area = area.groupby("year")["area"].sum()
        >>> total_area.round().unique()

    The status changes through time

        >>> area_st = area.groupby(["year", "status"])["area"].sum().reset_index()
        >>> area_st = area_st.pivot(columns="status", index="year", values="area")
        >>> area_st.plot()
        >>> plt.show()

    Why is it needed to group by classifiers first.

        >>> index = runner.post_processor.classifiers.columns.to_list()
        >>> index.remove("identifier")
        >>> df.value_counts(index, sort=False)
    
    At the end of the simulation a given set of classifiers can be repeated a
    thousand times with different values of time since last disturbance, last
    disturbance type, age class etc.

    At the classifier level


    At the year and status level

    """

    def __init__(self, parent):
        self.parent = parent
        self.runner = parent.runner
        self.combo_name = self.runner.combo.short_name
        self.pools = self.parent.pools
        self.fluxes = self.parent.fluxes
        self.classifiers = self.parent.classifiers

    @cached_property
    def df(self):
        """Area  at the most level of details available"""
        # TODO: remove pools columns, keep only status columns
        df = self.pools
        return df

    @cached_property
    def df_agg_by_classifiers(self):
        """Area t and area t-1 at the classifier level"""
        df = self.df
        index = self.classifiers.columns.to_list()
        # TODO: group by classifiers columns first
        time_columns = ["identifier", "year", "timestep"]
        index = [col for col in index if col not in time_columns]
        df.sort_values(["year"] + index, inplace=True)
        df["area_tm1"] = df.groupby(index)["area"].transform(lambda x: x.shift())

    def df_agg(self, groupby: Union[List[str], str] = None):
        """Area aggregated by the given grouping variables"""

