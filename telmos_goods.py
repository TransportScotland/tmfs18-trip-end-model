# -*- coding: utf-8 -*-
"""

@author: japeach

Conversion of TELMOS2_v2.2 vb scripts
"""

import os
from typing import Callable, Tuple

import numpy as np
import pandas as pd


def load_goods_data(goods_file: str,
                    hgv_output: str,
                    lgv_output: str
                    ) -> Tuple[np.array, np.array]:
    '''
    Loading function for TELMoS goods files
    Splits the data into LGV and HGV parts
    '''
    hgv_lines = []
    lgv_lines = []
    # Inconsistent format of input data - iterate through
    # lines, use indicator to check if HGV / LGV
    with open(goods_file, "r") as f:
        for line in f:
            split_line = line.split()
            indicator = split_line.pop(0)
            if indicator == "1":
                hgv_lines.append(split_line)
            elif indicator == "2":
                lgv_lines.append(split_line)
            else:
                continue

    # Frame should have 3 columns and an entry for each zone pair 1-803
    hgv_df = pd.DataFrame(hgv_lines, columns=["I", "J", "V"], dtype="float64")
    lgv_df = pd.DataFrame(lgv_lines, columns=["I", "J", "V"], dtype="float64")

    if not len(hgv_df) == 803*803:
        raise ValueError("HGV file requires 803 * 803 entries")
    if not len(lgv_df) == 803*803:
        raise ValueError("LGV file requires 803 * 803 entries")

    # TELMoS file zones are numbered with 1-783 as internal, 784-799 external
    #  and 800-803 internal. These should be renumbered to be in line with
    #  TMfS numbering, inserting 800-803 before external zones
    # Internal zones 800-803 get renumbered to 784-787,
    # and external zones 784-799 renumbered to 788-803
    zone_map = {
        z: z if z < 784 else z+4 if z < 800 else z-16 for z in range(1, 804)
    }

    # Rewrap zone numbers as integers and renumber zones
    for df in (hgv_df, lgv_df):
        for col in ("I", "J"):
            df[col] = df[col].astype(int).map(zone_map)
        # Sort the renumbered dataframe
        df.sort_values(by=["I", "J"], inplace=True)
        df.reset_index(drop=True, inplace=True)

    hgv_df.to_csv(hgv_output, index=False, header=False)
    lgv_df.to_csv(lgv_output, index=False, header=False)

    hgv_array = hgv_df.pivot_table(index="I", columns="J").to_numpy()
    lgv_array = lgv_df.pivot_table(index="I", columns="J").to_numpy()
    return (hgv_array, lgv_array)


def telmos_goods(delta_root: str,
                 tmfs_root: str,
                 tel_year: str,
                 tel_id: str,
                 tel_scenario: str,
                 base_year: str,
                 base_id: str,
                 base_scenario: str,
                 is_rebasing_run: bool = True,
                 log_func: Callable = print
                 ) -> None:
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
    # # # # # # # # # #

    # # # Outputs # # #
    tel_hgv_file = os.path.join(
        tmfs_root,
        "Runs",
        tel_year,
        "Demand",
        tel_id,
        "hgv%s%s.dat" % (tel_year, tel_id)
    )
    tel_lgv_file = os.path.join(
        tmfs_root,
        "Runs",
        tel_year,
        "Demand",
        tel_id,
        "lgv%s%s.dat" % (tel_year, tel_id)
    )
    base_hgv_file = os.path.join(
        tmfs_root,
        "Runs",
        base_year,
        "Demand",
        base_id,
        "hgv%s%s.dat" % (base_year, base_id)
    )
    base_lgv_file = os.path.join(
        tmfs_root,
        "Runs",
        base_year,
        "Demand",
        base_id,
        "lgv%s%s.dat" % (base_year, base_id)
    )
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
    hgv_base_array, lgv_base_array = load_goods_data(
        base_goods_file,
        base_hgv_file,
        base_lgv_file
    )

    zone_count = hgv_base_array.shape[0]

    # Repeat for tel data
    hgv_tel_array, lgv_tel_array = load_goods_data(
        tel_goods_file,
        tel_hgv_file,
        tel_lgv_file
    )

    log_func("HGV Count = %s" % str(zone_count))

    # # # # # # # # # # # # # # #

    goods_totals = {"TEL_HGV": np.sum(hgv_tel_array),
                    "TEL_LGV": np.sum(lgv_tel_array),
                    "BASE_HGV": np.sum(hgv_base_array),
                    "BASE_LGV": np.sum(lgv_base_array)}

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

    goods_growth_array = {"HGV": hgv_tel_array / hgv_base_array,
                          "LGV": lgv_tel_array / lgv_base_array}

    # # # # Read base am/ip/pm hgv/lgv files
    base_goods_array = {}
    forecast_goods_array = {}
    goods_total = {}
    new_forecast_array = {}
    for filename in filenames:

        # Keys to access dictionary
        f_key = filename.replace(".DAT", "")
        goods_type = f_key[-3:]  # HGV or LGV

        # Read base values from file
        base_goods_array[f_key] = np.array(pd.read_csv(
            os.path.join(base_filebase, filename), header=None,
            index_col=[0, 1]).unstack(-1))

        # Apply growth for forecast
        forecast_goods_array[f_key] = (
            base_goods_array[f_key][:zone_count, :zone_count]
            * goods_growth_array[goods_type][:zone_count, :zone_count]
        )

        # Sum of base and forecast matrices - Only up to 783
        # - changed to hgv_count to reflect number of zones
        goods_total["%s_base" % f_key] = np.sum(
            base_goods_array[f_key][:zone_count, :zone_count])
        goods_total["%s_forecast" % f_key] = np.sum(
            forecast_goods_array[f_key][:zone_count, :zone_count])

        # Adjust TMfS Forecast matrices
        if is_rebasing_run is True:
            new_forecast_array[f_key] = base_goods_array[f_key]
        else:
            # Road Traffic Forecast no longer used for external zones -
            #  TELMoS forecast goods files now include all zones
            new_forecast_array[f_key] = (
                forecast_goods_array[f_key] *
                ((goods_total["%s_base" % f_key] *
                  goods_totals["TEL_%s" % goods_type]) /
                 (goods_total["%s_forecast" % f_key] *
                  goods_totals["BASE_%s" % goods_type])))
        # Print these files stacked
        df = pd.DataFrame(new_forecast_array[f_key]).stack().reset_index()
        df.columns = ['I', 'J', 'V']

        # Change zone numbers from 0-based to 1-based
        df['I'] += 1
        df['J'] += 1

        # Create Trip End Files
        te_array = np.stack(
            (
                np.arange(new_forecast_array[f_key].shape[0]) + 1,
                new_forecast_array[f_key].sum(axis=1),
                new_forecast_array[f_key].sum(axis=0)
            ),
            axis=1
        )
        if te_array.nbytes < 500:
            log_func("Trip End Array is incomplete")
        save_path = os.path.join(
            tel_filebase,
            filename.replace(".DAT", "TE.DAT")
        )
        np.savetxt(
            save_path,
            te_array,
            fmt=["%d", "%.9f", "%.9f"],
            delimiter=","
        )
        log_func("Goods TE saved to %s" % save_path)

    # Check array sizes are > 250KBytes
    for k, array in new_forecast_array.items():
        if array.nbytes < 250000:
            log_func("Array is incomplete %s" % k)
