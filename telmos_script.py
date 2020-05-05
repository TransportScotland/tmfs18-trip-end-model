# -*- coding: utf-8 -*-
"""

@author: japeach

Conversion of TELMOS2_v2.2 vb scripts
The telmos_xxx files all replicate the old TMfS14 VB functions of the same names
"""

import sys

from telmos_main import telmos_main
from telmos_goods import telmos_goods
from telmos_addins import telmos_addins

def telmos_all(delta_root, tmfs_root, tel_year, tel_id, tel_scenario, base_year, 
         base_id, base_scenario, rebasing_run, do_output, do_debug, 
         thread_queue=None, print_func=print, just_pivots=False):
    
    if print_func is None:
        print_func = print
    try:
        main_diffs = telmos_main(delta_root, tmfs_root, tel_year, tel_id, tel_scenario, 
                    base_year, base_id, base_scenario, is_rebasing_run=rebasing_run,
                    do_output=do_output, debug=do_debug, log_func=print_func,
                    just_pivots=just_pivots)
        if just_pivots is False:
            goods_diffs = telmos_goods(delta_root, tmfs_root, tel_year, tel_id, tel_scenario, 
                        base_year, base_id, base_scenario, is_rebasing_run=rebasing_run,
                        do_output=do_output, debug=do_debug, log_func=print_func)
            
            addin_diffs = telmos_addins(delta_root, tmfs_root, tel_year, tel_id, tel_scenario, 
                        base_year, base_id, base_scenario, 
                        do_output=do_output, debug=do_debug, log_func=print_func)
    except Exception:
        thread_queue.put(sys.exc_info())
        return
    
    if do_debug is True:
        print("Matrix Differences:")
        diffs = (main_diffs, goods_diffs, addin_diffs)
        for d in diffs:
            for k, v in d.items():
                print("Matrix %s difference = %f%%" % (k, 100*v))
    
        print("Finished")
        thread_queue.put(diffs)
    else:
        print_func("Finished")
        thread_queue.put(None)
    
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
         rebasing_run=False, do_output=True, do_debug=False, just_pivots=False)
    
