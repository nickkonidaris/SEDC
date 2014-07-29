'''

    Nodder.py -- SED Machine Nodding code
    
    Coordinates control of nods with RC and IFU exposures
    
    TODO: Include guider
'''

import xmlrpclib
import numpy as np
import pyfits as pf
import pylab as pl
import time as t
from threading import Thread
import GXN
from collections import namedtuple

abort_nod = False
files = []

def nodder(target_name, rc_control, ifu_control, exp_time, positions = None,
    throw_distance = 5):
    global abort_nod, rc_files, ifu_files
    
    ''' nodder -> [filenames]
    nods the telescope takes ifu and rc images simultaneously according to the
    dither pattern.
    
    Args:
        target_name -- name of target
        rc_control -- camera_control_gui instance controlling RC
        ifu_control -- camera_control_gui instance controlling IFU
        exp_time -- exposure time in sec
        positions -- dither pattern string. Either: ABCD, AB, or A
        throw_distance -- amount to nod in arcsec
    
    Returns:
        obsfile -- named tuple of obsfiles with list of files for
            RC (in .rc) or IFU (in .ifu)
            
    Results:
        Moves telescope according to dither pattern.
        
    Todo:
        Parameterize throw distance 
    '''
    
    
    if positions == 'ABCD':
        nods = [( 0, 0),
                ( 0, throw_distance),
                (-throw_distance, 0)
                ( 0,-throw_distance),
                ( throw_distance, 0)]
    elif positions == 'AB':
        nods = [( 0, 0),
                ( 0, throw_distance),
                ( 0, -throw_distance)]
    else:
        nods = [(0,0)]
    
    n_rc_exp = int(exp_time / 60)
    rc_files = []
    ifu_files = []
    
    def expose(position):
        '''
        expose-- Helps with nod exposure

        1) Checks if there is an ongoing exposure. 
         If there is an ongoing exposure, waits until its complete.
        2) If there was an ongoing exposure, record file name
        '''
        if abort_nod: return
        
        record_file = False
        while (rc_control.isExposing()) or (ifu_control.isExposing()):
            record_file=True
            t.sleep(0.5)
            
        if record_file:
            rc_files.append((rc_control.getfilename(), position))
            ifu_files.append((ifu_control.getfilename(), position))
        
        rc_gui.num_exposures = n_rc_exp
        rc_gui.setexposure(60)
        ifu_control.setexposure(exp_time)
        
        rc_control.go()
        ifu_control.go()
        
        t.sleep(5)
        
        while (not rc_control.isExposureComplete()) or (not 
            ifu_control.isExposureComplete()):
            t.sleep(0.5)

        
    def helper():
        
        for i in xrange(len(positions)):
            position = positions[i]
            nod = nods[i]

            gxn_cmd.pt(*position)
                                
            ifu_gui.object = "%s [%s]" % (target_name, position)
            rc_gui.object = "%s [%s]" % (target_name, position)
            expose()

        gxn_cmd.pt(*positions[-1])
        
        ifu_gui.object = "%s" % target_name
        rc_gui.object = "%s" % target_name
        
        obsfiles = namedtuple("obsfiles", (ifu, rc))
        
        return obsfiles(ifu=ifu_files, rc=rc_files)

    
    T = Thread(target=helper)
    T.start()
    return T.join()


    