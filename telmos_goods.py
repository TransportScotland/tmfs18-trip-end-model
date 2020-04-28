# -*- coding: utf-8 -*-
"""

@author: japeach

Conversion of TELMOS2_v2.2 vb scripts
"""

import os

import numpy as np
import pandas as pd


def telmos_goods(delta_root, tmfs_root, tel_year, tel_id, tel_scenario,
                base_year, base_id, base_scenario, is_rebasing_run=True,
                do_output=False, debug=True, log_func=print):
    # Set this to true if run is rebasing from TMfS07 to TMfS12 or 
    # TMfS12 to TMfs14 => it resets the GV growth to 1.00
    rebasing_run = is_rebasing_run

    log_func("Processing Goods...")
    
    # # # Inputs # # #
    # sr1
    tel_goods_file = os.path.join(delta_root,  tel_scenario, 
                                  "trfl%s%s.dat" % (tel_year, tel_scenario))
    # sr2
    base_goods_file = os.path.join(delta_root, base_scenario, 
                                  "trfl%s%s.dat" % (base_year, base_scenario))
    
    nrtf_file = os.path.join(tmfs_root, "Factors", "NRTF.DAT")
    # # # # # # # # # # 
    
    # # # Outputs # # # 
    tel_hgv_file = os.path.join(tmfs_root, "Runs", tel_year, "Demand", tel_id,
                                "hgv%s%s.dat" % (tel_year, tel_id))
    tel_lgv_file = os.path.join(tmfs_root, "Runs", tel_year, "Demand", tel_id,
                                "lgv%s%s.dat" % (tel_year, tel_id))
    base_hgv_file = os.path.join(tmfs_root, "Runs", base_year, "Demand", base_id,
                                "hgv%s%s.dat" % (base_year, base_id))
    base_lgv_file = os.path.join(tmfs_root, "Runs", base_year, "Demand", base_id,
                                "lgv%s%s.dat" % (base_year, base_id))
    # # # # # # # # #
    
    
    filenames = ["AMHGV.DAT", "AMLGV.DAT", "IPHGV.DAT", "IPLGV.DAT",
                 "PMHGV.DAT", "PMLGV.DAT"]
    # # # Inputs # # #
    base_filebase = os.path.join(tmfs_root, "Runs", base_year, "Demand",
                                    base_id)
    
    # # # Outputs # # #
    tel_filebase = os.path.join(tmfs_root, "Runs", tel_year, "Demand",
                                    tel_id)
    
    # # # Load base_goods data
    with open(base_goods_file, "r") as f:
        data = f.readlines()
    # Discard header
    data = np.asarray([line.split() for line in data if (line.split()[0] == "1" or 
                                      line.split()[0] == "2")],dtype="float64")

    log_func("Base Goods shape = %s" % str(data.shape))
        
    hgv_base_array = pd.DataFrame(data[data[:,0]==1][:,1:])
    lgv_base_array = pd.DataFrame(data[data[:,0]==2][:,1:])
    #Print to separate files
    if do_output:
        pd.concat((hgv_base_array.loc[:,:1].astype("int16"),hgv_base_array.loc[:,2]),axis=1).to_csv(
            base_hgv_file, index=False, header=False)
        pd.concat((lgv_base_array.loc[:,:1].astype("int16"),lgv_base_array.loc[:,2]),axis=1).to_csv(
            base_lgv_file, index=False, header=False)
        log_func("Base HGV Saved to %s" % str(base_hgv_file))
        log_func("Base LGV Saved to %s" % str(base_lgv_file))
        
    hgv_base_array = np.array(hgv_base_array.set_index([0,1]).unstack(-1))
    lgv_base_array = np.array(lgv_base_array.set_index([0,1]).unstack(-1))
    
    hgv_count = hgv_base_array.shape[0]
    lgv_count = lgv_base_array.shape[0] ## This was an error in TMfS14 - but it is not used
    # # # # # # # # # # # # # # # 
    
    # Repeat for tel data
    with open(tel_goods_file, "r") as f:
        data = f.readlines()
    # Discard header
    data = np.asarray([line.split() for line in data if (line.split()[0] == "1" or 
                                      line.split()[0] == "2")], dtype="float64")
        
    log_func("TEL Goods shape = %s" % str(data.shape))
            
    hgv_tel_array = pd.DataFrame(data[data[:,0]==1][:,1:])
    lgv_tel_array = pd.DataFrame(data[data[:,0]==2][:,1:])
    if do_output:
        pd.concat((hgv_tel_array.loc[:,:1].astype("int16"),
                   hgv_tel_array.loc[:,2]),axis=1).to_csv(
            tel_hgv_file, index=False, header=False)
        pd.concat((lgv_tel_array.loc[:,:1].astype("int16"),
                   lgv_tel_array.loc[:,2]),axis=1).to_csv(
            tel_lgv_file, index=False, header=False)
        log_func("TEL HGV Saved to %s" % str(tel_hgv_file))
        log_func("TEL LGV Saved to %s" % str(tel_lgv_file))
    
    hgv_tel_array = np.array(hgv_tel_array.set_index([0,1]).unstack(-1))
    lgv_tel_array = np.array(lgv_tel_array.set_index([0,1]).unstack(-1))
    
    hgv_count = hgv_tel_array.shape[0]
    hgv_count = lgv_tel_array.shape[0] ## This is an error but does not matter

    log_func("HGV Count = %s" % str(hgv_count))
    
    # # # # # # # # # # # # # # # 
    
    goods_totals = {"TEL_HGV":np.sum(hgv_tel_array),
                    "TEL_LGV":np.sum(lgv_tel_array),
                    "BASE_HGV":np.sum(hgv_base_array),
                    "BASE_LGV":np.sum(lgv_base_array)}
    
    # pad tel arrays to match base shape
    result = np.zeros_like(hgv_base_array)
    result[:hgv_tel_array.shape[0], :hgv_tel_array.shape[1]] = hgv_tel_array
    hgv_tel_array = result
    result = np.zeros_like(lgv_base_array)
    result[:lgv_tel_array.shape[0], :lgv_tel_array.shape[1]] = lgv_tel_array
    lgv_tel_array = result
    
    # Totals are calculated then zeros filled in. 
    hgv_base_array[hgv_base_array == 0] = 1
    lgv_base_array[lgv_base_array == 0] = 1
    hgv_tel_array[hgv_tel_array == 0] = 1
    lgv_tel_array[lgv_tel_array == 0] = 1
    
    goods_growth_array = {"HGV":hgv_tel_array / hgv_base_array,
                          "LGV":lgv_tel_array / lgv_base_array}
    
    # Load NRTF Array
    nrtf_array = pd.read_csv(nrtf_file)
        
    # # # # Read base am/ip/pm hgv/lgv files
    base_goods_array = {}
    forecast_goods_array = {}
    goods_total = {}
    new_forecast_array = {}
    for filename in filenames:
        
        # Keys to access dictionary
        f_key = filename.replace(".DAT","")
        goods_type = f_key[-3:] # HGV or LGV
        
        # Read base values from file
        base_goods_array[f_key] = np.array(pd.read_csv(
                os.path.join(base_filebase, filename), header=None, 
                index_col=[0,1]).unstack(-1))
        
        # Apply growth for forecast 
        forecast_goods_array[f_key] = (base_goods_array[f_key][:hgv_count,:hgv_count] * 
                            goods_growth_array[goods_type][:hgv_count,:hgv_count])
        
        # Sum of base and forecast matrices - Only up to 783 - changed to hgv_count
        # to reflect number of zones
        goods_total["%s_base" % f_key] = np.sum(
                base_goods_array[f_key][:hgv_count,:hgv_count]) # hgv_count replaces 783
        goods_total["%s_forecast" % f_key] = np.sum(
                forecast_goods_array[f_key][:hgv_count,:hgv_count]) # hgv_count replaces 783
        
        # Adjust TMfS Forecast matrices
        if rebasing_run is True:
            new_forecast_array[f_key] = base_goods_array[f_key]
        else:
            nrtf_col = ["LGV","OGV"][["LGV","HGV"].index(goods_type)]
            
            # For 784 - 799 use the following
            new_forecast_array[f_key] = (base_goods_array[f_key] * 
                              (nrtf_array.loc[
                                      nrtf_array.PERIOD==
                                              int(tel_year)+2000][nrtf_col].values[0] / 
                                nrtf_array.loc[
                                        nrtf_array.PERIOD==
                                                int(base_year)+2000][nrtf_col].values[0]))
            # For up to hgv_count use the following
            new_forecast_array[f_key][:hgv_count,:hgv_count] = (
                    forecast_goods_array[f_key][:hgv_count,:hgv_count] * 
                    ((goods_total["%s_base" % f_key] * goods_totals["TEL_%s" % goods_type]) / 
                     (goods_total["%s_forecast" % f_key] * goods_totals["BASE_%s" % goods_type]))
                    )
        # Print these files as stack
        if do_output:
            df = pd.DataFrame(new_forecast_array[f_key]).stack().reset_index()
            df.loc[:,:"level_1"] = df.loc[:,:"level_1"] + 1
            df.to_csv(os.path.join(tel_filebase, filename), index=False, 
                      header=False, float_format="%.3f")
            log_func("Goods file saved to %s" % str(os.path.join(tel_filebase, filename)))
            
        # Create Trip End Files
        te_array = np.stack((np.arange(new_forecast_array[f_key].shape[0]) + 1,
                             new_forecast_array[f_key].sum(axis=1),
                             new_forecast_array[f_key].sum(axis=0)), axis=1)
        if te_array.nbytes < 500:
            log_func("Trip End Array is incomplete")
        if do_output:
            np.savetxt(os.path.join(tel_filebase, filename.replace(".DAT","TE.DAT")),
                       te_array, fmt=["%d","%.3f","%.3f"], delimiter=",")
            log_func("Goods TE saved to %s" % str(os.path.join(tel_filebase,
                                                     filename.replace(".DAT","TE.DAT"))))
            
    # Check against supplied files
    if debug is True:
        log_func("\nChecking against previous files in directory 'Received Data'\n")
        files = ["Base HGV", "Base LGV", "TEL HGV", "TEL LGV"] + [f for f in 
                filenames] + [f.replace(".DAT", "TE.DAT") for f in filenames]
        diffs = {k:0 for k in files}
        produced_path = os.path.join(tmfs_root, "Runs", tel_year, 
                                        "Demand", tel_id)
        produced_files = [base_hgv_file, base_lgv_file, tel_hgv_file, 
                          tel_lgv_file] + [os.path.join(tel_filebase, filename)
                          for filename in filenames] + [os.path.join(
                                  tel_filebase, filename.replace(
                                          ".DAT", "TE.DAT")) for filename in filenames]
                          
        check_path_out = os.path.join("Received Data", "Output", "37DSL_out")
        check_path_in = os.path.join("Received Data", "Input", "Runs", "14", 
                                     "Demand", "AAE")
        check_files = [os.path.join(check_path_in, "hgv14AAE.dat"),
                       os.path.join(check_path_in, "lgv14AAE.dat"),
                       os.path.join(check_path_out, "hgv37DSL.dat"),
                       os.path.join(check_path_out, "lgv37DSL.dat"),
                       ] + [os.path.join(check_path_out, filename) 
                       for filename in filenames
                       ] + [os.path.join(check_path_out, 
                       filename.replace(".DAT", "TE.DAT")) for filename in filenames]
                       
        for name, p, c in zip(files, produced_files, check_files):
            skiprows = 0
            p_total = np.loadtxt(p, skiprows=skiprows, delimiter=",").sum()
            c_total = np.loadtxt(c, skiprows=skiprows, delimiter=",").sum()
            diffs[name] = (p_total - c_total) / c_total
        return diffs
            
    # Check array sizes are > 250KBytes
    for k, array in new_forecast_array.items():
        if array.nbytes < 250000:
            log_func("Array is incomplete %s" % k)
                    
        
        
        
        
        
        
        
        
        
        
        
        
        
        
