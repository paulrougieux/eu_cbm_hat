
from eu_cbm_hat import eu_cbm_data_pathlib
from functools import cached_property
import pandas as pd

class HWPInput():
    """Input data for Harvested Wood Product sink computation"""

    def __init__(self, parent):
        self.parent = parent

    @cached_property
    def hwp_types(self):
        # this is the types of wood use data to be retrieved from FAOSTAT
        HWP_types = pd.read_csv(eu_cbm_data_pathlib / 'common/hwp_types.csv')
        return HWP_types
    
    @cached_property
    def eu_member_states (self):
        #list of EU MS
        EU_member_states = pd.read_csv(eu_cbm_data_pathlib / 'common/eu_member_states.csv')
        return EU_member_states
    
    @cached_property
    def faostat_bulk_data (self):
        #faostat as downloaded as bulk from FAOSTAT, namely :"Forestry_E_Europe" is a bulk download from  FAOSTAT. 
        Faostat_bulk_data = pd.read_csv(eu_cbm_data_pathlib / 'common/Forestry_E_Europe.csv', low_memory=False)
        return Faostat_bulk_data

    @cached_property
    def euwrb_stat (self):
        # input Sankey data
        EUwrb_stat = pd.read_csv(eu_cbm_data_pathlib / 'common/forestry_sankey_data.csv')
        return EUwrb_stat

    @cached_property
    def fao_rw_prod_gapfilled (self):
        ## import FAOSTAT on IRW production on con and broad, data in volume (m3), this is gapfilled for historical periods
        FAO_rw_prod_gapfilled = pd.read_csv(eu_cbm_data_pathlib / 'common/irw_con_broad_faostat.csv')
        return FAO_rw_prod_gapfilled

    @cached_property
    def crf_stat (self):
        # crf sumbissions
        CRF_stat = pd.read_csv(eu_cbm_data_pathlib / 'common/hwp_crf_submission_2023.csv')
        CRF_stat = CRF_stat.rename(columns = {'country':'area'})
        return CRF_stat

    @cached_property
    def subst_params (self):
        # substitution file
        Subst_params = pd.read_csv(eu_cbm_data_pathlib / 'common/substitution_factors.csv')
        return Subst_params

    @cached_property
    def subst_ref (self):
        # substitution reference scenario
        Subst_ref = pd.read_csv( eu_cbm_data_pathlib / 'common/substitution_reference_scenario.csv')
        return Subst_ref  
    
    @cached_property
    def silv_to_hwp (self):
        # substitution reference scenario
        Silv_to_hwp = pd.read_csv( eu_cbm_data_pathlib / 'common/silv_practices_to_hwp.csv')
        return Silv_to_hwp
