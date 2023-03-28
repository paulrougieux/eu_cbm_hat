#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.

Usage:

    >>> from eu_cbm_hat.core.continent import continent
    >>> runner = continent.combos['special'].runners["ZZ"][-1]
    >>> runner.qaqc.aidb_check.run_all_checks()

"""

# Built-in modules #

# Third party modules #
import numpy

# First party modules #

# Internal modules #

class AIDBCheck:
    """
    Check the consistency of the AIDB

        >>> from eu_cbm_hat.core.continent import continent
        >>> runner = continent.combos['special'].runners["ZZ"][-1]

    Check id duplication in vol_to_bio_factor

        >>> runner.qaqc.aidb_check.check_vol_to_bio_factor_id_duplication()

    """
    def __init__(self, qaqc):
        # Default attributes #
        self.runner = qaqc.runner
        self.aidb = self.runner.country.aidb

    def run_all_checks(self):
        """Run all AIDB checks"""
        self.check_vol_to_bio_factor_id_duplication()

    def check_vol_to_bio_factor_id_duplication(self):
        """Investigate identifier duplication in the vol_to_bio_factor in the AIDB"""
        df = self.aidb.db.read_df('vol_to_bio_factor')
        # Select duplicated rows
        selector = df["id"].duplicated(keep=False)
        if any(selector):
            msg = "Duplicated ids in the vol_to_bio_factor table in the AIDB."
            msg += "The following rows are duplicated:\n"
            msg += f"{df[selector]}\n\n"
            msg += "Investigate by loading the table with a command similar to this one:\n"
            msg += "runner.country.aidb.db.read_df('vol_to_bio_factor')"
            raise ValueError(msg)
