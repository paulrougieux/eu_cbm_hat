#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.
"""

# Built-in modules #
from typing import Dict

# Third party modules #

# First party modules #
from autopaths.auto_paths import AutoPaths
from plumbing.cache       import property_cached

# Internal modules #
from eu_cbm_hat.constants import eu_cbm_data_dir
from eu_cbm_hat.core.country import Country
from eu_cbm_hat.combos       import combo_classes_dict
from eu_cbm_hat.combos.base_combo import Combination
from eu_cbm_hat.constants import eu_cbm_data_pathlib


###############################################################################
class Continent(object):
    """
    Entry object to the pipeline.

    Aggregates countries together and enables access to a data frame containing
    concatenated data from all countries at once.

    Create a runner:

    >>> from eu_cbm_hat.core.continent import continent
    >>> runner = continent.combos['reference'].runners['ZZ'][-1]

    Create a runner using a shortcut:

    >>> runner = continent[("reference", "ZZ", -1)]

    """

    all_paths = """
    /countries/
    /output/
    """

    def __init__(self, base_dir):
        """
        Store the directory paths where there is a directory for every
        country and for every combo.
        """
        # The base directory #
        self.base_dir = base_dir
        # Automatically access paths based on a string of many subpaths #
        self.paths = AutoPaths(eu_cbm_data_dir, self.all_paths)
        # Where the input data will be stored #
        self.countries_dir = self.paths.countries_dir
        # Where the output data will be stored #
        self.output_dir = self.paths.output_dir

    def __repr__(self):
        return '%s object with %i countries' % (self.__class__, len(self))

    def __getitem__(self, key):
        """Return a runner based on a tuple of combo, country and step."""
        return self.get_runner(*key)

    def __iter__(self): return iter(self.countries.values())
    def __len__(self):  return len(self.countries.values())

    #----------------------------- Properties --------------------------------#
    @property_cached
    def countries(self):
        """Return a dictionary of country iso2 codes to country objects."""
        all_countries = [Country(self, d)
                         for d in self.countries_dir.flat_directories]
        return {c.iso2_code: c for c in all_countries}

    @property
    def combos(self)-> Dict[str, 'Combination']:
        """Return a dictionary of combination names to Combination objects."""
        combo_dir = eu_cbm_data_pathlib / "combos"
        # List hard coded combo classes
        hard_coded_combos = [combo(self, short_name) for short_name, combo in combo_classes_dict.items()]
        # List yaml files
        yaml_short_names = [x.stem for x in combo_dir.glob('**/*.yaml')]
        # Remove short_names which correspond to hard coded combos
        yaml_short_names = list(set(yaml_short_names) - set(combo_classes_dict.keys()))
        # Create combos from yaml files
        combos_from_yaml_files = [Combination(self, short_name) for short_name in yaml_short_names]
        # List all combos
        all_combos = hard_coded_combos + combos_from_yaml_files
        return {s.short_name: s for s in all_combos}

    #------------------------------- Methods ---------------------------------#
    def get_runner(self, combo, country, step):
        """Return a runner based on combo, country and step."""
        return self.combos[combo].runners[country][step]

###############################################################################
# Create singleton #
continent = Continent(eu_cbm_data_dir)

