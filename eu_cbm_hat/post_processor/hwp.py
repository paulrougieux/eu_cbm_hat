from functools import cached_property
import pandas


class HWP:
    """Compute the Harvested Wood Products Sink

    >>> from eu_cbm_hat.core.continent import continent
    >>> runner = continent.combos['reference'].runners['LU'][-1]
    >>> runner.post_processor.hwp

    """

    def __init__(self, parent):
        self.parent = parent
        self.runner = parent.runner
        self.combo_name = self.runner.combo.short_name
        # Use pool fluxes to get area and age class
        self.pools_fluxes = self.runner.output.pool_flux

    def __repr__(self):
        return '%s object code "%s"' % (self.__class__, self.runner.short_name)

    @cached_property
    def fluxes_to_products(self) -> pandas.DataFrame:
        """Fluxes to products retain from the cbm output the all transfers to
        products pool Remove lines where there are no fluxes to products. Keep
        only lines with positive flues.

            >>> from eu_cbm_hat.core.continent import continent
            >>> runner = continent.combos['reference'].runners['LU'][-1]
            >>> runner.post_processor.hwp.fluxes_to_products
        """
        classifiers_list = self.parent.classifiers_list
        index_cols = ["year", "area", "disturbance_type", "age_class"]
        fluxes_cols = [
            "softwood_merch_to_product",
            "softwood_other_to_product",
            "softwood_stem_snag_to_product",
            "softwood_branch_snag_to_product",
            "hardwood_merch_to_product",
            "hardwood_other_to_product",
            "hardwood_stem_snag_to_product",
            "hardwood_branch_snag_to_product",
        ]
        cols_of_interest = classifiers_list + index_cols + fluxes_cols
        df = self.pools_fluxes[cols_of_interest]
        # Keep only lines where there are fluxes to products.
        selector = df[fluxes_cols].sum(axis=1) > 0
        return df.loc[selector].reset_index(drop=True)



