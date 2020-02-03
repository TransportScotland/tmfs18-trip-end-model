# -*- coding: utf-8 -*-
"""

@author: japeach

Conversion of TELMOS2_v2.2 vb scripts
"""

import numpy as np
import pandas as pd

def odfile_to_matrix(in_file, num_columns=1, delimiter=",", header=None):
    # Assumes that dat is ordered
    data = pd.read_csv(in_file, sep=delimiter, index_col=[0,1],header=header)
    return_data = []
    for col in range(num_columns):
        return_data.append(np.array(data[col + 2].unstack()))
    if num_columns > 1:
        return return_data
    else:
        return return_data[0]
    
def matrix_to_odfile(data, out_file, num_columns=1, delimiter=","):
    # data is a NumPy array or list of NumPy arrays
    def stack_matrix(matrix):
        df = pd.DataFrame(matrix).stack().reset_index()
        df.loc[:,:"level_1"] += 1
        return df
        
    if num_columns > 1:
        dfs = []
        for matrix in data:
            dfs.append(stack_matrix(matrix))
        df = pd.concat([dfs[0].loc[:,:"level_1"]] + [x[0] for x in dfs], axis=1)
    else:
        df = stack_matrix(data)
    df.to_csv(out_file, index=None, columns=None, header=None)