# -*- coding: utf-8 -*-
"""

@author: japeach

Conversion of TELMOS2_v2.2 vb scripts
"""

from itertools import product
import os

import numpy as np
import pandas as pd

def read_trip_rates(factors_dir, just_pivots):
    '''
    Loads the production trip rate files into
    '''
    purposes = ["HBW", "HBO", "HBE", "HBS"]
    modes = ["Car", "PT"]
    periods = ["AM", "IP", "PM"]
    if just_pivots is True:
        periods.append("OP")
    suffixes = range(3, 9)
    
    sr_array = []
    for suffix in suffixes:
        data = []
        names = []
        for period, purpose, mode in product(periods, purposes, modes):
            file_name = "%s_%s_%s_%s.txt" % (purpose, mode, period, suffix)
            factor_file = os.path.join(factors_dir, file_name)
            data.append(np.loadtxt(factor_file))
            names.append(file_name)
        sr_array.append(data)
    return np.asarray(sr_array)

def load_cte_tod_files(tod_files, cte_files, file_base):
    tod_data = []
    cte_data = []
    for t_file, c_file in zip(tod_files, cte_files):
        # TMfS14 had a long-distance module that required some CTE/TOD files to have
        # _All appended to the end. This can now be removed if needed.
        if (os.path.exists(os.path.join(file_base, t_file)) and
               os.path.exists(os.path.join(file_base, c_file))):
            t_file_name = t_file
            c_file_name = c_file
        else:
            t_file_name = t_file.replace("_ALL","")
            c_file_name = c_file.replace("_ALL","")
        tod_data.append(np.loadtxt(os.path.join(file_base, t_file_name),
                                   delimiter=","))
        cte_data.append(np.loadtxt(os.path.join(file_base, c_file_name),
                                   delimiter=","))
    return (np.asarray(tod_data), np.asarray(cte_data))

def create_attraction_pivot(planning_data, attraction_trip_rates):
    ''' 
    Multiplies the planning data and the attraction trip rates
    '''
    # Columns are: Work, Employment, Other, Education
    attr_factors_array = np.ones((planning_data.shape[0], 4),dtype="float32")
    attr_factors_array[:,0] = planning_data[:,2] * attraction_trip_rates[0, 0]
    attr_factors_array[:,1] = planning_data[:,[1,3,4,5,6,7,8]].sum(axis=1) * attraction_trip_rates[2,1]
    attr_factors_array[:,2] = (planning_data[:,[4,8,1,3]] * 
                      attraction_trip_rates[[6,7,1,12],[3,4,8,9]]).sum(axis=1)
    attr_factors_array[:,3] = planning_data[:,7] * attraction_trip_rates[2,2]
    return attr_factors_array

def create_production_pivot(planning_data, production_trip_rates, area_correspondence,
                            check_file, count_tav, output_shape, just_pivots):
    ''' 
    Multiplies the planning data and the production trip rates
    
    planning_data : adjusted planning data (tmfsxxxx.csv)
    production_trip_rates : array of all production trip rates (p_trip_rate_array)
    area_correspondence : array containing urban/rural classification of zones 
    check_file : output path for check2.csv file
    count_tav : number of internal zones
    output_shape : shape of pivot file (same as base pivot file)
    just_pivots : bool : if just the pivots should be output (false)
    '''
    sr_prod_array = np.zeros((24, planning_data.shape[0], 11))
    if just_pivots is True:
        sr_prod_array = np.zeros((32, planning_data.shape[0], 11))
        
    with open(check_file, "w", newline="") as check:
        trr = 0
        for k in range(sr_prod_array.shape[0]):
            for j in range(sr_prod_array.shape[2]):
                for i in range(sr_prod_array.shape[1]-1):
                    sr_prod_array[k, i, j] = (planning_data[i, j] * 
                                 production_trip_rates[area_correspondence[i]-3, k, trr, j])
                    trr += 1
                    if trr == 8:
                        trr = 0
                    check.write(str(sr_prod_array[k,i,j]))
                    check.write("\n")
                    
    prod_factor_array = np.ones(output_shape)
    
    # Just Pivots is a debug option to output an extended version of the pivoting files
    # Originally outputs just 64 columns - 2 periods * 4 Purposes * 2 Modes * 4 Household types
    column_width = 2 * 4 * 2 * 4
    if just_pivots is True:
        # If just calculating the pivoting tables output all the possible time periods
        # - 4 Periods * 4 Purposes * 2 Modes * 4 Household types
        column_width = 4 * 4 * 2 * 4
        prod_factor_array = np.zeros(
                (output_shape[0], output_shape[1] + 
                 int(column_width / 2)))
        
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
                    v += (sr_prod_array[int((ca+4)/4)-1,0+(i*8),b] + 
                                        sr_prod_array[int((ca+4)/4)-1,2+(i*8),b] + 
                                        sr_prod_array[int((ca+4)/4)-1,5+(i*8),b])
                if j == cb:
                    v += sr_prod_array[int((cb+3)/4)-1,1+(i*8),b]
                if j == cc:
                    v += (sr_prod_array[int((cc+2)/4)-1,3+(i*8),b] + 
                                        sr_prod_array[int((cc+2)/4)-1,6+(i*8),b])
                if j == cd:
                    v += (sr_prod_array[int((cd+1)/4)-1,4+(i*8),b] + 
                                        sr_prod_array[int((cd+1)/4)-1,7+(i*8),b])

            if j == ca:
                ca += 4
            if j == cb:
                cb += 4
            if j == cc:
                cc += 4
            if j == cd:
                cd += 4

            prod_factor_array[i, j] = v
    
    return prod_factor_array

