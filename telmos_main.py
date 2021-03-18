# -*- coding: utf-8 -*-
"""

@author: japeach

Conversion of TELMOS2_v2.2 vb scripts
"""

import os
from itertools import product
from typing import Callable, Dict, List, Tuple, Union
from collections import defaultdict
import warnings

import numpy as np
import pandas as pd

from scripts.extract_trip_rates import convert_rates_format

# Factors applied to non-working to produce student population segmentation
MALE_STUDENT_FACTOR = 0.2794
FEMALE_STUDENT_FACTOR = 0.2453

# Default Trip Rate file
TR_FILE = "TripRates.csv"
# Default Trip rate file for home-working split
SPLIT_TR_FILE = "TripRatesSplit.csv"
# Default Airport factor file
AIRPORT_FAC_FILE = "airport_factors.csv"
# Default Area correspondence file
AREA_DEF_FILE = "AreaCorrespondence.csv"

# Define the values used when reading in trip rates
TR_PURPOSES = ["HBW", "HBO", "HBE", "HBS"]
TR_MODES = ["Car", "PT"]
TR_PERIODS = ["AM", "IP", "PM"]
TR_AREA_TYPES = list(range(3, 9))
TR_WORK_TYPES = ["WAH", "WBC"]

# Define the number of zones (used to check inputs only)
INT_ZONES = 787
ALL_ZONES = 803
# Define checks for number of rows/columns in each input file
INPUT_CHECKS = {
    "TR": [len(list(product(TR_PURPOSES,
                            TR_MODES,
                            TR_PERIODS + ["OP"],
                            TR_AREA_TYPES,
                            range(88)))),  # 88 Traveller types
           6],  # Exludes traveller type desc
    "TR_SPLIT": [len(list(product(TR_PURPOSES,
                                  TR_MODES,
                                  TR_PERIODS + ["OP"],
                                  TR_AREA_TYPES,
                                  range(120)))),  # 88 + 32 from WAH/WBC split
                 7],  # Exludes traveller type desc
    "POP": [INT_ZONES * 8, 11],
    "POP_SPLIT": [INT_ZONES * 8, 15],
    "EMP": [INT_ZONES, 9],
    "ATT_FAC": [15, 10],
    "AREA": [ALL_ZONES, 2]
}


def check_input_dims(df: pd.DataFrame,
                     input_check_flag: str,
                     input_file_name: str = None,
                     raise_err: bool = True
                     ) -> bool:
    """Checks the dimensions of an input dataframe against the expected values

    Args:
        df (pd.DataFrame): The input dataframe to check
        input_check_flag (str): Flag used to get the expected values from
        INPUT_CHECKS
        input_file_name (str, optional): Name to display in the error/warning.
        Defaults to None.
        raise_err (bool, optional): If an error should be raised - if False,
        will just raise a warning. Defaults to True.

    Raises:
        ValueError: If the dimensions are not as expected
    """
    messages = []
    file_name = input_file_name or input_check_flag
    target_dims = INPUT_CHECKS[input_check_flag]
    if df.shape[0] != target_dims[0]:
        messages.append(f"Incorrect number of rows in {file_name}: Should be "
                        f"{target_dims[0]} but found {df.shape[0]}")
    if df.shape[1] != target_dims[1]:
        messages.append(f"Incorrect number of columns in {file_name}: Should "
                        f"be {target_dims[1]} but found {df.shape[1]}")
    if len(messages) > 0:
        if raise_err:
            raise ValueError("::".join(messages))
        else:
            warnings.warn("::".join(messages))
        return False
    return True


def read_trip_rates(factors_dir, just_pivots):
    '''
    Loads the production trip rate files into a numpy array
    '''

    periods = TR_PERIODS

    if just_pivots is True:
        periods.append("OP")

    sr_array = []
    for area_type in TR_AREA_TYPES:
        data = []
        segmentations = product(periods, TR_PURPOSES, TR_MODES)
        for period, purpose, mode in segmentations:
            file_name = "%s_%s_%s_%s.txt" % (purpose, mode, period, area_type)
            factor_file = os.path.join(factors_dir, file_name)
            data.append(np.loadtxt(factor_file))
        sr_array.append(data)
    return np.asarray(sr_array)


def read_trip_rates_home_working(factors_dir: str,
                                 just_pivots: bool,
                                 wah_tag: str = "WAH"
                                 ) -> np.array:

    # Add off-peak to the period list if required
    periods = TR_PERIODS
    if just_pivots is True:
        periods.append("OP")

    file_base = "{purp}_{mode}_{period}_{area}_{wah_tag}.txt"

    # Setup an empty list to store the trip rates
    trip_rates = []

    # Loop through all available segmentation for the trip rates
    for area_type in TR_AREA_TYPES:

        data = []
        segmentations = product(periods, TR_PURPOSES, TR_MODES)

        for period, purpose, mode in segmentations:

            file_name = file_base.format(
                purp=purpose,
                mode=mode,
                period=period,
                area=area_type,
                wah_tag=wah_tag
            )
            file_path = os.path.join(factors_dir, file_name)

            data.append(np.loadtxt(file_path))

        trip_rates.append(data)

    return np.asarray(trip_rates)


