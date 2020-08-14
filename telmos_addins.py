# -*- coding: utf-8 -*-
"""

@author: japeach

Conversion of TELMOS2_v2.2 vb scripts
"""

import os

import numpy as np
import pandas as pd

from data_functions import odfile_to_matrix, matrix_to_odfile


def telmos_addins(delta_root, tmfs_root, 
                tel_year, tel_id, tel_scenario,
                base_year, base_id, base_scenario, rtf_file="",
                ptf_file="", log_func=print):
    log_func("Processing Addins...")
    
    #low_zones = 783 ;; This is now increased to 787 to represent the internal 
    #                ;; Cannot be done without hardcoding low_zones number if separate
    #                ;; to the rest of the model
    low_zones = 787
    
    purposes = ["PT", "COM", "EMP", "OTH"]
    periods = ["AM", "IP", "PM"]
    filenames = ["%s%s.DAT" % (period, purpose) for period in periods 
                 for purpose in purposes]
    
    if rtf_file == "":
        rtf_file = os.path.join(tmfs_root, "Factors", "RTF.DAT")
    if ptf_file == "":
        ptf_file = os.path.join(tmfs_root, "Factors", "PTF.DAT")
    for factor_file in [rtf_file, ptf_file]:
        assert os.path.exists(factor_file), \
                "Addin factor file not found {}".format(factor_file)
    # Load NRTF Array
    rtf_array = pd.read_csv(rtf_file)
    ptf_array = pd.read_csv(ptf_file)
    
    addin_array = {}
    new_addin_array = {}
    for filename in filenames:
        f_key = filename.replace(".DAT", "")
        if "PT" not in f_key:
            num_columns = 1
        else:
            # PT file has 3 columns
            num_columns = 3
        addin_array[f_key] = odfile_to_matrix(os.path.join(tmfs_root, "Runs",
                   base_year, "Demand", base_id, filename), num_columns=num_columns)
        
        # Apply NRTF growth
        out_file = os.path.join(tmfs_root, "Runs", tel_year, 
                                           "Demand", tel_id, filename)
        if "PT" not in f_key:
            # Different rules if below 'low_zones'
            new_addin_array[f_key] = (addin_array[f_key] * 
                   rtf_array.loc[rtf_array.PERIOD==int(tel_year)+2000][
                           "CARS"].values[0] / 
                   rtf_array.loc[rtf_array.PERIOD==int(base_year)+2000][
                           "CARS"].values[0])
            new_addin_array[f_key][:low_zones,:low_zones] = (
                    addin_array[f_key][:low_zones,:low_zones])
            
            # Set the output options for non PT files - only one column is used
            output_array = new_addin_array[f_key]
            num_columns = 1
            
            # Set the output options for TE.DAT summary files
            te_array = np.stack((np.arange(new_addin_array[f_key].shape[0]) + 1,
                                 new_addin_array[f_key].sum(axis=1),
                                 new_addin_array[f_key].sum(axis=0)), axis=1)
            
        else:
            # Loop through the 3 pt matrices and apply factor from ptf array
            new_pt_arrays = []
            for i in range(len(addin_array[f_key])):
                new_pt_arrays.append(addin_array[f_key][i] * 
                         ptf_array.loc[ptf_array.PERIOD==int(tel_year)+2000][
                                 "PT"].values[0] / 
                         ptf_array.loc[ptf_array.PERIOD==int(base_year)+2000][
                                 "PT"].values[0])
                new_pt_arrays[i][:low_zones,:low_zones] = (
                        addin_array[f_key][i][:low_zones,:low_zones])
            new_addin_array[f_key] = new_pt_arrays
            
            # Set the output options for PT files - three columns are needed
            output_array = [x for x in new_addin_array[f_key]]
            num_columns = 3
            
            # Set the output options for TE.DAT summary files
            # For PT, format is:
            #   i, j, o_1, o_2, o_3, d_1, d_2, d_3
            te_array = np.stack((np.arange(new_addin_array[f_key][0].shape[0]) + 1,
                                 new_addin_array[f_key][0].sum(axis=1),
                                 new_addin_array[f_key][1].sum(axis=1),
                                 new_addin_array[f_key][2].sum(axis=1),
                                 new_addin_array[f_key][0].sum(axis=0),
                                 new_addin_array[f_key][1].sum(axis=0),
                                 new_addin_array[f_key][2].sum(axis=0)), axis=1)
            
        # Save full array to .DAT file
#        matrix_to_odfile(output_array, out_file, num_columns=num_columns)
            
        log_func("Saved matrix as %s" % str(out_file))
            
        # Check File sizes
        try:
            if new_addin_array[f_key].nbytes < 250000:
                log_func("Addin array is incomplete: %s" % f_key)
            
        except AttributeError:
            for m in new_addin_array[f_key]:
                if m.nbytes < 250000:
                    log_func("Addin array is incomplete: %s" % f_key)
        if te_array.nbytes < 500:
            log_func("Addin TE array is incomplete: %s" % f_key)
            
        out_file = os.path.join(tmfs_root, "Runs", tel_year, "Demand",
                                tel_id, filename.replace(".DAT", "TE.DAT"))
        format_string = ["%d"] + ["%.9f" for _ in range(te_array.shape[1]-1)]
        np.savetxt(out_file, te_array, delimiter=",", fmt=format_string)
        log_func("Saved Trip Ends to %s" % str(out_file))
                
                