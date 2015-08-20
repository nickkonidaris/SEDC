import xmlrpclib
import numpy as np
import pyfits as pf
import pylab as pl
import time as t
from threading import Thread
import GXN

abort_focus = False
files = []

def focus_loop(rc_control, focus_pos = None, ifu_control=None):
    '''Perform a focus loop over positions via secondary mirror
    
    Args:
        rc_control-- instance of camera control gui that controls rc
        positions-- list of floats indicating positions to focus over. Default
            arange(14, 14.3, 0.06)
        ifu_control-- instance of camera control gui that controls ifu.
            Optional, default is not to simultaneously observe with ifu
    
    Returns:
        [files]-- List of full path to files that were created.
    '''
    global abort_focus, files, ifu_files
    
    rc_name = rc_control.getall()[1] # 2nd element is object name
    if ifu_control is not None:
        ifu_name = ifu_control.getall()[1] # 2nd element is object name
        
    if focus_pos is None:
        focus_pos = np.arange(14, 14.3, 0.06)
        
    def expose():
        if abort_focus: return
        print "exposing"
        
        while rc_control.isExposing():
            t.sleep(0.2)
        
        if ifu_control is not None:
            while ifu_control.isExposing():
                t.sleep(0.2)
            
            ifu_files.append(ifu_control.getfilename())
            ifu_control.go()
        
        files.append(rc_control.getfilename())
        
        rc_control.go()
        t.sleep(5)
        
        while not rc_control.isExposureComplete():
            t.sleep(0.2)
        
        if ifu_control is not None:
            while not ifu_control.isExposureComplete():
                t.sleep(0.2)
        
    def gof(pos_mm):
        print "to %s" % pos_mm
        cmd = GXN.Commands()
        cmd.gofocus(pos_mm)


    def helper():
        global abort_focus, files, ifu_files
        print "focusing at: ", focus_pos
        gof(13)
        files = []
        ifu_files = []
        for pos in focus_pos:  
            if abort_focus: return
            print pos
            gof(pos)
            rc_control.setobject("%s - Focus: %s" % (rc_name,pos))
            if ifu_control is not None: 
                ifu_control.setobject("%s - Focus: %s" % (ifu_name,pos))
            expose()
            
            
        while rc_control.isExposing():
            t.sleep(0.2)
        
        files.append(rc_control.getfilename())
        
        if ifu_control is not None:
            while ifu_control.isExposing():
                t.sleep(0.2)
            
            ifu_files.append(ifu_control.getfilename())
        
        gof(13)
        rc_control.setobject(rc_name)
        
        if ifu_control is not None:
            ifu_control.setobject(ifu_name)
    
    if ifu_control is not None:
        ifu_readout_speed = ifu_control.getall()[7]
    rc_readout_speed = rc_control.getall()[7]
    ifu_control.setreadout(2.0)
    rc_control.setreadout(2.0)
    
    T = Thread(target=helper)
    T.start()
    T.join()
    
    if ifu_control is not None:
        ifu_control.setreadout(ifu_readout_speed)
    rc_control.setreadout(rc_readout_speed)
    
    if ifu_control is None:
        return files[1:]
    
    return files[1:], ifu_files[1:]
    


abort_4 = False	

def analyze(files, xslice=slice(1200,1600), yslice=slice(1200,1800)):
    pl.ion()
    
    fpos = []
    res = []
    pl.figure(1)
    for fname in files:
        FF = pf.open(fname)
        im = FF[0].data[xslice, yslice]
        
        try:
            print FF[0].header['object']
            pos= FF[0].header['object'].split(":")[-1]
            print pos
            fpos.append(float(pos))
            res.append(np.max(im) - np.min(im))
        except KeyError:
            continue
    
    pl.figure(1)
    pl.clf()
    pl.plot(fpos,res,'o')
    pl.title("RC Focus")
    pl.show()
    
    
    