def read_long_trip_rates(trip_rate_path: str,
                         work_type_split: bool = False,
                         just_pivots: bool = False
                         ) -> Union[np.array, Dict[str, np.array]]:
    """Alternative function to the original read_trip_rates and
    read_trip_rates_home_working functions. Reads in a single combined as
    generated by extract_trip_rates.py for easier input file management.

    Args:
        trip_rate_path (str): Path to the trip rate combined file.
        work_type_split (bool, optional): Flag if rates are split between
        Working at Home and Working by Commute. Defaults to False.
        just_pivots (bool, optional): Flag if only pivots are being created
        and all periods shoule be used. Defaults to False.

    Returns:
        Union[np.array, Dict[str, np.array]]: Either a np.array object if
        work_type_split is False, or a dictionary with keys ["WAH", "WBC"]
        if True.
    """

    # Define the segmentation required from the trip rate file - could move
    # this to common constants
    trip_rate_seg = ["purpose", "mode", "period", "area", "traveller_type"]
    if work_type_split:
        trip_rate_seg.append("work_type")
    trip_rate_val = ["trip_rate"]

    # Read in all trip rates as a dataframe
    try:
        tr_df = pd.read_csv(trip_rate_path)[trip_rate_seg + trip_rate_val]
    except KeyError as e:
        raise ValueError(f"Could not find {e} in trip rate file"
                         f": {trip_rate_path}")

    # Check input dimensions are correct
    input_ok = check_input_dims(tr_df,
                                "TR_SPLIT" if work_type_split else "TR",
                                input_file_name="Trip Rate File",
                                raise_err=False)

    # Add off-peak to the period list if required
    periods = TR_PERIODS
    if just_pivots is True:
        periods.append("OP")

    # Setup an empty dictionary to store the rates [work_type]
    trip_rates = defaultdict(lambda: defaultdict(list))

    # Loop through all available segmentation for the trip rates
    segmentations = product(TR_AREA_TYPES, periods, TR_PURPOSES, TR_MODES)
    for area_type, period, purpose, mode in segmentations:
        # Extract the segmentation from the dataframe
        df = tr_df.loc[
            (tr_df["period"] == period)
            & (tr_df["mode"] == mode)
            & (tr_df["purpose"] == purpose)
            & (tr_df["area"] == area_type)
        ]
        # Extract just the traveller type, work type (if available) and
        # trip rate
        df = df[trip_rate_seg[4:] + trip_rate_val]

        if work_type_split:
            for work_type in TR_WORK_TYPES:
                use_work_types = ["ALL", work_type]
                filtered_df = df.loc[df["work_type"].isin(use_work_types)]
                arr = filtered_df.sort_values("traveller_type")[trip_rate_val]
                arr = convert_rates_format(
                    arr.values,
                    direction="to_wide"
                )
                trip_rates[work_type][area_type].append(arr)
        else:
            arr = df.sort_values("traveller_type")[trip_rate_val]
            arr = convert_rates_format(
                arr.values,
                direction="to_wide"
            )
            trip_rates["ALL"][area_type].append(arr)

    # Combine into a single numpy array
    for work_type in trip_rates:
        tr_array = list(trip_rates[work_type].values())
        trip_rates[work_type] = np.asarray(tr_array)

    if work_type_split:
        return trip_rates
    else:
        return trip_rates["ALL"]


def load_cte_tod_files(tod_files, cte_files, file_base):
    tod_data = []
    cte_data = []
    for t_file, c_file in zip(tod_files, cte_files):
        # TMfS14 had a long-distance module that required some CTE/TOD files
        # to have _All appended to the end. This can now be removed if needed.
        t_file_name = (
            t_file if os.path.isfile(os.path.join(file_base, t_file))
            else t_file.upper().replace("_ALL", "")
        )
        c_file_name = (
            c_file if os.path.isfile(os.path.join(file_base, c_file))
            else c_file.upper().replace("_ALL", "")
        )
        tod_data.append(np.loadtxt(os.path.join(file_base, t_file_name),
                                   delimiter=","))
        cte_data.append(np.loadtxt(os.path.join(file_base, c_file_name),
                                   delimiter=","))
    return (np.asarray(tod_data), np.asarray(cte_data))


def student_factor_adjustment(population_data: np.array) -> np.array:
    """Split columns in the tmfs population data using student factors.
    Also removes unnecessary columns.

    Args:
        population_data (np.array): Numpy array of population data, extracted
        from the DELTA directory.

    Returns:
        np.array: The adjusted array containing non-working split by student/
        non-students
    """
    adjusted_arr = np.copy(population_data)

    adjusted_arr[:, :3] = adjusted_arr[:, 2:5]
    adjusted_arr[:, 3] = adjusted_arr[:, 7] * MALE_STUDENT_FACTOR
    adjusted_arr[:, 4] = adjusted_arr[:, 8] * FEMALE_STUDENT_FACTOR
    adjusted_arr[:, 7] = adjusted_arr[:, 7] * (1 - MALE_STUDENT_FACTOR)
    adjusted_arr[:, 8] = adjusted_arr[:, 8] * (1 - FEMALE_STUDENT_FACTOR)

    return adjusted_arr


