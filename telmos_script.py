# -*- coding: utf-8 -*-
"""

@author: japeach

Conversion of TELMOS2_v2.2 vb scripts
The telmos_xxx files all replicate the old TMfS14 VB functions of the same names
"""

import sys
import os

from telmos_main import telmos_main
from telmos_goods import telmos_goods
from telmos_addins import telmos_addins

def telmos_all(delta_root, tmfs_root, tel_year, tel_id, tel_scenario, base_year, 
         base_id, base_scenario, rebasing_run, 
         thread_queue=None, print_func=print, just_pivots=False):
    
    if print_func is None:
        print_func = print
        
    try:
        # Create a new directory for the output if it does not already exist
        output_dir = os.path.join(tmfs_root, "Runs", tel_year, "Demand", tel_id)
        if os.path.exists(output_dir) is False:
            os.mkdir(output_dir)
        
        telmos_main(delta_root, tmfs_root, tel_year, tel_id, tel_scenario, 
                    base_year, base_id, base_scenario, is_rebasing_run=rebasing_run,
                    log_func=print_func, just_pivots=just_pivots)
        if just_pivots is False:
            telmos_goods(delta_root, tmfs_root, tel_year, tel_id, tel_scenario, 
                        base_year, base_id, base_scenario, is_rebasing_run=rebasing_run,
                        log_func=print_func)
            
            telmos_addins(delta_root, tmfs_root, tel_year, tel_id, tel_scenario, 
                        base_year, base_id, base_scenario, log_func=print_func)
    except Exception:
        if thread_queue is not None:
            thread_queue.put(sys.exc_info())
            return
        else:
            # Not running from GUI so raise the exception as normal
            raise
    else:
        if thread_queue is not None:
            thread_queue.put(None)
        print_func("Finished")
        
    
if __name__ == "__main__":
    delta_root = "Data/Structure/delta_root"
    tmfs_root = "Data/Structure/tmfs_root"
    tel_year = "18"
    tel_id = "AAL"
    tel_scenario = "AL"
    base_year = "14"
    base_id = "AAE"
    base_scenario = "AE"
    diffs = telmos_all(delta_root, tmfs_root, tel_year, tel_id, tel_scenario,
         base_year, base_id, base_scenario,
         rebasing_run=False, just_pivots=False)
    
