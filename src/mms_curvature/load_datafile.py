# Copyright 2020 Tim Rogers.  All rights reserved.
# Released under the Apache 2.0 license.
#

from .load_cdf import load_cdf
import re
import numpy as np
import pandas as pd
import datetime as dt
import os
#import xarray as xr
#from pytplot.store_data import store_data
#from pytplot.tplot import tplot
#from pytplot.options import options
#from pytplot import data_quants
#import copy


def load_datafile(filename, varformat=None, get_support_data=False,
                 prefix='', suffix='', center_measurement=False):
    """
    This function delagates data file loading based upon supplied file info.
    At present, this just handles standard data files (CDF) and ancillary data.

    Parameters:
        filenames : str
            The file name and full path of the data file.
        varformat : str
            (CDF-only)
            The file variable formats to load into tplot.  Wildcard character
            "*" is accepted.  By default, all variables are loaded in.
        get_support_data: bool
            (CDF-only)
            Data with an attribute "VAR_TYPE" with a value of "support_data"
            will be loaded into tplot.  By default, only loads in data with a
            "VAR_TYPE" attribute of "data".
        prefix: str
            The tplot variable names will be given this prefix.  By default,
            no prefix is added.
        suffix: str
            The tplot variable names will be given this suffix.  By default,
            no suffix is added.
        center_measurement: bool
            (CDF-only)
            If True, the CDF epoch variables are time-shifted to the middle
            of the accumulation interval by their DELTA_PLUS_VAR and
            DELTA_MINUS_VAR variable attributes

    Returns:
        Tupple of dictionaries containing the variables loaded and related metadata.
        ie.  (variables, metadata)
    """

    #if isinstance(filenames, str):
    #    filenames = [filenames]
    #elif isinstance(filenames, list):
    #    filenames = filenames
    #else:
    #    print("Invalid filenames input.")
    #    return (output_table, metadata)  # These will be empty a dictionaries at this time.
    if not isinstance(filename, str):
        raise ValueError('Invalid input for "filename" parameter!')

    if 'ancillary' in filename:
        return load_ancillary_data(filename, prefix=prefix, suffix=suffix)
    else:
        return load_cdf(filename, varformat=varformat, get_support_data=get_support_data, prefix=prefix, suffix=suffix, center_measurement=center_measurement)
            


def load_ancillary_data(filename, prefix='', suffix=''):
    """
    This function will load the dataset and metadata from an ancillary data file.
    Parameters:
        filename : str
            The full path of the ancillary data file.
        prefix: str
            The tplot variable names will be given this prefix.  By default,
            no prefix is added.
        suffix: str
            The tplot variable names will be given this suffix.  By default,
            no suffix is added.

    Returns:
        Tupple of dictionaries containing the variables loaded and related metadata.
        ie.  (variables, metadata)
    """

    epoch_cache = {}
    output_table = {}
    metadata = {}

    if not isinstance(filename, str):
        print("Invalid filename input.")
        return (output_table, metadata)  # These will be empty a dictionaries at this time.

    try:
        file = open(filename, "r")
        title = file.readline().strip()
        #data_in = []
        #data = dict()
        meta = dict()
        metalines = 0
        meta_interrupt = False
        meta['Title'] = title
        Set_Name = prefix
        Set_Name += '_'.join(os.path.splitext(os.path.basename(filename))[0].split('_',maxsplit=2)[0:2])
        Set_Name += suffix
        meta['Set_Name'] = Set_Name
        
        for line in file:
            metalines += 1
            # Parse metadata lines.
            tmpline = line.strip()
            if tmpline == '':
                # End of metadata.  Bail out of the file.
                break
            while tmpline[-1] == ',':
                tmpline += file.readline().strip()
                metalines += 1
            line_split = tmpline.partition('=')
            key = line_split[0].strip()
            value = [item.strip() for item in (line_split[-1].split(','))]
            meta[key] = value
        #end for
    finally:
        # Always a good idea to ensure we drop open file handles.
        if not file.closed:
            file.close()

    extra_lines = 0
    skiplines = [x for x in range(metalines)]
    dateRegex = re.compile('^\d{4}-\d{3}/')
    dFile = pd.read_csv(filename, skiprows=skiplines, sep='\s\s+', engine='python')
    while not dateRegex.match(str(dFile.values[0][0])):
        extra_lines += 1
        skiplines += [metalines+extra_lines]
        dFile = pd.read_csv(filename, skiprows=skiplines, sep='\s\s+', engine='python')
    epochRegex = re.compile('(Epoch|UTC)', re.IGNORECASE)
    dKeys = [x for x in dFile.keys() if epochRegex.match(x)]
    if len(dKeys) > 0:
        dFile[dKeys[0]] = dFile[dKeys[0]].map(lambda date: dt.datetime.strptime(date[:-4], '%Y-%j/%H:%M:%S').timestamp() + float(date[-4:]))
    
    return (dFile, meta)




#        # Parse data lines...
#        # Parse headers for continued reference.
#        header_line = file.readline().strip()
#
#        data_headers = re.split('\s\s+', data_in[0])
#        data_cols = [None]*len(data_headers)
#        for headernum in len(data_headers):
#            # Doing it this way to ensure consistant ordering of columns
#            data[data_headers[headernum]] = []
#            data_cols[headernum] = [data_in[0].find(data_headers[headernum])]
#        
#        
#        # Parse data lines into the output dict.  Leave everything as a string for now.
#        for line in data_in[1:]:
#            line_data = re.split('\s\s+', line)
#            for headernum in len(data_headers):
#                data[data_headers[headernum]] += line_data[headernum]
#        
#        #########################################################################
#        
#        
#        if var_name not in output_table:
#            output_table[var_name] = axis_data
#        else:
#            var_data = output_table[var_name]
#            for output_var in var_data:
#                if output_var not in nontime_varying_depends:
#                    var_data[output_var] = np.concatenate((
#                        var_data[output_var], axis_data[output_var]))

    #except:
    #    
    #    
#    finally:
#        # Always a good idea to ensure we drop open file handles.
#        if not file.closed:
#            file.close()
#
#
#    return (output_table, metadata)