def create_attraction_pivot(planning_data: np.array,
                            attraction_trip_rates: np.array
                            ) -> np.array:
    """Multiples the employment planning data and attraction trip rates to
    produce synthetic attractions

    Args:
        planning_data (np.array): Planning data from land use model, shape is
        (num of zones, 8 columns)
        attraction_trip_rates (np.array): Attraction trip rates, containing
        15 attraction sites and 9 purposes

    Returns:
        np.array: Attractions pivoting file, containing 4 purpose columns
    """
    # Purpose Columns are: Work, Employment, Other, Education - All HB
    attr_factors_array = np.ones((planning_data.shape[0], 4), dtype="float32")

    # Create Work column
    # planning columns - employment
    work = planning_data[:, 2]
    # Extract the single attraction factor (HB Work, All Jobs)
    work_factor = attraction_trip_rates[0, 0]
    attr_factors_array[:, 0] = work * work_factor

    # Create Business/ In Employment column
    # planning columns - households, agricul and fishing, retail,
    # hospitality, local financial, education, health & sociol serv
    employment = planning_data[:, [1, 3, 4, 5, 6, 7, 8]].sum(axis=1)
    # Extract the single attraction factor (HB Emp Business, All)
    # Note that this expects the same factor for e.g. schools, Hotels,
    # Retail, etc. - TODO: could use a combination instead
    employment_factor = attraction_trip_rates[2, 1]
    attr_factors_array[:, 1] = employment * employment_factor

    # Create Other column
    # planning columns - retail, health & socio serv, households,
    # agricul and fishing
    other = planning_data[:, [4, 8, 1, 3]]
    # Extract attraction factors -
    # [(HB Shopping, Retail),
    # (HB Personal Business, Health/Medical),
    # (HB Visiting, Households),
    # (HB Holiday, Agriculture/Fishing)]
    other_factor = attraction_trip_rates[[6, 7, 1, 12], [3, 4, 8, 9]]
    attr_factors_array[:, 2] = (other * other_factor).sum(axis=1)

    # Create Education column
    # planning columns - education
    education = planning_data[:, 7]
    # Extract attraction factor - (HB Education, Schools).
    # Note that this expects the same factor for e.g. schools,
    # higher education, and adult education
    education_factor = attraction_trip_rates[2, 2]
    attr_factors_array[:, 3] = education * education_factor

    return attr_factors_array


