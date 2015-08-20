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
    throw_distancex = -7, throw_distancey = 0):
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
        2-tuple of list- (list IFU file names, list RC file names)
            
    Results:
        Moves telescope according to dither pattern.
        
    Todo:
        Parameterize throw distance 
    '''
    
    
    if positions == 'ABCD':
        nods = [( 0, 0),
                ( 0, throw_distance),
                ( throw_distance, 0),
                ( 0,-throw_distance),
                ( -throw_distance, 0)]
    elif positions == 'AB':
        nods = [( 0, 0),
                ( throw_distancex,  throw_distancey),
                (-throw_distancex,  -throw_distancey)]
    else:
        nods = [(0,0)]
    
    n_rc_exp = int(exp_time / 33)
    if n_rc_exp == 0: n_rc_exp = 1
    rc_files = []
    ifu_files = []
    
    print nods
    def expose(position):
        '''
        expose-- Helps with nod exposure

        1) Checks if there is an ongoing exposure. 
         If there is an ongoing exposure, waits until its complete.
        2) If there was an ongoing exposure, record file name
        '''
        if abort_nod: return
        

        while (rc_control.isExposing()) or (ifu_control.isExposing()):
            t.sleep(1)
        
        rc_control.setnumexposures(n_rc_exp)
        rc_control.setexposure(30)
        ifu_control.setexposure(exp_time)
        ifu_control.setnumexposures(1)
        

        print "Exposures beginning"
        ifu_control.go() ; rc_control.go()
        
        print "Wait"
        while (not rc_control.isExposureComplete()) or ifu_control.isExposing():
            t.sleep(1)

        rc_files.append((rc_control.getfilename(), position))
        ifu_files.append((ifu_control.getfilename(), position))
        
    def helper():
        gxn_cmd = GXN.Commands()
        for i in xrange(len(positions)):
            position = positions[i]
            nod = nods[i]
            
            print "Handling %s @ %s" % (position, nod)
            gxn_cmd.pt(*nod)
            t.sleep(5)
                                
            ifu_control.setobject("%s [%s]" % (target_name, position))
            rc_control.setobject("%s [%s]" % (target_name, position))
            expose(position)

        gxn_cmd.pt(*nods[-1])
        
        ifu_control.setobject("%s" % target_name)
        rc_control.setobject("%s" % target_name)
        
        print "Wait for end"
        while rc_control.isExposing() or ifu_control.isExposing():
            t.sleep(0.5)

        rcf = rc_control.getfilename()
        ifuf = ifu_control.getfilename()
        if rcf != rc_files[-1][0]: rc_files.append((rcf,position))
        if ifuf != ifu_files[-1][0]: ifu_files.append((ifuf,position))



    ifu_readout_speed = ifu_control.getall()[7]
    ifu_exptime = ifu_control.getall()[10]
    
    if exp_time >= 61: ifu_control.setreadout(0.1)
    if exp_time < 61: ifu_control.setreadout(2.0)
    
    T = Thread(target=helper)
    T.start()
    T.join()
    
    ifu_control.setreadout(ifu_readout_speed)
    
    print "Finished"
    return (ifu_files, rc_files)


    
