#!/usr/bin/python
# -*- coding: utf-8 -*-

# This file adapted from mms_load_data.py from the pyspedas library,
# sourced from https://github.com/spedas/pyspedas
#
# All modifications copyright 2019 Tim Rogers.  All rights reserved.
# Released under the Apache 2.0 license.
#
# Original copyright notice from pyspedas preserved below for proper attribution:


# Copyright (c) 2017, THEMIS group, Space Sciences Laboratory, UC Berkeley.
# 
# All rights reserved.
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.



import os
import requests
import logging
import numpy as np
from .load_datafile import load_datafile
from concurrent.futures import ThreadPoolExecutor
#from multiprocessing import Pool
#from p_tqdm import p_map
from functools import partial
import pandas as pd
import re

from dateutil.parser import parse
from datetime import timedelta, datetime, timezone

from . import mms_sdc_api_client as mms_sdc_api_client

logging.captureWarnings(True)
logging.basicConfig(format='%(asctime)s: %(message)s', datefmt='%d-%b-%y %H:%M:%S', level=logging.INFO)

def mms_load_data(trange=['2015-10-16', '2015-10-17'], probe='1', data_rate='srvy', level='l2', 
    instrument='fgm', datatype='', anc_product=None, descriptor=None, 
    varformat=None, prefix='', suffix='', get_support_data=False, time_clip=False, 
    no_update=False, center_measurement=False, notplot=False, data_root=None):
    """
    This function loads MMS data into a dictionary by variable name.
    
    Parameters:
        trange : list of str
            time range of interest [starttime, endtime] with the format 
            'YYYY-MM-DD','YYYY-MM-DD'] or to specify more or less than a day 
            ['YYYY-MM-DD/hh:mm:ss','YYYY-MM-DD/hh:mm:ss']

        probe : str or list of str
            list of probes, valid values for MMS probes are ['1','2','3','4']. 

        data_rate : str or list of str
            instrument data rates for FGM include 'brst' 'fast' 'slow' 'srvy'. The
            default is 'srvy'.

        level : str
            indicates level of data processing. the default if no level is specified is 'l2'

        instrument : str or list of str
            Name(s) of instrument(s) for which to load data.

        datatype : str or list of str
            One or more types of data to load.
            Must be selected from this list: ['ancillary', 'hk', 'science']
            If given as an empty string or not provided, will default to 'science' data.

        anc_product : str or list of str
            One or more ancillary products to load.

        descriptor : str or list of str
            Optional name(s) of data subset(s) to load.

        varformat: str
            The file variable formats to load.  Wildcard character
            "*" is accepted.  By default, all variables are loaded in.

        prefix: str
            The variable names will be given this prefix.  By default, 
            no prefix is added.

        suffix: str
            The variable names will be given this suffix.  By default, 
            no suffix is added.

        get_support_data: bool
            If True, data with an attribute "VAR_TYPE" with a value of "support_data"
            will be loaded into data tables.  If False, only loads in data with a 
            "VAR_TYPE" attribute of "data".  Defaults to False.

        time_clip: bool
            Data will be clipped to the exact trange specified by the trange keyword.

        no_update: bool
            If true, do not poll the upstream MMS data repository for new/updated data.
            This will limit loading to only files already available from the local system.

        center_measurement: bool
            If True, the CDF epoch variables are time-shifted to the middle
            of the accumulation interval by their DELTA_PLUS_VAR and
            DELTA_MINUS_VAR variable attributes

        notplot: bool
            [Deprecated] No effect.  Parameter is preserved for partial
            compatibility with original pyspedas implementation.

        data_root: str
            Full path to the root directory where MMS directory structure begins.
            If not provided, will default to '<user_home>/data/mms'

    Returns:
        Tuple of dictionaries with the loaded data and metadata.
        ie. (data, metadata)

    """

    if not (isinstance(probe, list) or probe is None): probe = [probe]
    if not (isinstance(data_rate, list) or data_rate is None): data_rate = [data_rate]
    if not isinstance(datatype, list): datatype = [datatype]
    if not isinstance(level, list): level = [level]
    if not isinstance(descriptor, list): descriptor = [descriptor]
    
    if probe:
      probe = [('mms'+(str(p))) for p in probe]

    # We're going to handle everything as datetime objects fo consistancy and easy conversion at-need.
    local_trange = [None,None]
    
    if type(trange[0]) == datetime: # Already a datetime.
        local_trange[0] = trange[0]
    elif type(trange[0]) in (int,float,np.float32,np.float64): # Convert from posix timestamp if provided.
        local_trange[0] = datetime.fromtimestamp(trange[0], timezone.utc)
    elif type(trange[0]) == str: # Parse the string and generate a datetime.
        local_trange[0] = parse(trange[0])
    else:
        raise TypeError("Unsupported input format for start date/time.")
    
    if type(trange[1]) == datetime: # Already a datetime.
        local_trange[1] = trange[1]
    elif type(trange[1]) == int: # Convert from posix timestamp if provided.
        local_trange[1] = datetime.fromtimestamp(trange[1], timezone.utc)
    elif type(trange[1]) == str: # Parse the string and generate a datetime.
        local_trange[1] = parse(trange[1])
    else:
        raise TypeError("Unsupported input format for end date/time.")
    
    # Replicating behavior of pyspedas:
    start_date = local_trange[0].isoformat()
    end_date = local_trange[1].isoformat()
    
    
    out_files = []
    
    for dtype in datatype:
        # Default to 'science' data, as the old SPEDAS implementation assumed that and used "datatype" for something else entirely.
        if len(dtype) == 0: dtype = 'science'
        for lvl in level:
            for desc in descriptor:
                mms_api_client = mms_sdc_api_client.MMS_SDC_API_CLIENT(
                        sc=probe, 
                        instr=instrument, 
                        mode=data_rate, 
                        level=lvl,
                        data_type=dtype,
                        anc_product=anc_product,
                        data_root=data_root,
                        end_date=end_date,
                        offline=no_update,
                        optdesc=desc,
                        site='public',
                        start_date=start_date)
                logging.info('download URI: '+mms_api_client.url())
                out_files.extend(mms_api_client.Download())

    out_files = sorted(out_files)
    
    #Because we're not using pytplot, new_variables is a simple dictionary containing the data.
    #  eg.
    #    pytplot:  get_data(Varname)
    #    current:  new_variables[Varname].values()
    #new_variables,new_metadata = load_cdf(out_files, varformat=varformat, get_support_data=get_support_data, prefix=prefix, suffix=suffix, center_measurement=center_measurement)
    
    new_variables = {}
    new_metadata = {}
    
    logging.info('Beginning parallel load of '+str(len(out_files))+' data files...')
    
    # This attempts to load all requested cdf files into memory concurrently, using as many threads as the system permits.
    # The load_cdf function returns a tuple of (data, metadata), so pile_o_data will be a list of these tuples.
    # pile_o_data = p_map(load_cdf, out_files, varformat, get_support_data, prefix, suffix, center_measurement)
    #pile_o_data = p_map(partial(load_datafile, varformat=varformat, get_support_data=get_support_data, prefix=prefix, suffix=suffix, center_measurement=center_measurement), out_files)
    ##pile_o_data = p_map(partial(load_cdf, varformat=varformat, get_support_data=get_support_data, prefix=prefix, suffix=suffix, center_measurement=center_measurement), out_files)
    with ThreadPoolExecutor() as p:
        pile_o_data = p.map(partial(load_datafile, varformat=varformat, get_support_data=get_support_data, prefix=prefix, suffix=suffix, center_measurement=center_measurement), out_files)

    # Merge matching variable names across loaded files.
    logging.info('Stitching together the data...')
    for data,metadata in pile_o_data:
      # merge data dictionary
      if isinstance(data, pd.DataFrame):
        # Ancillary data loaded via Pandas magic.
        dataset = metadata['Set_Name']
        
        # Metadata
        if dataset not in new_metadata.keys():
            # No previous entries for this dataset.  Add the whole thing as-is.
            new_metadata[dataset] = metadata
        else:
            # Compare the new set's metadata with the existing metadata.
            for meta in [key for key in metadata.keys() if key in set(new_metadata[dataset].keys())]:
                # Print a notice for any unexpected differences, but don't raise exceptions.
                if metadata[meta] != new_metadata[dataset][meta]:
                    #Ancillary data is wierd.  Just append any new metadata to the existing metadata field.
                    metadata[meta] = str(metadata[meta]) + ', ' +str(new_metadata[dataset][meta])
                    #logging.warning("Dataset '"+dataset+"' has non-matching metadata between input files. Old: {'"+meta+"': '"+new_metadata[dataset][meta]+"'} -- Now using: {'"+meta+"': '"+metadata[dataset][meta]+"'}")
            # Update the metadata, overwriting old values if appliciable.
            new_metadata[dataset].update(metadata)
        # Data values
        if dataset not in new_variables.keys():
            # No previous entries for this dataset.  Add the whole thing as-is.
            new_variables[dataset] = data
        else:
            # Panic and error out if the datasets with identical names don't have the same axes/variables being tracked.
            if len(new_variables[dataset].keys()) != len(data.columns):
                logging.error('Failure to merge new data with axes ('+(','.join(data.columns))+') with existing data with axes ('+(','.join((new_variables[dataset].keys())))+')'+'.')
                raise TypeError('Failure to merge new data with axes ('+(','.join(data.columns))+') with existing data with axes ('+(','.join((new_variables[dataset].keys())))+')'+'.')
            
            # Update existing dataset entry with the additional data.
            new_variables[dataset] = new_variables[dataset].append(data)
      else:
        # Direct loaded from CDF.
        for dataset in data.keys():
            if dataset not in new_variables.keys():
                # No previous entries for this dataset.  Add the whole thing as-is.
                new_variables[dataset] = data[dataset]
            else:
                # Panic and error out if the datasets with identical names don't have the same axes/variables being tracked.
                if len(new_variables[dataset].keys()) != len(data[dataset].keys()):
                    logging.error('Failure to merge new data with axes ('+(','.join((data[dataset].keys())))+') with existing data with axes ('+(','.join((new_variables[dataset].keys())))+')'+'.')
                    raise TypeError('Failure to merge new data with axes ('+(','.join((data[dataset].keys())))+') with existing data with axes ('+(','.join((new_variables[dataset].keys())))+')'+'.')
                
                # Update existing dataset entry with the additional data.
                for axis in data[dataset].keys():
                    new_variables[dataset][axis] = np.concatenate((new_variables[dataset][axis],data[dataset][axis]))
        # write/revise metadata
        for dataset in metadata.keys():
            if dataset not in new_metadata.keys():
                # No previous entries for this dataset.  Add the whole thing as-is.
                new_metadata[dataset] = metadata[dataset]
            else:
                # Compare the new set's metadata with the existing metadata.
                for meta in [key for key in metadata[dataset].keys() if key in set(new_metadata[dataset].keys())]:
                    # Print a notice for any unexpected differences, but don't raise exceptions.
                    if metadata[dataset][meta] != new_metadata[dataset][meta]:
                        logging.warning("Dataset '"+dataset+"' has non-matching metadata between input files. Old: {'"+meta+"': '"+new_metadata[dataset][meta]+"'} -- Now using: {'"+meta+"': '"+metadata[dataset][meta]+"'}")
                # Update the metadata, overwriting old values if appliciable.
                new_metadata[dataset].update(metadata[dataset])
    
    if len(new_variables) == 0:
        logging.warning('No data loaded.')
        return
    
    if len(new_metadata) == 0:
        logging.warning('No metadata loaded.')
        return
    
    # Drop any duplicate entries in the pandas dataframes.
    for dataset in new_variables.values():
        if isinstance(dataset, pd.DataFrame):
            dataset = dataset.drop_duplicates()
    
    logging.info('Loaded variables:')
    for new_var in new_variables.keys():
        print(new_var)
    
    if time_clip:
        logging.info('Clipping variables to time range...')
        mms_data_time_clip(new_variables, local_trange[0], local_trange[1])
    
    return new_variables, new_metadata
    #else:
    #    return out_files