def apply_pivot_files(tod_data, cte_data, 
                      production_growth, attraction_growth,
                      airport_growth):
    '''
    Applies growth to the base cte and tod files
    
    '''
    sw_array = np.zeros_like(tod_data, dtype="float")
    
    attr_growth_idxs = [0,2,1,3,0,2,1,3,3]
    for j in range(sw_array.shape[0] - 1):
        sw_array[j,:,1:4] = ((cte_data[j,:,1:4] * production_growth[:,(1+8*j):(4+8*j)]) +
                            (cte_data[j,:,4:7] * production_growth[:,(5+8*j):(8+8*j)])) * airport_growth[:,None]
        sw_array[j,:,4] = tod_data[j,:,4] * production_growth[:,(4+8*j)] * airport_growth
        sw_array[j,:,5] = tod_data[j,:,5] * attraction_growth[:,attr_growth_idxs[j]] * airport_growth

    sw_array[8,:,1:4] = ((cte_data[8,:,1:4] * production_growth[:,(1+8*7):(4+8*7)]) +
                            (cte_data[8,:,4:7] * production_growth[:,(5+8*7):(8+8*7)])) * airport_growth[:,None]
    sw_array[8,:,4] = tod_data[8,:,4] * production_growth[:,(4+8*7)] * airport_growth
    sw_array[8,:,5] = tod_data[8,:,5] * attraction_growth[:,attr_growth_idxs[7]] * airport_growth

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
    
    sw_cte_array = np.zeros_like(cte_data, dtype="float")
    prod_col_idxs = np.array([1,2,3,5,6,7,4])
    attr_growth_idxs = [None, 2, 1, None, None, 2, 1, None, None]
    for j in range(sw_cte_array.shape[0]):
        if j < 8:
            sw_cte_array[j,:,1:8] = (cte_data[j,:,1:8] * 
                        production_growth[:,prod_col_idxs+(j*8)] *
                        airport_growth[:,None])
        else:
            sw_cte_array[j,:,1:8] = (cte_data[j,:,1:8] * 
                        production_growth[:,prod_col_idxs+((j-1)*8)] *
                        airport_growth[:,None])
        # These columns do the following
        if j in [0,3,4,7,8]:
            sw_cte_array[j,:,8] = sw_array[j,:,5]
        # Otherwise...
        else:
            sw_cte_array[j,:,8] = (cte_data[j,:,8] * 
                        production_growth[:,attr_growth_idxs[j]] * 
                        airport_growth)
    
    return (sw_array, sw_cte_array)

def save_trip_end_files(file_names, trip_ends, base_path, precision):
    for i, t_file in zip(range(trip_ends.shape[0]), file_names):
        path = os.path.join(base_path, t_file.replace("_ALL", ""))
        np.savetxt(path, np.concatenate(
                (np.arange(trip_ends[i].shape[0])[:,None]+1, trip_ends[i][:,1:]),axis=1),
                    delimiter=", ", 
                    fmt=["%d"]+["%." + str(precision) + "f" for x in range(trip_ends[i].shape[1]-1)])
                

