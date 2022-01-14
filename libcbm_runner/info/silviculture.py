#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.
"""

# Built-in modules #

# Third party modules #
import pandas

# First party modules #
from plumbing.cache import property_cached

# Internal modules #

###############################################################################
class Silviculture:
    """
    Access to silvicultural information pertaining to a given country.
    This includes the following files:

    * irw_frac_by_dist.csv
    * vol_to_mass_coefs.csv
    * events_templates.csv
    * harvest_factors.csv

    Each is accessed by its own corresponding attribute:

    * `silv.irw_frac`
    * `silv.coefs`
    * `silv.events`
    * `silv.harvest`

    Loading this information will fail if you call `df` before a simulation
    is launched, because we need the internal SIT classifier and disturbance
    mapping.
    """

    def __init__(self, runner):
        # Default attributes #
        self.runner = runner
        # Shortcuts #
        self.country = self.runner.country

    @property_cached
    def irw_frac(self):
        return IRWFractions(self)

    @property_cached
    def coefs(self):
        return VolToMassCoefs(self)

    @property_cached
    def events(self):
        return EventsTemplates(self)

    @property_cached
    def harvest(self):
        return HarvestFactors(self)

###############################################################################
class BaseSilvInfo:
    """
    A class that contains methods common to all silvicultural information
    files. You should inherit from this class.
    """

    def __init__(self, silv):
        # Default attributes #
        self.silv = silv
        # Shortcuts #
        self.runner  = self.silv.runner
        self.country = self.silv.country
        self.combo   = self.runner.combo
        self.code    = self.country.iso2_code

    #----------------------------- Properties --------------------------------#
    @property_cached
    def raw(self):
        return pandas.read_csv(self.csv_path,
                               dtype = {c:'str' for c in self.cols})

    @property_cached
    def cols(self):
        return list(self.country.orig_data.classif_names.values()) + \
               ['disturbance_type']

    @property_cached
    def dup_cols(self):
        return ['scenario'] + self.cols

    @property_cached
    def df(self):
        # Make a check of duplicated entries #
        self.duplication_check()
        # Optional extra checks #
        if hasattr(self, 'extra_checks'): self.extra_checks()
        # Load #
        df = self.raw.copy()
        # Drop the names which are useless #
        if 'dist_type_name' in self.raw.columns:
            # Make a consistency check between dist_name and dist_id #
            self.consistency_check()
            df = df.drop(columns='dist_type_name')
        # Convert the disturbance IDs to the real internal IDs #
        df = self.conv_dists(df)
        # Convert the classifier IDs to the real internal IDs #
        df = self.conv_clfrs(df)
        # Return #
        return df

    #------------------------------- Methods ---------------------------------#
    def conv_dists(self, df):
        """
        Convert the disturbance IDs such as `20` and `22` into their
        internal simulation ID numbers that are defined by SIT.
        """
        # Get the conversion mapping and invert it #
        id_to_id = self.runner.simulation.sit.disturbance_id_map
        id_to_id = {v:k for k,v in id_to_id.items()}
        # Apply the mapping to the dataframe #
        df['disturbance_type'] = df['disturbance_type'].map(id_to_id)
        # Return #
        return df

    def conv_clfrs(self, df):
        """
        Convert the classifier values such as `PA` and `QA` into their
        internal simulation ID numbers that are defined by SIT.
        """
        # Get all the conversion mappings, for each classifier #
        all_maps = self.runner.simulation.sit.classifier_value_ids.items()
        # Apply each of them to the dataframe #
        for classif_name, str_to_id in all_maps:
            if classif_name not in df.columns: continue
            df[classif_name] = df[classif_name].map(str_to_id)
        # Return #
        return df

    def consistency_check(self):
        # Get mapping dictionary from ID to full description #
        id_to_name = self.country.orig_data['disturbance_types']
        id_to_name = dict(zip(id_to_name['dist_type_name'],
                              id_to_name['dist_desc_input']))
        # Compare #
        names = self.raw['disturbance_type'].map(id_to_name)
        orig  = self.raw['dist_type_name']
        comp  = orig == names
        # Raise exception #
        if not all(comp):
            msg = "Names don't match IDs in '%s'.\n" % self.csv_path
            msg += "Names derived from the IDs:\n"
            msg += str(names[~comp])
            msg += "\n\nNames in the user file:\n"
            msg += str(orig[~comp])
            raise Exception(msg)

    def duplication_check(self):
        # What columns are we going to check duplication on #
        cols = self.dup_cols
        # Get duplicated rows #
        dups = self.raw.duplicated(subset=cols, keep=False)
        # Assert #
        if any(dups):
            msg = "There are duplicated entries in the file '%s'."
            msg += "\nThe duplicated rows are shown below:\n\n"
            msg += str(self.raw.loc[dups, cols])
            raise Exception(msg % self.csv_path)

    def get_year(self, year):
        # Case number 1: there is only a single scenario specified #
        if isinstance(self.choices, str): scenario = self.choices
        # Case number 2: the scenarios picked vary according to the year #
        else: scenario = self.choices[year]
        # Retrieve by query #
        df = self.df.query("scenario == '%s'" % scenario)
        # Drop the scenario column #
        df = df.drop(columns='scenario')
        # Check there is data left #
        assert not df.empty
        # Return #
        return df

###############################################################################
class IRWFractions(BaseSilvInfo):
    """
    Gives access the industrial roundwood fractions, per disturbance type,
    for the current simulation run.
    """

    @property
    def choices(self):
        """Choices made for `irw` fraction in the current combo."""
        return self.combo.config['irw_frac_by_dist']

    @property
    def csv_path(self):
        return self.country.orig_data.paths.irw_csv

###############################################################################
class VolToMassCoefs(BaseSilvInfo):
    """
    Gives access to the coefficients that enable the conversion from
    wood volume to wood mass.
    """

    @property
    def csv_path(self):
        return self.country.orig_data.paths.vol_to_mass_csv

    @property
    def cols(self):
        return ['forest_type']

    @property
    def dup_cols(self):
        return self.cols

    @property_cached
    def df(self):
        # Make a check of duplicated entries #
        self.duplication_check()
        # Load #
        df = self.raw.copy()
        # Convert the classifier IDs to the real internal IDs #
        df = self.conv_clfrs(df)
        # Return #
        return df

###############################################################################
class EventsTemplates(BaseSilvInfo):
    """
    Gives access to the dynamic events that have to be generated to
    satisfy the demand.
    """

    @property
    def choices(self):
        """Choices made for the events template in the current combo."""
        return self.combo.config['events_templates']

    @property
    def csv_path(self):
        return self.country.orig_data.paths.events_templates

    @property
    def dup_cols(self):
        return list(self.country.orig_data.classif_names.values()) + \
               ['scenario', 'sw_start', 'sw_end', 'hw_start', 'hw_end']

    def extra_checks(self):
        # Guarantee no difference between sw_start and hw_start #
        assert all(self.raw['sw_start'] == self.raw['hw_start'])
        # Guarantee no difference between sw_end and hw_end #
        assert all(self.raw['sw_end'] == self.raw['hw_end'])
        # Guarantee we don't use max_since_last_dist #
        assert all(self.raw['max_since_last_dist'] == -1)

###############################################################################
class HarvestFactors(BaseSilvInfo):
    """
    Gives access to the data in the file `harvest_factors.csv`.
    """

    @property
    def choices(self):
        """Choices made for the harvest factors in the current combo."""
        return self.combo.config['harvest_factors']

    @property
    def csv_path(self):
        return self.country.orig_data.paths.harvest_factors

    @property
    def cols(self):
        return ['forest_type', 'mgmt_type', 'disturbance_type']