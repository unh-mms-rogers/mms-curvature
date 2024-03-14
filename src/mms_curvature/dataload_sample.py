# Copyright 2019-2022 Tim Rogers.  All rights reserved.
# Released under the Apache 2.0 license.

# This file is retained only for historical reference.

import pyspedas

def DataLoad(trange=['2017-05-01', '2017-05-02/15:30:02'], data_rate='srvy', level='l2'):
    '''
    This function displays example usage of the data load methods found in mms_load_data_shims.py
    
    Loads all data needed for calculating magnnetic field curvature from MMS FGM data.  
    Uses a modified pymms for accessing the SDC API, file downloading, and file version control
    Uses a modified load_cdf from pyspedas for CDF unpacking.

    Parameters:
    trange:     A list with two strings for the date range [tstart, tend]
                e.g. trange=['2017-05-01', '2017-05-02/15:30:02']

    data_rate:  The cadance of data which should be loaded.
                Options are 'srvy', 'brst'

    level:      The data level which will be loaded.  Use 'l2' unless you're sure otherwise.
    '''
    mec_data = pyspedas.mms.mec(
        trange=trange, 
        probe=['1', '2', '3', '4'], 
        data_rate='srvy', 
        level=level, 
        time_clip=True
    )
    fgm_data = pyspedas.mms.fgm(
        trange=trange, 
        probe=['1', '2', '3', '4'], 
        data_rate=data_rate, 
        level=level, 
        time_clip=True
        )
    return {"mec": mec_data, "fgm": fgm_data}
