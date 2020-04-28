# -*- coding: utf-8 -*-
"""

@author: japeach

Conversion of TELMOS2_v2.2 vb scripts
"""

from itertools import product
import os

import numpy as np
import pandas as pd

from telmos_goods import telmos_goods
from telmos_addins import telmos_addins


def telmos_main(delta_root, tmfs_root, tel_year, tel_id, tel_scenario,
                base_year, base_id, base_scenario, is_rebasing_run=True,
                do_output=False, debug=True, print_func=print,
                just_pivots=False):
    '''
    This is a conversion of the TMfS14 Visual Basic application 
    '''
    
    print = print_func
    
    rebasing_run = is_rebasing_run # May need to be Variable
    
    # Read in the trip rate matrices into multi-dim array
    factors_base = os.path.join(tmfs_root, "Factors")
    purposes = ["HBW", "HBO", "HBE", "HBS"]
    modes = ["Car", "PT"]
    periods = ["AM", "IP", "PM"]
    if just_pivots is True:
        periods.append("OP")
    suffixes = range(3, 9)
    
    sr_array = []
    all_names = []
    for suffix in suffixes:
        data = []
        names = []
        for period, purpose, mode in product(periods, purposes, modes):
            file_name = "%s_%s_%s_%s.txt" % (purpose, mode, period, suffix)
            file = os.path.join(factors_base, file_name)
            try:
                data.append(np.loadtxt(file))
                names.append(file_name)
            except FileNotFoundError as f:
                # If any file can not be found - abort
                print("Could not find file %s\nAborting" % f)
                return
        sr_array.append(data)
        all_names.append(names)
    sr_array = np.asarray(sr_array)
    
    # Load in the student factors and attraction factors separately
    filenames = ["Student Factors.txt", "Attraction Factors.txt"]
    student_factors = np.loadtxt(os.path.join(factors_base, filenames[0]))
    attraction_factors = np.loadtxt(os.path.join(factors_base, filenames[1]))
    
    print("Loaded SR Factors with shape: %s" % str(sr_array.shape)) # old shape was (24, 6, 7, 10)
    print("Loaded Student Factors with shape: %s" % str(student_factors.shape))
    print("Loaded Attraction Factors with shape: %s" % str(attraction_factors.shape))
    
    # Read in Non-Factor files
    
    tel_tmfs_file = os.path.join(delta_root, tel_scenario, 
                                 "tmfs%s%s.csv" % (tel_year, tel_scenario.lower()))
    tel_tav_file = os.path.join(delta_root, tel_scenario, 
                                 "tav_%s%s.csv" % (tel_year, tel_scenario.lower()))
    base_tmfs_file = os.path.join(tmfs_root, "Runs", base_year, "Demand",
                                  base_id, "tmfs%s_%s.csv" % (base_year, base_id))
    base_tav_file = os.path.join(tmfs_root, "Runs", base_year, "Demand",
                                  base_id, "tav_%s_%s.csv" % (base_year, base_id))
    
    tav_array = np.loadtxt(tel_tav_file, skiprows=1, delimiter=",")
    count_tav = tav_array.shape[0]
    
    tmfs_base_array = np.loadtxt(base_tmfs_file, skiprows=1, delimiter=",")
    count_i = tmfs_base_array.shape[0]
    
    tav_base_array = np.loadtxt(base_tav_file, skiprows=1, delimiter=",")
    
    tmfs_array = np.loadtxt(tel_tmfs_file, skiprows=1, delimiter=",",
                            usecols=range(2,11))
    tmfs_array = np.concatenate((np.zeros_like(tmfs_array[:,[0,1]]), tmfs_array), axis=1)
    # Previous version swaps columns 4 and 5 to be in line with the tmfs07 version expects
    tmfs_array[:,4], tmfs_array[:,5] = tmfs_array[:,5], tmfs_array[:,4].copy()
    count_tmfs = tmfs_array.shape[0]
    
    print("TAV Count: %d" % count_tav)
    print("I Count: %d" % count_i)
    print("TMFS Count: %d" % count_tmfs)

    # # # # # # # # # # # # # # # #
    # Put income segregation here #
    # # # # # # # # # # # # # # # #

    # Rearrange and account for students
    tmfs_adj_array = np.copy(tmfs_array)
    tmfs_adj_array[:,:3] = tmfs_adj_array[:,2:5]
    tmfs_adj_array[:,3] = tmfs_adj_array[:,7] * student_factors[0]
    tmfs_adj_array[:,4] = tmfs_adj_array[:,8] * student_factors[1]
    tmfs_adj_array[:,7] = tmfs_adj_array[:,7] * (1 - student_factors[0])
    tmfs_adj_array[:,8] = tmfs_adj_array[:,8] * (1 - student_factors[1])

    print("TAV Base Array shape = %s" % str(tav_base_array.shape))
    print("TMFS Array shape = %s" % str(tmfs_array.shape))
    print("TMFS Adj Array shape = %s" % str(tmfs_adj_array.shape))

    
    # Attraction Factors
    # Apply various attraction factors to the tav array
    attr_file = os.path.join(tmfs_root, "Runs", tel_year, "Demand", tel_id,
                             "tav_%s_%s.csv" % (tel_year, tel_id))

    attr_factors_array = np.zeros((count_tav, 4),dtype="float32")
    attr_factors_array[:,0] = tav_array[:,2] * attraction_factors[0, 0]
    attr_factors_array[:,1] = tav_array[:,[1,3,4,5,6,7,8]].sum(axis=1) * attraction_factors[2,1]
    attr_factors_array[:,2] = (tav_array[:,[4,8,1,3]] * attraction_factors[[6,7,1,12],[3,4,8,9]]).sum(axis=1)
    attr_factors_array[:,3] = tav_array[:,7] * attraction_factors[2,2]
    # Fill zeros with ones
    attr_factors_array[attr_factors_array == 0.0] = 1.0

    if do_output:
        np.savetxt(attr_file, attr_factors_array.round(3), delimiter=",",
                header="HW,HE,HO,HS", fmt="%.3f", comments="")
        print("Attraction Factors saved to %s" % str(attr_file))

    # # # # # # # # # # # #
    # Attraction Growth Factors
    if just_pivots is False:
        attr_growth_array = attr_factors_array / tav_base_array
        # Replace Infinite values with 1
        attr_growth_array[attr_growth_array == np.inf] = 1.0

    # # # # # # # # # # # #
    # Production Factors
    area_corres_file = os.path.join(tmfs_root, "Factors", "AreaCorrespondence.csv")
    area_corres_array = np.loadtxt(area_corres_file, skiprows=1, delimiter=",",
                                   usecols=2, dtype="int8")
    # 
    area_corres_array = np.repeat(area_corres_array, 8)
    print("Area Correspondence shape = %s" % str(area_corres_array.shape))
    
    check_file = os.path.join(tmfs_root, "Runs", tel_year,
                              "Demand", tel_id, "check2.csv")
    sr_prod_array = np.zeros((24, count_tmfs, 11))
    if just_pivots is True:
        sr_prod_array = np.zeros((32, count_tmfs, 11))

        
    with open(check_file, "w", newline="") as file:
        trr = 0
        for k in range(sr_prod_array.shape[0]):
            for j in range(sr_prod_array.shape[2]):
                for i in range(sr_prod_array.shape[1]-1):
                    sr_prod_array[k, i, j] = (tmfs_adj_array[i, j] * 
                                 sr_array[area_corres_array[i]-3, k, trr, j])
                    trr += 1
                    if trr == 8:
                        trr = 0
                    file.write(str(sr_prod_array[k,i,j]))
                    file.write("\n")
    

    print("SR Product array %s" % str(sr_prod_array.shape))
    prod_factor_array = np.zeros_like(tmfs_base_array)
    
    # Just Pivots is a debug option to output an extended version of the pivoting files
    # Originally outputs just 64 columns - 2 periods * 4 Purposes * 2 Modes * 4 Household types
    column_width = 2 * 4 * 2 * 4
    if just_pivots is True:
        # If just calculating the pivoting tables output all the possible time peeriods
        # - 4 Periods * 4 Purposes * 2 Modes * 4 Household types
        column_width = 4 * 4 * 2 * 4
        prod_factor_array = np.zeros(
                (tmfs_base_array.shape[0], tmfs_base_array.shape[1] + 
                 int(column_width / 2)))
        
    # FOR OUTPUTTING WITH DIFFERENT NUMBER OF ZONES
    """if just_pivots is True:
        # If just calculating the pivoting tables output all the possible time peeriods
        # - 4 Periods * 4 Purposes * 2 Modes * 4 Household types
        column_width = 4 * 4 * 2 * 4
        prod_factor_array = np.zeros(
                (tmfs_base_array.shape[0]+4, tmfs_base_array.shape[1] + 
                 int(column_width / 2)))"""
        
    # aggregates the household types into C0, C11, C12, C2
    for i in range(count_tav):
        ca = 0
        cb = 1
        cc = 2
        cd = 3
        for j in range(column_width):
            v = 0
            for b in range(11):
                if j == ca:
                    v += sr_prod_array[int((ca+4)/4)-1,0+(i*8),b] + sr_prod_array[int((ca+4)/4)-1,2+(i*8),b] + sr_prod_array[int((ca+4)/4)-1,5+(i*8),b]
                if j == cb:
                    v += sr_prod_array[int((cb+3)/4)-1,1+(i*8),b]
                if j == cc:
                    v += sr_prod_array[int((cc+2)/4)-1,3+(i*8),b] + sr_prod_array[int((cc+2)/4)-1,6+(i*8),b]
                if j == cd:
                    v += sr_prod_array[int((cd+1)/4)-1,4+(i*8),b] + sr_prod_array[int((cd+1)/4)-1,7+(i*8),b]

            if j == ca:
                ca += 4
            if j == cb:
                cb += 4
            if j == cc:
                cc += 4
            if j == cd:
                cd += 4

            prod_factor_array[i, j] = v
                
    prod_factor_array[prod_factor_array == 0] = 1
    prod_factor_file = os.path.join(tmfs_root, "Runs", tel_year, "Demand", tel_id, "tmfs%s_%s.csv" % (tel_year, tel_id))
    
    if do_output:
        file_header = ("WAC C0,WAC C11,WAC C12,WAC C2,WAP C0,WAP C11,WAP C12,"
                       "WAP C2,OAC C0,OAC C11,OAC C12,OAC C2,OAP C0,OAP C11,OAP C12,OAP C2,"
                       "EAC C0,EAC C11,EAC C12,EAC C2,EAP C0,EAP C11,EAP C12,EAP C2,SAC C0,"
                       "SAC C11,SAC C12,SAC C2,SAP C0,SAP C11,SAP C12,SAP C2,WIC C0,WIC C11,"
                       "WIC C12,WIC C2,WIP C0,WIP C11,WIP C12,WIP C2,OIC C0,OIC C11,OIC C12,"
                       "OIC C2,OIP C0,OIP C11,OIP C12,OIP C2,EIC C0,EIC C11,EIC C12,EIC C2,"
                       "EIP C0,EIP C11,EIP C12,EIP C2,SIC C0,SIC C11,SIC C12,SIC C2,SIP C0,"
                       "SIP C11,SIP C12,SIP C2")
        if just_pivots is True:
            file_header += (",WPC C0,WPC C11,WPC C12,WPC C2,WPP C0,WPP C11,"
                       "WPP C12,WPP C2,OPC C0,OPC C11,OPC C12,OPC C2,OPP C0,OPP C11,OPP C12,"
                       "OPP C2,EPC C0,EPC C11,EPC C12,EPC C2,EPP C0,EPP C11,EPP C12,EPP C2,"
                       "SPC C0,SPC C11,SPC C12,SPC C2,SPP C0,SPP C11,SPP C12,SPP C2"
                       ",WOC C0,WOC C11,WOC C12,WOC C2,WOP C0,WOP C11,"
                       "WOP C12,WOP C2,OOC C0,OOC C11,OOC C12,OOC C2,OOP C0,OOP C11,OOP C12,"
                       "OOP C2,EOC C0,EOC C11,EOC C12,EOC C2,EOP C0,EOP C11,EOP C12,EOP C2,"
                       "SOC C0,SOC C11,SOC C12,SOC C2,SOP C0,SOP C11,SOP C12,SOP C2")
            np.savetxt(prod_factor_file, prod_factor_array.round(3), delimiter=",",
                       header=file_header, fmt="%.3f", comments="")
            print("Completed calculating pivoting tables")
            print("Finished")
            return

        np.savetxt(prod_factor_file, prod_factor_array.round(3), delimiter=",",
                    header=file_header, fmt="%.3f", comments="")
        print("Production Factors saved to %s" % str(prod_factor_file))
        
    
    ## # # # # # # # # #
    # Production Growth Factors
    prod_growth_array = prod_factor_array / tmfs_base_array
    prod_growth_array[prod_growth_array == np.inf] = 1.0
    print("Production Growth Array shape = %s" % str(prod_growth_array.shape))

    prefixes = ["AM","IP"]
    types = ["HWZ_A1", "HOZ_A1_ALL", "HEZ_A1_ALL", "HSZ_A1"]
    tod_files = ["%s_%s.TOD" % (prefix, t) for prefix in prefixes for t in types] + ["PM_HSZ_A1.TOD"]
    cte_files = [("%s_%s.CTE" % (prefix, t)).replace("A1","D0") for prefix in prefixes for t in types] + ["PM_HSZ_D0.CTE"]
    tod_data = []
    cte_data = []
    for t_file, c_file in zip(tod_files, cte_files):
        # TMfS14 had a long-distance module that required some CTE/TOD files to have
        # _All appended to the end. This can now be removed if needed.
        if (os.path.exists(os.path.join(tmfs_root, "Runs", base_year,
                                                "Demand", base_id, t_file)) and
               os.path.exists(os.path.join(tmfs_root, "Runs", base_year,
                        "Demand", base_id, t_file))):
            t_file_name = t_file
            c_file_name = c_file
        else:
            t_file_name = t_file.replace("_ALL","")
            c_file_name = c_file.replace("_ALL","")
        tod_data.append(np.loadtxt(os.path.join(tmfs_root, "Runs", base_year,
                                                "Demand", base_id, t_file_name),
                                   delimiter=","))
        cte_data.append(np.loadtxt(os.path.join(tmfs_root, "Runs", base_year,
                                                "Demand", base_id, c_file_name),
                                   delimiter=","))
    tod_data = np.asarray(tod_data)
    cte_data = np.asarray(cte_data)
    print("TOD Data Shape = %s" % str(tod_data.shape))
    print("CTE Data Shape = %s" % str(cte_data.shape))

    airport_growth = np.ones(count_tav,dtype="float")
    if rebasing_run is False:
        # Airport indices are as follows (zones are indices + 1):
        #   708 = Edinburgh Airport
        #   709 = Prestwick Airport
        #   710 = Glasgow Airport
        #   711 = Aberdeen Airport
        
        #factors = pd.DataFrame([[708,1.05588],[709,1.0],[710,1.02371],[711,1.01213]])
        
        # Factors updated as of TMfS 2018
        #   708 = 4.97% Edinburgh 
        #   709 = 7.6%  Prestwick
        #   710 = 3.33% Glasgow
        #   711 = 1.86% Aberdeen
        
        ####
        #   Previous method for airport growth < TMfS18 (constant value per annum)
        #factors = pd.DataFrame([[708,1.0497],[709,1.076],[710,1.0333],[711,1.0186]])
        #airport_growth[factors[0]] = factors[1] ** (int(tel_year) - int(base_year))
        
        ####
        #   New method for airport growth >= TMfS18 (growth varies according to DfT 2017 aviation forecast)
        # now reads in a file from "Factors" that contains the expected growth 
        # from 2017
        factors = pd.read_csv(os.path.join(tmfs_root, "Factors", 
                                           "airport_factors.csv"), index_col="Year")
        factors = factors.loc[int(tel_year) + 2000]/factors.loc[int(base_year) + 2000]
        airport_growth[factors.index.astype("int")] = factors.values

    sw_array = np.zeros_like(tod_data, dtype="float")
    
    attr_growth_idxs = [0,2,1,3,0,2,1,3,3]
    for j in range(sw_array.shape[0] - 1):
        sw_array[j,:,1:4] = ((cte_data[j,:,1:4] * prod_growth_array[:,(1+8*j):(4+8*j)]) +
                            (cte_data[j,:,4:7] * prod_growth_array[:,(5+8*j):(8+8*j)])) * airport_growth[:,None]
        sw_array[j,:,4] = tod_data[j,:,4] * prod_growth_array[:,(4+8*j)] * airport_growth
        sw_array[j,:,5] = tod_data[j,:,5] * attr_growth_array[:,attr_growth_idxs[j]] * airport_growth

    sw_array[8,:,1:4] = ((cte_data[8,:,1:4] * prod_growth_array[:,(1+8*7):(4+8*7)]) +
                            (cte_data[8,:,4:7] * prod_growth_array[:,(5+8*7):(8+8*7)])) * airport_growth[:,None]
    sw_array[8,:,4] = tod_data[8,:,4] * prod_growth_array[:,(4+8*7)] * airport_growth
    sw_array[8,:,5] = tod_data[8,:,5] * attr_growth_array[:,attr_growth_idxs[7]] * airport_growth

    sw_prod = {}
    sw_attr = {}
    sw_prod["1"] = sw_array[0,:,1:5].sum()
    sw_prod["5"] = sw_array[4,:,1:5].sum()
    sw_prod["4"] = sw_array[3,:,1:5].sum()
    sw_prod["14"] = sw_array[7,:,1:5].sum()
    sw_prod["17"] = sw_array[8,:,1:5].sum()

    sw_attr["1"] = sw_array[0,:,5].sum()
    sw_attr["5"] = sw_array[4,:,5].sum()
    sw_attr["4"] = sw_array[3,:,5].sum()
    sw_attr["14"] = sw_array[7,:,5].sum()
    sw_attr["17"] = sw_array[8,:,5].sum()

    sw_array[0,:,5] *= (sw_prod["1"] / sw_attr["1"])
    sw_array[4,:,5] *= (sw_prod["5"] / sw_attr["5"])
    sw_array[3,:,5] *= (sw_prod["4"] / sw_attr["4"])
    sw_array[7,:,5] *= (sw_prod["14"] / sw_attr["14"])
    sw_array[8,:,5] *= (sw_prod["17"] / sw_attr["17"])

    print("SW Array shape = %s" % str(sw_array.shape))

    # Print the TOD files - index +1: array(round(3))
    # All the zones are internal, so are labelled continuously - 1->787 as of tmfs18
    if do_output:
        for i, t_file in zip(range(sw_array.shape[0]), tod_files):
            path = os.path.join(tmfs_root, "Runs", tel_year, "Demand", tel_id, t_file.replace("_ALL", ""))
            np.savetxt(path, np.concatenate(
                    (np.arange(sw_array[i].shape[0])[:,None]+1, sw_array[i][:,1:]),axis=1),
                        delimiter=", ", fmt=["%d"]+["%.3f" for x in range(sw_array[i].shape[1]-1)])
            print("TOD File saved to %s" % str(path))

    sw_cte_array = np.zeros_like(cte_data, dtype="float")
    prod_col_idxs = np.array([1,2,3,5,6,7,4])
    attr_growth_idxs = [None, 2, 1, None, None, 2, 1, None, None]
    print("SW CTE Array shape = %s" % str(sw_cte_array.shape))
    for j in range(sw_cte_array.shape[0]):
        if j < 8:
            sw_cte_array[j,:,1:8] = (cte_data[j,:,1:8] * 
                        prod_growth_array[:,prod_col_idxs+(j*8)] *
                        airport_growth[:,None])
        else:
            sw_cte_array[j,:,1:8] = (cte_data[j,:,1:8] * 
                        prod_growth_array[:,prod_col_idxs+((j-1)*8)] *
                        airport_growth[:,None])
        # These columns do the following
        if j in [0,3,4,7,8]:
            sw_cte_array[j,:,8] = sw_array[j,:,5]
        # Otherwise...
        else:
            #print("CTE Data = : ",cte_data[j,:,8].shape)
            #print("Attr Growth = : ", attr_growth_array[:,attr_growth_idxs[j]].shape)
            #print("Airport_growth = :", airport_growth.shape)
            sw_cte_array[j,:,8] = (cte_data[j,:,8] * 
                        attr_growth_array[:,attr_growth_idxs[j]] * 
                        airport_growth)
            
    # Print the CTE files - index+1: array(round(5))
    # All the zones are internal, so are labelled continuously - 1->787 as of tmfs18
    if do_output:
        for i, c_file in zip(range(sw_array.shape[0]), cte_files):
            path = os.path.join(tmfs_root, "Runs", tel_year, "Demand", tel_id, c_file.replace("_ALL", ""))
            np.savetxt(path, np.concatenate(
                    (np.arange(sw_cte_array[i].shape[0])[:,None]+1, sw_cte_array[i][:,1:]),axis=1),
                        delimiter=", ", fmt=["%d"]+["%.5f" for x in range(sw_cte_array[i].shape[1]-1)])
            print("CTE File saved to %s" % str(path))
    
    # Check that each array CTE and TOD is > 15kBytes
    for i,test_array in enumerate(sw_array):
        if test_array.nbytes < 15000:
            print("TOD Array is incomplete: %d" % i)
    for i,test_array in enumerate(sw_cte_array):
        if test_array.nbytes < 15000:
            print("CTE Array is incomplete: %d" % i)
            
            
    # Check against supplied files
    if debug is True:
        print("\nChecking against previous files in directory 'Received Data'\n")
        files = ["Attraction", "Production"] + [file for file in tod_files] + [
                file for file in cte_files]
        diffs = {k:0 for k in files}
        produced_path = os.path.join(tmfs_root, "Runs", tel_year, 
                                        "Demand", tel_id)
        produced_files = [attr_file, prod_factor_file] + [os.path.join(produced_path, 
                         file) for file in tod_files] + [os.path.join(produced_path,
                             file) for file in cte_files]
        check_path = os.path.join("Received Data", "Output", "37DSL_out")
        check_files = ["tav_37_DSL.csv", "tmfs37_DSL.csv"] + [
                file for file in tod_files] + [file for file in cte_files]
        check_files = [os.path.join(check_path, x) for x in check_files]
        for name, p, c in zip(files, produced_files, check_files):
            if name == "Attraction" or name == "Production":
                # Skip header
                skiprows = 1
            else:
                skiprows = 0
            p_total = np.loadtxt(p, skiprows=skiprows, delimiter=",").sum()
            c_total = np.loadtxt(c, skiprows=skiprows, delimiter=",").sum()
            diffs[name] = (p_total - c_total) / c_total
        return diffs
            
            
    ###############################################
    ################## End of Main ################
    ###############################################
        
    
if __name__ == "__main__":
    
    telmos_main("Data/Input/DELTA", "Data/Input",
                "14", "AAE", "AE", "14", "AAE", "AE")
    telmos_goods("Data/Input/DELTA", "Data/Input",
                "14", "AAE", "AE", "14", "AAE", "AE")
    telmos_addins("Data/Input/DELTA", "Data/Input",
                "14", "AAE", "AE", "14", "AAE", "AE")