def create_production_pivot(planning_data: np.array,
                            production_trip_rates: np.array,
                            area_correspondence: np.array,
                            output_shape: Tuple[int, int],
                            just_pivots: bool,
                            check_file: str = None,
                            int_zones: int = None
                            ) -> np.array:
    """Created the synthetic productions pivot file. Multiplies planning data
    by relevant trip rates, based on : area type, period/purpose/mode,
    household/person type.
    Aggregates the household/person types to the 4 household types required

    Args:
        planning_data (np.array): Population split by employment type,
        male/female, and age
        production_trip_rates (np.array): Trip rates read from read_trip_rates
        functions
        area_correspondence (np.array): Area definition for each model zone
        output_shape (Tuple[int, int]): Shape required by the output array
        just_pivots (bool): If all time periods should be used
        check_file (str, optional): Output path of optional check file.
        Defaults to None.
        int_zones (int, optional): Number of internal zones. Defaults to None.

    Returns:
        np.array: Synthetic productions used in pivoting. Saved as tmfsXXXX.csv
    """

    split_prod_array = np.zeros((24, planning_data.shape[0], 11))
    if just_pivots is True:
        split_prod_array = np.zeros((32, planning_data.shape[0], 11))

    # Store contents of check2 file to output later if required
    check_file_data = []

    # Define the iterators
    segment_combinations = range(split_prod_array.shape[0])
    person_types = range(split_prod_array.shape[2])
    # This part seems strange, it means that not all rows are used even in the
    #  VB version
    planning_data_rows = range(split_prod_array.shape[1] - 1)

    int_zones = int_zones or (len(planning_data_rows) // 8)

    # Variable to track the current household type (8 types)
    household_num = 0
    household_types = 8
    # Iterate through the combinations of period, purpose, mode
    for seg_num in segment_combinations:
        # Iterate through the 11 person types
        for person_num in person_types:

            # Iterate through each row in planning data
            # (num. zones * 8 household types)
            for row in planning_data_rows:
                # Index to the correct trip rate -
                #  area type (-3 to match indexing),
                #  segmentation (period, purpose, mode),
                #  household type,
                #  person type
                trip_rate = production_trip_rates[
                    area_correspondence[row] - 3,
                    seg_num,
                    household_num,
                    person_num
                ]
                split_prod_array[seg_num, row, person_num] = (
                    planning_data[row, person_num]
                    * trip_rate
                )

                # Continue iterating through household numbers up to 8
                household_num += 1
                if household_num == household_types:
                    household_num = 0
                check_file_data.append(
                    str(split_prod_array[seg_num, row, person_num])
                )

    if check_file is not None:
        with open(check_file, "w", newline="") as f:
            for line in check_file_data:
                f.write(line)
                f.write("\n")

    prod_factor_array = np.ones(output_shape)

    # Just Pivots is a debug option to output an extended version of
    #  the pivoting files
    # Originally outputs just 64 columns
    # - 2 periods * 4 Purposes * 2 Modes * 4 Aggregated Household types
    column_width = 2 * 4 * 2 * 4
    if just_pivots is True:
        # If just calculating the pivoting tables output all
        #  the possible time periods
        # - 4 Periods * 4 Purposes * 2 Modes * 4 Aggregated Household types
        column_width = 4 * 4 * 2 * 4
        prod_factor_array = np.zeros(
            (output_shape[0], output_shape[1] +
             int(column_width / 2)))

    # Aggregate the household types into C0, C11, C12, C2
    # - No cars available
    # - 1 adult, 1 car
    # - 2+ adults, 1 car
    # - 2+ cars

    # Planning data household types are stacked - 8 entries for each zone
    # - ordered in the following way
    c_0_idxs = [0, 2, 5]
    c_11_idxs = [1]
    c_12_idxs = [3, 6]
    c_2_idxs = [4, 7]
    agg_household_idxs = [c_0_idxs, c_11_idxs, c_12_idxs, c_2_idxs]

    prod_factor_array = np.zeros(
        (len(segment_combinations), len(agg_household_idxs), int_zones)
    )

    # Sum over all person types
    split_prod_array = split_prod_array.sum(axis=2)
    # Reshape to unstack household types
    split_prod_array = split_prod_array.reshape(
        (len(segment_combinations), household_types, int_zones),
        order="F"
    )

    # Aggregate household types
    for i, idxs in enumerate(agg_household_idxs):
        # Slice to the aggregate household type indices and sum them
        prod_factor_array[:, i, :] = split_prod_array[:, idxs, :].sum(axis=1)

    # Reshape to 2D array with the correct column order (transposed)
    required_segment_size = int(column_width / len(agg_household_idxs))
    prod_factor_array = prod_factor_array[:required_segment_size, :, :]
    prod_factor_array = prod_factor_array.reshape(column_width, int_zones).T

    return prod_factor_array


def calculate_growth(base, forecast):
    growth = forecast / base
    growth = np.select(
        [np.isinf(growth), np.isnan(growth)],
        [forecast, 1], default=growth
    )
    return growth


def apply_pivot_files(tod_data: np.array,
                      cte_data: np.array,
                      production_growth: np.array,
                      attraction_growth: np.array,
                      airport_growth: np.array
                      ) -> Tuple[np.array, np.array]:
    '''
    Applies growth to the base cte and tod files

    '''
    # Initialise forecast array for TOD data
    tod_f_array = np.zeros_like(tod_data, dtype="float")

    # Apply growth to generate forecast .TOD arrays

    # TOD/CTE array dimensions are:
    #  Period/Purpose = [AM(Work),AM(Other),AM(Business),AM(Education),
    #        IP(Work),IP(Other),IP(Business),IP(Education),PM(Education)]
    #  Zones = [num_zones]
    #  Household Types / ATtractions = [TOD([C11, C12, C2, C0, Attractions]),
    #      CTE([Car_C11, Car_C12, Car_C2, PT_C11, PT_C12, PT_C2, PT_C0, Attr])]

    # Reorder attraction growth purpose columns to match TOD/CTE order
    tod_attr_growth_idxs = [0, 2, 1, 3, 0, 2, 1, 3, 3]
    # Loop through AM and IP arrays
    for j in range(tod_f_array.shape[0] - 1):
        # Apply growth to C11, C12, and C2 columns by grouping Car / PT from
        # the CTE array (as CTE is more precise)
        # - extracting the relevant growth columns from the synthetic
        #   future / base in 'production_growth'
        tod_f_array[j, :, 1:4] = (
            (cte_data[j, :, 1:4] * production_growth[:, (1+8*j):(4+8*j)])
            + (cte_data[j, :, 4:7] * production_growth[:, (5+8*j):(8+8*j)])
            ) * airport_growth[:, None]
        # Apply the same process to C0 households (PT only)
        tod_f_array[j, :, 4] = (
            tod_data[j, :, 4]
            * production_growth[:, (4+8*j)]
            * airport_growth
        )
        # Finally apply attraction growth to the total attractions
        #  (using tod_attr_growth_idxs to get the correct column in attraction
        #   growth)
        tod_f_array[j, :, 5] = (
            tod_data[j, :, 5]
            * attraction_growth[:, tod_attr_growth_idxs[j]]
            * airport_growth
        )

    # Handle PM(Education) separately to fetch correct column in growth arrays
    tod_f_array[8, :, 1:4] = (
        (cte_data[8, :, 1:4] * production_growth[:, (1+8*7):(4+8*7)])
        + (cte_data[8, :, 4:7] * production_growth[:, (5+8*7):(8+8*7)])
        ) * airport_growth[:, None]
    tod_f_array[8, :, 4] = (
        tod_data[8, :, 4]
        * production_growth[:, (4+8*7)]
        * airport_growth
    )
    tod_f_array[8, :, 5] = (
        tod_data[8, :, 5]
        * attraction_growth[:, tod_attr_growth_idxs[7]]
        * airport_growth
    )

    # Apply attraction matching to Work and Education matrices
    tod_f_prod = {}
    tod_f_attr = {}

    tod_f_prod["AM_Work"] = tod_f_array[0, :, 1:5].sum()
    tod_f_prod["IP_Work"] = tod_f_array[4, :, 1:5].sum()
    tod_f_prod["AM_Edu"] = tod_f_array[3, :, 1:5].sum()
    tod_f_prod["IP_Edu"] = tod_f_array[7, :, 1:5].sum()
    tod_f_prod["PM_Edu"] = tod_f_array[8, :, 1:5].sum()

    tod_f_attr["AM_Work"] = tod_f_array[0, :, 5].sum()
    tod_f_attr["IP_Work"] = tod_f_array[4, :, 5].sum()
    tod_f_attr["AM_Edu"] = tod_f_array[3, :, 5].sum()
    tod_f_attr["IP_Edu"] = tod_f_array[7, :, 5].sum()
    tod_f_attr["PM_Edu"] = tod_f_array[8, :, 5].sum()

    tod_f_array[0, :, 5] *= (tod_f_prod["AM_Work"] / tod_f_attr["AM_Work"])
    tod_f_array[4, :, 5] *= (tod_f_prod["IP_Work"] / tod_f_attr["IP_Work"])
    tod_f_array[3, :, 5] *= (tod_f_prod["AM_Edu"] / tod_f_attr["AM_Edu"])
    tod_f_array[7, :, 5] *= (tod_f_prod["IP_Edu"] / tod_f_attr["IP_Edu"])
    tod_f_array[8, :, 5] *= (tod_f_prod["PM_Edu"] / tod_f_attr["PM_Edu"])

    cte_f_array = np.zeros_like(cte_data, dtype="float")
    # Set the production growth indexes to use
    prod_col_idxs = np.array([1, 2, 3, 5, 6, 7, 4])
    for j in range(cte_f_array.shape[0]):
        # Handle AM and IP using the standard growth columns
        if j < 8:
            cte_f_array[j, :, 1:8] = (
                cte_data[j, :, 1:8]
                * production_growth[:, prod_col_idxs+(j*8)]
                * airport_growth[:, None]
            )
        # PM Requires a different index to access the growth
        else:
            cte_f_array[j, :, 1:8] = (
                cte_data[j, :, 1:8]
                * production_growth[:, prod_col_idxs+((j-1)*8)]
                * airport_growth[:, None]
            )
        # Apply attraction growth
        cte_f_array[j, :, 8] = (
            cte_data[j, :, 8]
            * attraction_growth[:, tod_attr_growth_idxs[j]]
            * airport_growth
        )

    return (tod_f_array, cte_f_array)


def save_trip_end_files(file_names: List[str],
                        trip_ends: np.array,
                        base_path: str,
                        precision: int
                        ) -> None:

    for i, t_file in zip(range(trip_ends.shape[0]), file_names):

        path = os.path.join(base_path, t_file.replace("_ALL", ""))
        format_cols = ["%d"] + [
            "%." + str(precision) + "f"
            for x in range(trip_ends[i].shape[1]-1)
        ]

        out_arr = np.concatenate(
            (
                np.arange(trip_ends[i].shape[0])[:, None]+1,
                trip_ends[i][:, 1:]
            ),
            axis=1
        )
        np.savetxt(
            path,
            out_arr,
            delimiter=", ",
            fmt=format_cols
        )


def telmos_main(delta_root: str,
                tmfs_root: str,
                tel_year: str,
                tel_id: str,
                tel_scenario: str,
                base_year: str,
                base_id: str,
                base_scenario: str,
                is_rebasing_run: bool = True,
                log_func: Callable = print,
                just_pivots: bool = False,
                trip_rate_file: str = "",
                airport_growth_file: str = "",
                integrate_home_working: bool = False,
                legacy_trip_rates: bool = False
                ) -> None:
    '''
    Applies growth to base year trip end files for input into the second stage
    of the TMfS18 trip end model
    '''

    # Build paths to the trip rate file
    factors_base = os.path.join(tmfs_root, "Factors")
    if trip_rate_file == "":
        # Use the default version
        tr_name = SPLIT_TR_FILE if integrate_home_working else TR_FILE
        tr_path = os.path.join(factors_base, tr_name)
    else:
        tr_path = trip_rate_file
    # Check that the required file exists
    if not os.path.isfile(tr_path):
        raise ValueError(f"Trip Rate file does not exist: {tr_path}")
    log_func(f"Using trip rates from {tr_path}")

    # # Read in the trip rate matrices into multi-dim array
    log_func("Loading Production Trip Rates")
    if legacy_trip_rates:
        tr_message = "Loaded {} Trip Rate Factors with shape: {}"
        if integrate_home_working:
            log_func("Integrating Home Working Splits")
            p_trip_rate_array = {"WAH": None, "WBC": None}
            for work_type in p_trip_rate_array:
                p_trip_rate_array[work_type] = read_trip_rates_home_working(
                    factors_base,
                    just_pivots=just_pivots,
                    wah_tag=work_type
                )
                log_func(
                    tr_message.format(
                        work_type,
                        p_trip_rate_array[work_type].shape
                    )
                )
        else:
            p_trip_rate_array = read_trip_rates(factors_base, just_pivots)
            log_func(tr_message.format("all", p_trip_rate_array.shape))

    # Read in the combined version of the trip rate files
    else:
        p_trip_rate_array = read_long_trip_rates(
            tr_path,
            work_type_split=integrate_home_working
        )
        log_func(f"Using Split Trip Rates: {integrate_home_working}")
        log_func(f"Loaded Trip Rate Factors from {tr_path}")

    # Load in the student factors and attraction factors separately
    log_func("Loading Attraction Factors")
    attraction_file = "Attraction Factors.txt"
    attraction_factors = pd.read_csv(
        os.path.join(factors_base, attraction_file),
        header=None,
        delimiter=" "
    )
    att_fac_ok = check_input_dims(attraction_factors,
                                  "ATT_FAC",
                                  "Attraction Factors")
    attraction_factors = attraction_factors.values

    # Read in planning data and pivoting files
    # planning data

    # If using home working split inputs, create 2 tmfs_array objects, one
    # for each split. These can be combined in create_production_pivot()
    tel_scenario_tmfs = tel_scenario.lower()
    if integrate_home_working:
        # tel_scenario_tmfs = "{}_hw".format(tel_scenario.lower())
        # Need to load in extra columns for the working at home split
        use_cols_tmfs = range(2, 15)
        # Define how the array will be split - take 2 sets of columns
        split_tmfs = {"WAH": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                      "WBC": [0, 1, 2, 11, 12, 13, 14, 7, 8, 9, 10]}
    else:
        use_cols_tmfs = range(2, 11)
        split_tmfs = None

    tel_tmfs_file = os.path.join(
        delta_root,
        tel_scenario,
        "tmfs%s%s.csv" % (tel_year, tel_scenario_tmfs)
    )
    tel_tav_file = os.path.join(
        delta_root,
        tel_scenario,
        "tav_%s%s.csv" % (tel_year, tel_scenario.lower())
    )
    # base pivoting files
    base_tmfs_file = os.path.join(
        tmfs_root,
        "Runs",
        base_year,
        "Demand",
        base_id,
        "tmfs%s_%s.csv" % (base_year, base_id)
    )
    base_tav_file = os.path.join(
        tmfs_root,
        "Runs",
        base_year,
        "Demand",
        base_id,
        "tav_%s_%s.csv" % (base_year, base_id)
    )

    log_func("Loading Base Year Synthetic Productions")
    tmfs_base_array = np.loadtxt(base_tmfs_file, skiprows=1, delimiter=",")
    count_i = tmfs_base_array.shape[0]
    tav_base_array = np.loadtxt(base_tav_file, skiprows=1, delimiter=",")

    log_func("Loading Future Year Planning Data")
    tav_array = pd.read_csv(tel_tav_file)
    check_input_dims(tav_array,
                     "EMP",
                     input_file_name="Employment Planning Data",
                     raise_err=True)
    tav_array = tav_array.values
    count_tav = tav_array.shape[0]
    tmfs_array = pd.read_csv(tel_tmfs_file)
    # tmfs_array = np.loadtxt(tel_tmfs_file, skiprows=1, delimiter=",")
    # Check that the coorect number of columns are there
    check_input_dims(tmfs_array,
                     "POP_SPLIT" if integrate_home_working else "POP",
                     input_file_name="Population Planning Data",
                     raise_err=True)
    tmfs_array = tmfs_array.values
    tmfs_array = tmfs_array[:, list(use_cols_tmfs)]
    tmfs_array = np.concatenate(
        (np.zeros_like(tmfs_array[:, [0, 1]]), tmfs_array), axis=1)
    count_tmfs = tmfs_array.shape[0]

    # Extract the columns required for the 2 versions of tmfs_array if required
    if split_tmfs:
        tmfs_array = {
            work_type: tmfs_array[:, split_cols]
            for work_type, split_cols in split_tmfs.items()
        }
        for work_type in tmfs_array:
            tmfs_array[work_type][:, 4], tmfs_array[work_type][:, 5] = (
                tmfs_array[work_type][:, 5], tmfs_array[work_type][:, 4].copy()
            )
    else:
        # Previous version swaps columns 4 and 5 of the planning data
        # to be in line with the tmfs07 version expects
        tmfs_array[:, 4], tmfs_array[:, 5] = (
            tmfs_array[:, 5], tmfs_array[:, 4].copy()
        )

    log_func(f"Number of Zones: {count_tav}")
    log_func(f"Planning Data Row Count {count_tmfs}")

    # # # # # # # # # # # # # # # #
    # Put income segregation here #
    # (not implemented)           #
    # # # # # # # # # # # # # # # #

    # Rearrange and account for students
    log_func("Applying Student Factor Splits")
    if split_tmfs:
        tmfs_adj_array = {}
        # Adjust each array individually
        for work_type in tmfs_array:
            tmfs_adj_array[work_type] = student_factor_adjustment(
                tmfs_array[work_type]
            )
            tmfs_array_shape = tmfs_array[work_type].shape
            tmfs_adj_array_shape = tmfs_adj_array[work_type].shape
    else:
        tmfs_adj_array = student_factor_adjustment(tmfs_array)
        tmfs_array_shape = tmfs_array.shape
        tmfs_adj_array_shape = tmfs_adj_array.shape

    # tmfs_adj_array = np.copy(tmfs_array)
    # tmfs_adj_array[:,:3] = tmfs_adj_array[:,2:5]
    # tmfs_adj_array[:,3] = tmfs_adj_array[:,7] * MALE_STUDENT_FACTOR
    # tmfs_adj_array[:,4] = tmfs_adj_array[:,8] * FEMALE_STUDENT_FACTOR
    # tmfs_adj_array[:,7] = tmfs_adj_array[:,7] * (1 - MALE_STUDENT_FACTOR)
    # tmfs_adj_array[:,8] = tmfs_adj_array[:,8] * (1 - FEMALE_STUDENT_FACTOR)

    # Attraction Factors
    # Apply the attraction factors to the tav array planning data
    log_func("Creating Synthetic Attractions")
    attr_file = os.path.join(tmfs_root, "Runs", tel_year, "Demand", tel_id,
                             "tav_%s_%s.csv" % (tel_year, tel_id))
    attr_factors_array = create_attraction_pivot(tav_array, attraction_factors)
    # Output pivot attraction factors
    np.savetxt(attr_file, attr_factors_array.round(3), delimiter=",",
               header="HW,HE,HO,HS", fmt="%.3f", comments="")

    # Calculate Attraction Growth Factors
    log_func("Calculating Attraction Growth")
    attr_growth_array = calculate_growth(
        base=tav_base_array.round(3), forecast=attr_factors_array.round(3))

    # # # # # # # # # # # #
    # Production Factors
    log_func("Loading Area Correspondence Lookup")
    area_corres_file = os.path.join(
        tmfs_root, "Factors", AREA_DEF_FILE)
    area_corres_array = pd.read_csv(area_corres_file, dtype="int")
    area_ok = check_input_dims(area_corres_array,
                               "AREA",
                               "Area Definition File")
    area_corres_array = area_corres_array.values[:, 1]
    # Area correspondence array maps tmfs18 zones to their urban
    #  rural classification - repeat for each of the household types
    area_corres_array = np.repeat(area_corres_array, 8)

    check_file = os.path.join(tmfs_root, "Runs", tel_year,
                              "Demand", tel_id, "check2.csv")

    # Create the production pivot data - multiplying population/planning data
    # by the trip rates

    # For home working split data, we need to combine the resulting pivot data
    log_func("Creating Synthetic Productions")
    if integrate_home_working:
        prod_factor_array = None
        for work_type in tmfs_adj_array:
            # Check that the work type is valid (Should be WAH or WBC)
            if work_type not in p_trip_rate_array:
                raise ValueError("Error: Could not find split in Trip Rates")

            # Pick out the columns that have not been split
            split_cols = [1, 2, 5, 6]
            # Halve all other columns to prevent double counts
            split_pop_data = tmfs_adj_array[work_type].copy()
            non_split_cols = [x for x in range(split_pop_data.shape[1])
                              if x not in split_cols]
            split_pop_data[:, non_split_cols] /= 2

            temp_prod_factors = create_production_pivot(
                planning_data=split_pop_data,
                production_trip_rates=p_trip_rate_array[work_type],
                area_correspondence=area_corres_array,
                output_shape=tmfs_base_array.shape,
                just_pivots=just_pivots,
                int_zones=count_tav
            )

            if prod_factor_array is None:
                prod_factor_array = temp_prod_factors
            else:
                prod_factor_array += temp_prod_factors
    # Otherwise, can just use the output data
    else:
        prod_factor_array = create_production_pivot(
            planning_data=tmfs_adj_array,
            production_trip_rates=p_trip_rate_array,
            area_correspondence=area_corres_array,
            output_shape=tmfs_base_array.shape,
            just_pivots=just_pivots,
            check_file=check_file,
            int_zones=count_tav
        )

    prod_factor_file = os.path.join(
        tmfs_root,
        "Runs",
        tel_year,
        "Demand",
        tel_id,
        "tmfs%s_%s.csv" % (tel_year, tel_id)
    )

    # Output pivot production factors
    purposes = ["W", "O", "E", "S"]
    periods = ["A", "I"]
    modes = ["C", "P"]
    households = ["C0", "C11", "C12", "C2"]
    if just_pivots:
        periods.extend(["P", "O"])
    file_header = [
        f"{purp}{period}{mode} {hh}" for period, purp, mode, hh
        in product(periods, purposes, modes, households)
    ]
    file_header = ",".join(file_header)

    np.savetxt(prod_factor_file, prod_factor_array.round(3), delimiter=",",
               header=file_header, fmt="%.3f", comments="")

    if just_pivots:
        log_func("Completed calculating synthetic PAs")
        log_func("Finished")
        return

    # # # # # # # # # # #
    # Production Growth Factors
    # Calculate growth from the base and tel_year pivot files
    log_func("Calculating Production Growth")
    prod_growth_array = calculate_growth(
        base=tmfs_base_array.round(3),
        forecast=prod_factor_array.round(3)
    )

    log_func("Loading Base Year Calibrated Trip Ends")
    prefixes = ["AM", "IP"]
    types = ["HWZ_A1", "HOZ_A1_ALL", "HEZ_A1_ALL", "HSZ_A1"]
    tod_files = ["%s_%s.TOD" % (prefix, t)
                 for prefix in prefixes for t in types] + ["PM_HSZ_A1.TOD"]
    cte_files = [("%s_%s.CTE" % (prefix, t)).replace("A1", "D0")
                 for prefix in prefixes for t in types] + ["PM_HSZ_D0.CTE"]

    cte_tod_base_path = os.path.join(
        tmfs_root, "Runs", base_year, "Demand", base_id)
    tod_data, cte_data = load_cte_tod_files(
        tod_files, cte_files, cte_tod_base_path)

    airport_growth = np.ones(count_tav, dtype="float")
    if is_rebasing_run is False:
        # Airport indices are as follows (zones are indices + 1):
        #   708 = Edinburgh Airport
        #   709 = Prestwick Airport
        #   710 = Glasgow Airport
        #   711 = Aberdeen Airport

        # Factors updated as of TMfS 2018
        #   708 = 4.97% Edinburgh
        #   709 = 7.6%  Prestwick
        #   710 = 3.33% Glasgow
        #   711 = 1.86% Aberdeen

        ####
        #   Previous method for airport growth < TMfS18
        #    (constant value per annum)

        ####
        #   New method for airport growth >= TMfS18 (growth varies
        #        according to DfT 2017 aviation forecast)
        # now reads in a file from "Factors" that contains the expected growth
        # from 2017
        if airport_growth_file == "":
            airport_growth_file = os.path.join(
                tmfs_root,
                "Factors",
                AIRPORT_FAC_FILE
            )
        log_func(f"Loading Airport Factors from {airport_growth_file}")
        if not os.path.isfile(airport_growth_file):
            raise FileNotFoundError("File does not exist: {}".format(
                airport_growth_file))
        factors = pd.read_csv(airport_growth_file, index_col="Year")
        factors = factors.loc[int(tel_year) + 2000] / \
            factors.loc[int(base_year) + 2000]
        airport_growth[factors.index.astype("int")] = factors.values

    log_func("Applying Growth to Calibrated Trip Ends")
    sw_array, sw_cte_array = apply_pivot_files(
        tod_data,
        cte_data,
        prod_growth_array.round(5),
        attr_growth_array.round(5),
        airport_growth
    )

    # Print the TOD and CTE files - index +1: array(round(3))
    # All the zones are internal, so are labelled continuously - 1->787
    #   as of tmfs18

    base_path = os.path.join(tmfs_root, "Runs", tel_year, "Demand", tel_id)

    log_func("Saving .TOD Files")
    save_trip_end_files(tod_files, sw_array, base_path, 3)
    log_func("Saving .CTE Files")
    save_trip_end_files(cte_files, sw_cte_array, base_path, 5)

    # Check that each array CTE and TOD is > 15kBytes
    for i, test_array in enumerate(sw_array):
        if test_array.nbytes < 15000:
            log_func("TOD Array is incomplete: %d" % i)
    for i, test_array in enumerate(sw_cte_array):
        if test_array.nbytes < 15000:
            log_func("CTE Array is incomplete: %d" % i)

    log_func("Finished Main Trip End Growth")
