import xmlrpclib
import numpy as np
import pyfits as pf
import pylab as pl
import time as t
from threading import Thread
import GXN

abort_focus = False
files = []

def secfocus(rc_control, positions = None):
    global abort_focus, files
    
    if positions is None:
        positions = np.arange(14, 14.3, 0.06)
        
    def expose():
        if abort_focus: return
        print "exposing"
        
        while rc_control.isExposing():
            t.sleep(0.2)
        
        files.append(rc_control.getfilename())
        
        rc_control.go()
        t.sleep(5)
        
        while not rc_control.isExposureComplete():
            t.sleep(0.2)
        
    def gof(pos_mm):
        print "to %s" % pos_mm
        cmd = GXN.Commands()
        cmd.gofocus(pos_mm)


    def helper():
        global abort_focus, files
        print "focusing at: ", positions
        gof(13)
        files = []
        for pos in positions:  
            if abort_focus: return
            print pos
            gof(pos)
            rc_control.setobject("Focus: %s" % pos)
            expose()
            
            
        while rc_control.isExposing():
            t.sleep(0.2)
    
        gof(13)
        rc_control.setobject("")
    
    rc_control.setexposure(10.)    
    T = Thread(target=helper)
    T.start()

abort_4 = False

def analyze():
    global files
    
    fpos = []
    res = []
    pl.figure(1)
    for fname in files:
        FF = pf.open(fname)
        im = FF[0].data[1300:1600 , 1400:1800]
        
        pl.figure()
        pl.imshow(im)
        fpos.append(FF[0].header['secfocus'])
        res.append(np.max(im) - np.min(im))
    
    pl.figure(1)
    pl.clf()
    pl.plot(fpos,res,'o')
        
        
    
    
    