def mms_data_time_clip(data_dict, start_time, end_time):
    """
    Revised function to clip all datasets in the data_dict to the specified time range.
    
    This function assumes the following:
        - in each dataset, there exists a numpy array 'x', which is a time axis
        - all values in the time axis are of the same type
        - being numpy arrays, the aforementioned type will be some form of float, representing a unix timestamp
    
    """

    new_start = 0.
    new_end = 0.

    # Handle likely input types for start and end times.  Convert to unix timestamp.
    if type(start_time) == datetime: # Handle all datetimes as UTC timezone
        new_start = start_time.replace(tzinfo=timezone.utc).timestamp()
    elif type(start_time)  in (int,float,np.float32,np.float64): # Looks like it's already a timestamp. Use as-is.
        new_start = start_time
    elif type(start_time) == str: # Parse the string, then convert to timestamp.
        new_start = parse(start_time).replace(tzinfo=timezone.utc).timestamp()
    else:
        raise TypeError("Unsupported input format for start date/time.")
    
    if type(end_time) == datetime: # Handle all datetimes as UTC timezone
        new_end = end_time.replace(tzinfo=timezone.utc).timestamp()
    elif type(end_time)  in (int,float,np.float32,np.float64): # Looks like it's already a timestamp. Use as-is.
        new_end = end_time
    elif type(end_time) == str: # Parse the string, then convert to timestamp.
        new_end = parse(end_time).replace(tzinfo=timezone.utc).timestamp()
    else:
        raise TypeError("Unsupported input format for end date/time.")
    
    
    for setname in data_dict.keys():
        dataset = data_dict[setname]
        if isinstance(dataset, pd.DataFrame):
            epochRegex = re.compile('(Epoch|UTC)', re.IGNORECASE)
            dKeys = [x for x in dataset.keys() if epochRegex.match(x)]
            if len(dKeys) > 0:
                timearr = dataset[dKeys[0]].values
            else:
                # Hope that the first column is the epoch date/times, despite name issues.
                timearr = dataset[dataset.keys()[0]].values
        else:
            timearr = dataset['x']
        start_index = 0
        end_index = len(timearr)-1
        
        # Early sanity checks
        if new_start > new_end:
            logging.error('Error: Start time is after end time.')
            continue
        if (new_start > timearr[len(timearr)-1]) or (new_end < timearr[0]):
            logging.warning('Entire dataset removed by time clipping: "'+setname+'"')
            continue
        if (new_start <= timearr[0]) and (new_end >= timearr[len(timearr)-1]):
            logging.info('Entire dataset included in time clip range: "'+setname+'"')
            continue
        
        # Find our indices
        while timearr[start_index] < new_start: start_index += 1
        while timearr[end_index] > new_end: end_index -= 1
        
        # End index needs to point at the first index we want to exclude after the data.
        end_index += 1

        # Update the datasets
        for axis in dataset.keys():
            # Only clip the axis if it is a list/array instead of a scalar.
            if isinstance(dataset[axis], list):  # It's a list!
                if len(dataset[axis]) >= 1:
                    dataset[axis] = dataset[axis][start_index:end_index]
            elif isinstance(dataset[axis], np.ndarray):  # It's a numpy array!
                if len(dataset[axis].shape) >= 1:
                    dataset[axis] = dataset[axis][start_index:end_index]
            #else: It's neither.  no-op

    # Dictionary was directly altered.  No value directly returned.
