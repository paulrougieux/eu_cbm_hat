from functools import cached_property
from typing import List, Union
import numpy as np

class Stock:
    #def __init__(self, parent):
        #self.parent = parent
        #self.pools = self.parent.pools
        
        
    #@cached_property
    def dw_stock_ratio(self):
        """Estimate the ratio of standing stocks, dead_wood to merchantable """
        # Aggregate by the classifier for which it is possible to compute a
        # difference in pools.
        
        dw_pools = self.pools
        dw_pools['softwood_dw_ratio'] = dw_pools['softwood_stem_snag'] / dw_pools['softwood_merch']
        dw_pools['hardwood_dw_ratio'] = dw_pools['hardwood_stem_snag'] / dw_pools['hardwood_merch']
        
        # Aggregate separately for softwood and hardwood
        softwood_stock = dw_pools.groupby('year').agg(softwood_dw_ratio=('softwood_dw_ratio', np.mean))
        hardwood_stock = dw_pools.groupby('year').agg(hardwood_dw_ratio=('hardwood_dw_ratio', np.mean))
        return hardwood_stock,softwood_stock