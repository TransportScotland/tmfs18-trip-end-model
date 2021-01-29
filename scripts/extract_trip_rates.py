# -*- coding: utf-8 -*-
"""
Created on Wed Jul 31 09:57:11 2019

@author: japeach
"""

import os
from typing import List
from itertools import product

import numpy as np
import pandas as pd


def save_output(arr: np.array,
                out_path: str = None,
                combined_arr: List[np.array] = None,
                combined_args: List[str] = None
                ) -> list:

    if combined_arr is not None:
        ret_arr = combined_arr + [combined_args + [arr]]
        return ret_arr

    np.savetxt(out_path, arr, fmt=FLOAT_FORMAT)

    return None


# PARAMETERS
BASE_DIR = r"C:\Users\japeach\Documents\41456 - LATIS Scoping\Trip End Model"
WORKING_DIR = os.path.join(BASE_DIR, "Home Working", "Trip Rates")
INPUT_DIR = os.path.join(WORKING_DIR, "Input")
TRIP_RATE_NAME = "210129 Order Test"
OUTPUT_DIR = os.path.join(WORKING_DIR, "Output", TRIP_RATE_NAME)

if not os.path.isdir(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

DEBUG_MODE = False

# Factors to apply to trip rates for home-working split
SPLIT_HOME_WORKING = True
FACTOR = {
    "WAH": 1.0,
    "WBC": 1.0
}

# Define output file details
FLOAT_PRECISION = 3
FLOAT_FORMAT = f"%.{FLOAT_PRECISION}f"

# FLAG if single output file is required
COMBINE_OUTPUT = False

# Build Paths and load beta and rho files
beta_path = os.path.join(INPUT_DIR, "IBETAhsr_NTEM7.2_NEW.csv")
rho_path = os.path.join(INPUT_DIR, "IRhomdhsr_NTEM7.2_NEW.csv")
ref_dir = os.path.join("Input Data", "Input", "Factors")

b = pd.read_csv(beta_path)
r = pd.read_csv(rho_path)

# Fetch the lookup file for traveller type definitions if required
if COMBINE_OUTPUT:
    s_lookup_path = os.path.join(INPUT_DIR, "DefTraveller.csv")
    s_lookup = pd.read_csv(s_lookup_path)
    s_lookup["sDef"] = s_lookup["sDef"].str.strip("\"")
    s_lookup = s_lookup.set_index("s")["sDef"]

# Create lookup to purpose definitions
h_table = pd.DataFrame([[1, "HBW"], [2, "HBE"], [3, "HBS"]] + [
    [x, "HBO"] for x in range(4, 9)], columns=["h", "PURPOSE"])

# Merge beta and rho tables together on the common columns
rates = b.merge(r, on=["h", "s", "r"]).merge(h_table, on="h").sort_values(
        ["h", "s", "r"])

# Define the columns needed for each time period/mode combination
cols = [["AM_Car", ["m3d1", "m4d1"]],
        ["IP_Car", ["m3d2", "m4d2"]],
        ["PM_Car", ["m3d3", "m4d3"]],
        ["OP_Car", ["m3d4", "m4d4"]],
        ["AM_PT", ["m5d1", "m6d1"]],
        ["IP_PT", ["m5d2", "m6d2"]],
        ["PM_PT", ["m5d3", "m6d3"]],
        ["OP_PT", ["m5d4", "m6d4"]]]

# Apply the splits from rho to the trip rates in beta
for col_name, sum_cols in cols:
    rates[col_name] = rates[sum_cols].sum(axis=1) * rates["TripRates"]
rates.drop(["m%dd%d" % (m, d) for m in range(1, 7) for d in range(1, 7)],
           inplace=True, axis=1)
rates.drop(["h", "TripRates"], axis=1, inplace=True)

# Group similar purposes (other) together
g_rates = rates.groupby(["s", "r", "PURPOSE"]).sum().reset_index()

# Setup column order expected by the trip end model
col_order = [0, 1, 6, 3, 8, 2, 7, 4, 9, 5, 10]
total_diff = 0

# Loop through the segments and save each to a separate file
segment_iter = product(
    g_rates.PURPOSE.unique(),
    ["Car", "PT"],
    ["AM", "IP", "PM", "OP"],
    range(3, 9)
)

combined_arr = [] if COMBINE_OUTPUT else None

for purpose, mode, period, area in segment_iter:

    filename = "%s_%s_%s_%s.txt" % (purpose, mode, period, area)
    file_path = os.path.join(OUTPUT_DIR, filename)

    col = "%s_%s" % (period, mode)
    arr = g_rates.loc[
        (g_rates["r"] == area)
        & (g_rates["PURPOSE"] == purpose)
    ][col].to_numpy()

    arr = arr.reshape((8, 11), order="F")[:, col_order]

    if SPLIT_HOME_WORKING:
        for work_type in ["WAH", "WBC"]:
            factored_arr = arr * FACTOR[work_type]
            out_file = file_path.replace(".txt", f"_{work_type}.txt")
            comb_args = [purpose, mode, period, area, work_type]
            combined_arr = save_output(factored_arr,
                                       out_path=out_file,
                                       combined_arr=combined_arr,
                                       combined_args=comb_args)

    else:
        factored_arr = arr
        out_file = file_path
        comb_args = [purpose, mode, period, area]
        combined_arr = save_output(factored_arr,
                                   out_path=out_file,
                                   combined_arr=combined_arr,
                                   combined_args=comb_args)

    if DEBUG_MODE is True:
        ref_arr = np.loadtxt(os.path.join(ref_dir, filename))
        diff = ref_arr - arr
        print("Identical matrix %s: %r" % (
            filename,
            (arr.round(3) == ref_arr).sum() == arr.size
        ))
        total_diff += diff

if DEBUG_MODE is True:
    print("Total difference is %d" % total_diff)

if COMBINE_OUTPUT:
    # Retrieve the order of the trip rate traveller types (88 traveller types)
    reshaped_s = np.arange(1, 89, step=1)
    reshaped_s = reshaped_s.reshape((8, 11), order="F")[:, col_order]

    # Loop through and unstack each matrix
    combined_df = pd.DataFrame()
    columns = ["purpose", "mode", "period", "area"]
    if SPLIT_HOME_WORKING:
        columns.append("work_type")
    for matrix_details in combined_arr:
        arr = matrix_details.pop(-1)
        df = pd.DataFrame([matrix_details], index=range(88), columns=columns)

        df["traveller_type"] = reshaped_s.reshape(88)
        df["trip_rate"] = arr.reshape(88)

        if combined_df.empty:
            combined_df = df
        else:
            combined_df = combined_df.append(df)

    out_file = os.path.join(OUTPUT_DIR, f"{TRIP_RATE_NAME} Trip Rates.csv")
    sort_columns = columns + ["traveller_type"]
    combined_df = combined_df.sort_values(sort_columns)
    combined_df["tt_desc"] = combined_df["traveller_type"].map(s_lookup)
    combined_df.to_csv(out_file, index=False, float_format=FLOAT_FORMAT)
