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
                base_year, base_id, base_scenario, do_output=False,
                debug=True, log_func=print):
    log_func("Processing Addins...")
    
    #low_zones = 783 ;; This is now increased to 787 to represent the internal 
    #                ;; Cannot be done without hardcoding low_zones number if separate
    #                ;; to the rest of the model
    low_zones = 787
    
    # Following store the output file names and paths for debugging purposes
    file_names = []
    produced_files = []
    check_files = []
    
    purposes = ["PT", "COM", "EMP", "OTH"]
    periods = ["AM", "IP", "PM"]
    filenames = ["%s%s.DAT" % (period, purpose) for period in periods 
                 for purpose in purposes]
    
    nrtf_file = os.path.join(tmfs_root, "Factors", "NRTF.DAT")
    # Load NRTF Array
    nrtf_array = pd.read_csv(nrtf_file)
    
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
        if "PT" not in f_key:
            # Different rules if below 'low_zones'
            new_addin_array[f_key] = (addin_array[f_key] * 
                   nrtf_array.loc[nrtf_array.PERIOD==int(tel_year)+2000]["CARS"].values[0] / 
                   nrtf_array.loc[nrtf_array.PERIOD==int(base_year)+2000]["CARS"].values[0])
            new_addin_array[f_key][:low_zones,:low_zones] = (
                    addin_array[f_key][:low_zones,:low_zones])
            
            # Print the matrix as a column
            if do_output:
                out_file = os.path.join(
                        tmfs_root, "Runs", tel_year, "Demand", tel_id, filename)
                matrix_to_odfile(new_addin_array[f_key].round(3), out_file)
                log_func("Saved matrix to %s" % str(out_file))
                produced_files.append(out_file)
                file_names.append(filename)
            
        else:
            # Loop through the 3 pt matrices and apply psv factor from nrtf array
            new_pt_arrays = []
            for i in range(len(addin_array[f_key])):
                new_pt_arrays.append(addin_array[f_key][i] * 
                         nrtf_array.loc[nrtf_array.PERIOD==int(tel_year)+2000]["PSV"].values[0] / 
                         nrtf_array.loc[nrtf_array.PERIOD==int(base_year)+2000]["PSV"].values[0])
                new_pt_arrays[i][:low_zones,:low_zones] = (
                        addin_array[f_key][i][:low_zones,:low_zones])
            new_addin_array[f_key] = new_pt_arrays
            
            # Print the matrices as columns
            if do_output:
                out_file = os.path.join(tmfs_root, "Runs", tel_year, 
                                               "Demand", tel_id, filename)
                matrix_to_odfile([x.round(3) for x in new_addin_array[f_key]], 
                                  out_file, num_columns=3)
                log_func("Saved matrix as %s" % str(out_file))
                produced_files.append(out_file)
                file_names.append(filename)
                
        # Create Trip End Files
        if "PT" not in f_key:
            te_array = np.stack((np.arange(new_addin_array[f_key].shape[0]) + 1,
                                 new_addin_array[f_key].sum(axis=1),
                                 new_addin_array[f_key].sum(axis=0)), axis=1)
        else:
            # For PT, format is:
            #   i, j, o_1, o_2, o_3, d_1, d_2, d_3
            te_array = np.stack((np.arange(new_addin_array[f_key][0].shape[0]) + 1,
                                 new_addin_array[f_key][0].sum(axis=1),
                                 new_addin_array[f_key][1].sum(axis=1),
                                 new_addin_array[f_key][2].sum(axis=1),
                                 new_addin_array[f_key][0].sum(axis=0),
                                 new_addin_array[f_key][1].sum(axis=0),
                                 new_addin_array[f_key][2].sum(axis=0)), axis=1)
            
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
            
        if do_output:
            out_file = os.path.join(tmfs_root, "Runs", tel_year, "Demand",
                                    tel_id, filename.replace(".DAT", "TE.DAT"))
            format_string = ["%d"] + ["%.3f" for x in range(te_array.shape[1]-1)]
            np.savetxt(out_file, te_array, delimiter=",", fmt=format_string)
            log_func("Saved Trip Ends to %s" % str(out_file))
            produced_files.append(out_file)
            file_names.append(filename.replace(".DAT", "TE.DAT"))
            
    # Check against supplied files
    if debug is True:
        log_func("\nChecking against previous files in directory 'Received Data'\n")
        diffs = {k:0 for k in file_names}
        check_path = os.path.join("Received Data", "Output", "37DSL_out")
        check_files = [os.path.join(check_path, f) for f in file_names]
        for name, p, c in zip(file_names, produced_files, check_files):
            skiprows = 0
            p_total = np.loadtxt(p, skiprows=skiprows, delimiter=",").sum()
            c_total = np.loadtxt(c, skiprows=skiprows, delimiter=",").sum()
            diffs[name] = (p_total - c_total) / c_total
        return diffs
                
                
                
                
                
                