def telmos_main(delta_root, tmfs_root, tel_year, tel_id, tel_scenario,
                base_year, base_id, base_scenario, is_rebasing_run=True,
                log_func=print, just_pivots=False):
    '''
    Conversion of the TMfS14 Visual Basic application 
    '''
    
    
    # Read in the trip rate matrices into multi-dim array
    factors_base = os.path.join(tmfs_root, "Factors")
    p_trip_rate_array = read_trip_rates(factors_base, just_pivots)
    
    # Load in the student factors and attraction factors separately
    attraction_file = "Attraction Factors.txt"
    attraction_factors = np.loadtxt(os.path.join(factors_base, attraction_file))
        
    # [Male student factor, Female student factor]
    # Used to factor the productions down
    student_factors = np.array([0.2794, 0.2453])
    
    log_func("Loaded SR Factors with shape: %s" % str(p_trip_rate_array.shape)) # old shape was (24, 6, 8, 11)
    log_func("Loaded Student Factors with shape: %s" % str(student_factors.shape))
    log_func("Loaded Attraction Factors with shape: %s" % str(attraction_factors.shape))
    
    # Read in planning data and pivoting files
    # planning data
    tel_tmfs_file = os.path.join(delta_root, tel_scenario, 
                                 "tmfs%s%s.csv" % (tel_year, tel_scenario.lower()))
    tel_tav_file = os.path.join(delta_root, tel_scenario, 
                                 "tav_%s%s.csv" % (tel_year, tel_scenario.lower()))
    # base pivoting files
    base_tmfs_file = os.path.join(tmfs_root, "Runs", base_year, "Demand",
                                  base_id, "tmfs%s_%s.csv" % (base_year, base_id))
    base_tav_file = os.path.join(tmfs_root, "Runs", base_year, "Demand",
                                  base_id, "tav_%s_%s.csv" % (base_year, base_id))
    
    
    tmfs_base_array = np.loadtxt(base_tmfs_file, skiprows=1, delimiter=",")
    count_i = tmfs_base_array.shape[0]
    tav_base_array = np.loadtxt(base_tav_file, skiprows=1, delimiter=",")
    
    
    tav_array = np.loadtxt(tel_tav_file, skiprows=1, delimiter=",")
    count_tav = tav_array.shape[0]
    tmfs_array = np.loadtxt(tel_tmfs_file, skiprows=1, delimiter=",",
                            usecols=range(2,11))
    tmfs_array = np.concatenate((np.zeros_like(tmfs_array[:,[0,1]]), tmfs_array), axis=1)
    # Previous version swaps columns 4 and 5 of the planning data
    # to be in line with the tmfs07 version expects
    tmfs_array[:,4], tmfs_array[:,5] = tmfs_array[:,5], tmfs_array[:,4].copy()
    count_tmfs = tmfs_array.shape[0]
    
    log_func("TAV Count: %d" % count_tav)
    log_func("I Count: %d" % count_i)
    log_func("TMFS Count: %d" % count_tmfs)

    # # # # # # # # # # # # # # # #
    # Put income segregation here #
    # (not implemented)           #
    # # # # # # # # # # # # # # # #

    # Rearrange and account for students
    tmfs_adj_array = np.copy(tmfs_array)
    tmfs_adj_array[:,:3] = tmfs_adj_array[:,2:5]
    tmfs_adj_array[:,3] = tmfs_adj_array[:,7] * student_factors[0]
    tmfs_adj_array[:,4] = tmfs_adj_array[:,8] * student_factors[1]
    tmfs_adj_array[:,7] = tmfs_adj_array[:,7] * (1 - student_factors[0])
    tmfs_adj_array[:,8] = tmfs_adj_array[:,8] * (1 - student_factors[1])

    log_func("TAV Base Array shape = %s" % str(tav_base_array.shape))
    log_func("TMFS Array shape = %s" % str(tmfs_array.shape))
    log_func("TMFS Adj Array shape = %s" % str(tmfs_adj_array.shape))

    # Attraction Factors
    # Apply the attraction factors to the tav array planning data
    attr_file = os.path.join(tmfs_root, "Runs", tel_year, "Demand", tel_id,
                             "tav_%s_%s.csv" % (tel_year, tel_id))
    attr_factors_array = create_attraction_pivot(tav_array, attraction_factors)
    # Output pivot attraction factors
    np.savetxt(attr_file, attr_factors_array.round(3), delimiter=",",
            header="HW,HE,HO,HS", fmt="%.3f", comments="")
    log_func("Attraction Factors saved to %s" % str(attr_file))

    # Calculate Attraction Growth Factors
    attr_growth_array = attr_factors_array / tav_base_array
    # Replace Infinite values with 1
    attr_growth_array[attr_growth_array == np.inf] = 1.0

    # # # # # # # # # # # #
    # Production Factors
    area_corres_file = os.path.join(tmfs_root, "Factors", "AreaCorrespondence.csv")
    area_corres_array = np.loadtxt(area_corres_file, skiprows=1, delimiter=",",
                                   usecols=2, dtype="int8")
    # Area correspondence array maps tmfs18 zones to their urban rural classification
    area_corres_array = np.repeat(area_corres_array, 8)
    log_func("Area Correspondence shape = %s" % str(area_corres_array.shape))
    
    check_file = os.path.join(tmfs_root, "Runs", tel_year,
                              "Demand", tel_id, "check2.csv")
    
    
    prod_factor_array = create_production_pivot(tmfs_adj_array, p_trip_rate_array,
                                                area_corres_array, check_file,
                                                count_tav, tmfs_base_array.shape,
                                                just_pivots)
    
    
    prod_factor_file = os.path.join(tmfs_root, "Runs", tel_year, "Demand", tel_id, "tmfs%s_%s.csv" % (tel_year, tel_id))
    
    # Output pivot production factors
    file_header = ("WAC C0,WAC C11,WAC C12,WAC C2,WAP C0,WAP C11,WAP C12,"
                   "WAP C2,OAC C0,OAC C11,OAC C12,OAC C2,OAP C0,OAP C11,OAP C12,OAP C2,"
                   "EAC C0,EAC C11,EAC C12,EAC C2,EAP C0,EAP C11,EAP C12,EAP C2,SAC C0,"
                   "SAC C11,SAC C12,SAC C2,SAP C0,SAP C11,SAP C12,SAP C2,WIC C0,WIC C11,"
                   "WIC C12,WIC C2,WIP C0,WIP C11,WIP C12,WIP C2,OIC C0,OIC C11,OIC C12,"
                   "OIC C2,OIP C0,OIP C11,OIP C12,OIP C2,EIC C0,EIC C11,EIC C12,EIC C2,"
                   "EIP C0,EIP C11,EIP C12,EIP C2,SIC C0,SIC C11,SIC C12,SIC C2,SIP C0,"
                   "SIP C11,SIP C12,SIP C2")
    if just_pivots is True:
        # Output pm and offpeak factors 
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
        log_func("Completed calculating pivoting tables")
        log_func("Finished")
        return

    np.savetxt(prod_factor_file, prod_factor_array.round(3), delimiter=",",
                header=file_header, fmt="%.3f", comments="")
    log_func("Production Factors saved to %s" % str(prod_factor_file))
        
    
    ## # # # # # # # # #
    # Production Growth Factors
    # Calculate growth from the base and tel_year pivot files
    prod_growth_array = prod_factor_array / tmfs_base_array
    prod_growth_array[prod_growth_array == np.inf] = 1.0
    log_func("Production Growth Array shape = %s" % str(prod_growth_array.shape))

    prefixes = ["AM","IP"]
    types = ["HWZ_A1", "HOZ_A1_ALL", "HEZ_A1_ALL", "HSZ_A1"]
    tod_files = ["%s_%s.TOD" % (prefix, t) for prefix in prefixes for t in types] + ["PM_HSZ_A1.TOD"]
    cte_files = [("%s_%s.CTE" % (prefix, t)).replace("A1","D0") for prefix in prefixes for t in types] + ["PM_HSZ_D0.CTE"]
    
    cte_tod_base_path = os.path.join(tmfs_root, "Runs", base_year,"Demand", base_id)
    tod_data, cte_data = load_cte_tod_files(tod_files, cte_files, cte_tod_base_path)
    
    log_func("TOD Data Shape = %s" % str(tod_data.shape))
    log_func("CTE Data Shape = %s" % str(cte_data.shape))

    airport_growth = np.ones(count_tav,dtype="float")
    if is_rebasing_run is False:
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

    sw_array, sw_cte_array = apply_pivot_files(tod_data, cte_data, 
                                             prod_growth_array, attr_growth_array,
                                             airport_growth)

    log_func("SW Array shape = %s" % str(sw_array.shape))

    # Print the TOD and CTE files - index +1: array(round(3))
    # All the zones are internal, so are labelled continuously - 1->787 as of tmfs18
    
    base_path = os.path.join(tmfs_root, "Runs", tel_year, "Demand", tel_id)
    
    save_trip_end_files(tod_files, sw_array, base_path, 3)
    log_func("TOD Files saved to %s" % str(base_path))
    save_trip_end_files(cte_files, sw_cte_array, base_path, 5)
    log_func("CTE Files saved to %s" % str(base_path))
    
    # Check that each array CTE and TOD is > 15kBytes
    for i,test_array in enumerate(sw_array):
        if test_array.nbytes < 15000:
            log_func("TOD Array is incomplete: %d" % i)
    for i,test_array in enumerate(sw_cte_array):
        if test_array.nbytes < 15000:
            log_func("CTE Array is incomplete: %d" % i)
            
