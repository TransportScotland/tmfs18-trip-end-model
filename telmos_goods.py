# -*- coding: utf-8 -*-
"""

@author: japeach

Conversion of TELMOS2_v2.2 vb scripts
"""

import os

import numpy as np
import pandas as pd

def load_goods_data(goods_file, hgv_output, lgv_output):
    '''
    Loading function for TELMoS goods files
    Splits the data into LGV and HGV parts
    '''
    with open(goods_file, "r") as f:
        data = f.readlines()
    # Discard header
    data = np.asarray([line.split() for line in data if (line.split()[0] == "1" or 
                                      line.split()[0] == "2")],dtype="float64")
        
    hgv_array = pd.DataFrame(data[data[:,0]==1][:,1:])
    lgv_array = pd.DataFrame(data[data[:,0]==2][:,1:])
    #Print to separate files
    pd.concat((hgv_array.loc[:,:1].astype("int16"),hgv_array.loc[:,2]),axis=1).to_csv(
        hgv_output, index=False, header=False)
    pd.concat((lgv_array.loc[:,:1].astype("int16"),lgv_array.loc[:,2]),axis=1).to_csv(
        lgv_output, index=False, header=False)
    
    hgv_array = np.array(hgv_array.set_index([0,1]).unstack(-1))
    lgv_array = np.array(lgv_array.set_index([0,1]).unstack(-1))
    return (hgv_array, lgv_array)

def telmos_goods(delta_root, tmfs_root, tel_year, tel_id, tel_scenario,
                base_year, base_id, base_scenario, is_rebasing_run=True,
                log_func=print):
    # Set this to true if run is rebasing from TMfS07 to TMfS12 or 
    # TMfS12 to TMfs14 => it resets the GV growth to 1.00

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
    hgv_base_array, lgv_base_array = load_goods_data(base_goods_file, 
                                                     base_hgv_file, base_lgv_file)
    
    zone_count = hgv_base_array.shape[0]
    
    # Repeat for tel data
    hgv_tel_array, lgv_tel_array = load_goods_data(tel_goods_file, 
                                                   tel_hgv_file, tel_lgv_file)

    log_func("HGV Count = %s" % str(zone_count))
    
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
        forecast_goods_array[f_key] = (base_goods_array[f_key][:zone_count,:zone_count] * 
                            goods_growth_array[goods_type][:zone_count,:zone_count])
        
        # Sum of base and forecast matrices - Only up to 783 - changed to hgv_count
        # to reflect number of zones
        goods_total["%s_base" % f_key] = np.sum(
                base_goods_array[f_key][:zone_count,:zone_count]) # hgv_count replaces 783
        goods_total["%s_forecast" % f_key] = np.sum(
                forecast_goods_array[f_key][:zone_count,:zone_count]) # hgv_count replaces 783
        
        # Adjust TMfS Forecast matrices
        if is_rebasing_run is True:
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
            new_forecast_array[f_key][:zone_count,:zone_count] = (
                    forecast_goods_array[f_key][:zone_count,:zone_count] * 
                    ((goods_total["%s_base" % f_key] * goods_totals["TEL_%s" % goods_type]) / 
                     (goods_total["%s_forecast" % f_key] * goods_totals["BASE_%s" % goods_type]))
                    )
        # Print these files stacked
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
        np.savetxt(os.path.join(tel_filebase, filename.replace(".DAT","TE.DAT")),
                   te_array, fmt=["%d","%.3f","%.3f"], delimiter=",")
        log_func("Goods TE saved to %s" % str(os.path.join(tel_filebase,
                                                 filename.replace(".DAT","TE.DAT"))))
            
    # Check array sizes are > 250KBytes
    for k, array in new_forecast_array.items():
        if array.nbytes < 250000:
            log_func("Array is incomplete %s" % k)
                    
        