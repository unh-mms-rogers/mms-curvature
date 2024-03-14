#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Feb 25 13:34:47 2018

@author: argall
"""

# File modified from original found in pymms repository:
#   https://github.com/argallmr/pymms
#
# All modifications copyright 2019 Tim Rogers.  All rights reserved.
# Released under the Apache 2.0 license.

import os
import datetime as dt
#import pdb # https://pythonconquerstheuniverse.wordpress.com/2009/09/10/debugging-in-python/



def construct_path(sc, instr=None, mode=None, level=None, tstart='*',
                   optdesc=None, root='', files=False):
    """
    Construct a directory structure compliant with MMS path guidelines.
    
    MMS paths follow the convention
        brst: sc/instr/mode/level[/optdesc]/<year>/<month>/<day>
        srvy: sc/instr/mode/level[/optdesc]/<year>/<month>
    
    Arguments:
        sc (str,list,tuple):   Spacecraft ID(s)
        instr   (str,list):    Instrument ID(s)
        mode    (str,list):    Data rate mode(s). Options include slow, fast, srvy, brst
        level   (str,list):    Data level(s). Options include l1a, l1b, l2pre, l2, l3
        tstart  (str,list):    Start time of data file, formatted as a date: '%Y%m%d'.
                               If not given, all dates from 20150901 to today's date are
                               used.
        optdesc (str,list):    Optional file name descriptor. If multiple parts,
                               they should be separated by hyphens ("-"), not under-
                               scores ("_").
        root    (str):         Root directory at which the directory structure begins.
        files   (bool):        If True, file names will be generated and appended to the
                               paths. The file tstart will be "YYYYMMDD*" (i.e. the date
                               with an asterisk) and the version number will be "*".
    
    Returns:
        fnames  (str,list);    File names constructed from inputs.
    """
    
    # Convert all to lists
    if isinstance(sc, str):
        sc = [sc]
    if isinstance(instr, str):
        instr = [instr]
    if isinstance(mode, str):
        mode = [mode]
    if isinstance(level, str):
        level = [level]
    if isinstance(tstart, str):
        tstart = [tstart]
    if optdesc is not None and isinstance(optdesc, str):
        optdesc = [optdesc]
    
    # Accept tuples, as those returned by MrMMS_Construct_Filename
    if type(sc) == 'tuple':
        sc_ids = [file[0] for file in sc]
        instr = [file[1] for file in sc]
        mode = [file[2] for file in sc]
        level = [file[3] for file in sc]
        tstart = [file[-2] for file in sc]
        
        if len(sc) > 6:
            optdesc = [file[4] for file in sc]
        else:
            optdesc = None
    else:
        sc_ids = sc
    
    # Paths + Files
    if files:
        if optdesc is None:
            paths = [os.path.join(root,s,i,m,l,t[0:4],t[4:6],t[6:8],'_'.join((s,i,m,l,t+'*','v*.cdf'))) if m == 'brst' else
                     os.path.join(root,s,i,m,l,t[0:4],t[4:6],'_'.join((s,i,m,l,t+'*','v*.cdf')))
                     for s in sc_ids
                     for i in instr
                     for m in mode
                     for l in level
                     for t in tstart]
        else:
            paths = [os.path.join(root,s,i,m,l,o,t[0:4],t[4:6],t[6:8],'_'.join((s,i,m,l,o,t+'*','v*.cdf'))) if m == 'brst' else
                     os.path.join(root,s,i,m,l,o,t[0:4],t[4:6],'_'.join((s,i,m,l,o,t+'*','v*.cdf')))
                     for s in sc_ids
                     for i in instr
                     for m in mode
                     for l in level
                     for o in optdesc
                     for t in tstart]
    
    # Paths
    else:
        if optdesc is None:
            paths = [os.path.join(root,s,i,m,l,t[0:4],t[4:6],t[6:8]) if m == 'brst' else
                     os.path.join(root,s,i,m,l,t[0:4],t[4:6]) for s in sc_ids
                                                              for i in instr
                                                              for m in mode
                                                              for l in level
                                                              for t in tstart]
        else:
            paths = [os.path.join(root,s,i,m,l,o,t[0:4],t[4:6],t[6:8]) if m == 'brst' else
                     os.path.join(root,s,i,m,l,o,t[0:4],t[4:6]) for s in sc_ids
                                                                for i in instr
                                                                for m in mode
                                                                for l in level
                                                                for o in optdesc
                                                                for t in tstart]
    
    
    return paths



def filter_time(fnames, start_date, end_date):
    """
    Filter files by their start times.
    
    Arguments:
        fnames (str,list):    File names to be filtered.
        start_date (str):     Start date of time interval, formatted as '%Y-%m-%dT%H:%M:%S'
        end_date (str):       End date of time interval, formatted as '%Y-%m-%dT%H:%M:%S'
    
    Returns:
        paths (list):     Path to the data file.
    """
    
    # Output
    outFiles = []
    fileNames = fnames
    if isinstance(fileNames, str):
        fileNames = [fileNames]
    
    # Convert date range to datetime objects
    start_date = dt.datetime.strptime(start_date, '%Y-%m-%dT%H:%M:%S')
    end_date = dt.datetime.strptime(end_date, '%Y-%m-%dT%H:%M:%S')
    
    # Parse the time out of the file name
    parts = parse_filename(fnames)
    
    craftSet = set()
    for name in parts:
        craftSet.add((name[0], name[1])) # First part is which spacecraft. Second is instrument.
    
    for craft in craftSet:
        files = [f for f in fileNames if os.path.basename(f).startswith(craft[0]+'_'+craft[1])]
        # Reparse just the set of files we're working with.
        parts = parse_filename(files)
        
        fstart = [dt.datetime.strptime(name[-2], '%Y%m%d') if len(name[-2]) == 8 else
                  dt.datetime.strptime(name[-2], '%Y%m%d%H%M%S')
                  for name in parts]
        
        # Sor the files by start time
        isort = sorted(range(len(fstart)), key=lambda k: fstart[k])
        fstart = [fstart[i] for i in isort]
        files = [files[i] for i in isort]
        
        # End time
        #   - Any files that start on or before END_DATE can be kept
        idx = [i for i, t in enumerate(fstart) if t <= end_date ]
        if len(idx) > 0:
            fstart = [fstart[i] for i in idx]
            files = [files[i] for i in idx]
        else:
            fstart = []
            files = []
        
        # Start time
        #   - Any file with TSTART <= START_DATE can potentially have data
        #     in our time interval of interest.
        #   - Assume the start time of one file marks the end time of the previous file.
        #   - With this, we look for the file that begins just prior to START_DATE and
        #     throw away any files that start before it.
#        idx = [i for i, t in enumerate(fstart) if t.date() < start_date.date()]
        idx = [i for i, t in enumerate(fstart) if t >= start_date]
        
        if (len(idx) == 0) & (fstart[-1].date() == start_date.date()):
            idx = [len(fstart)-1]
        elif (len(idx) != 0) & ((idx[0] != 0) & (fstart[idx[0]] != start_date)):
            idx.insert(0, idx[0]-1)
        
        if len(idx) > 0:
            fstart = [fstart[i] for i in idx]
            files = [files[i] for i in idx]
        else:
            fstart = []
            files = []
        
        outFiles += files
    
    return outFiles



def parse_filename(fnames):
    """
    Construct a file name compliant with MMS file name format guidelines.
    
    Arguments:
        fname (str,list): File names to be parsed.
    
    Returns:
        parts (list):     A list of tuples. The tuple elements are:
                          [0]: Spacecraft IDs
                          [1]: Instrument IDs
                          [2]: Data rate modes
                          [3]: Data levels
                          [4]: Optional descriptor (empty string if not present)
                          [5]: Start times
                          [6]: File version number
    """
    
    # Allocate space
    out = []
    
    if type(fnames) is str:
        files = [fnames]
    else:
        files = fnames
    
    # Parse each file
    for file in files:
        # Special handling if the file is ancillary data
        if 'ancillary' in file.split('/'):
            # Parse the file names
            basename,extension = os.path.splitext(os.path.basename(file))
            parts = basename.split('_')
            
            # Ancillary filename structure:
            #   [0]: 'mms' or spacecraft
            #   [1]: ancillary product (we'll return this as the Instrument ID)
            #   [2]: Start_date in '%Y%j' format (4-digit year, 3-digit day-of-year)
            #   [3]: End_date in '%Y%j' format (as above)
            #   [4]: Version
            
            version = extension[2:]
            start_date_parsed = dt.datetime.strptime(parts[2], '%Y%j')
            start_date = start_date_parsed.strftime('%Y%m%d')
            out.append((*parts[0:2], '', '', '', start_date, version))
            
        else:
            # Parse the file names
            parts = os.path.basename(file).split('_')
            
            if len(parts) == 6:
                optdesc = ''
            else:
                optdesc = parts[4]
                
            out.append((*parts[0:4], optdesc, parts[-2], parts[-1][1:-4]))
    
    return out

