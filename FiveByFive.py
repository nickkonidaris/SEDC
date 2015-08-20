import xmlrpclib
import numpy as np
import pyfits as pf
import pylab as pl
import time as t
from threading import Thread
import GXN

abort_focus = False



def magic_func(delta=3):
    ''' [ (pos num, (dRA, dDec)), .... ] '''
    
    cnt = 0
    poss = []
    for i in xrange(5):
        for j in xrange(5):
            
            if cnt % 5 == 0 and cnt != 0:
                pos = (cnt, (-delta*4, delta))
            elif cnt == 0:
                pos = (cnt, (0,0))
            else:
                pos = (cnt, (delta, 0)) # (Left -> Right)                
                                
            cnt += 1            
            poss.append(pos)
            
    return poss     

def grid_loop(rc_control, ifu_control, delta=3):
    '''Take spectra in a 5x5 grid spaced by delta arcsec
    
    Args:
        rc_control: instance of camera control gui that controls rc
        ifu_control: instance of camera control gui that controls ifu.
        delta: throw amount in arcsec
    '''
    global abort_grid
    
    
    abort_grid = False
    positions = magic_func(delta)
    rc_name = rc_control.getall()[1] # 2nd element is object name
    if ifu_control is not None:
        ifu_name = ifu_control.getall()[1] # 2nd element is object name
                
    def expose():
        if abort_grid: return
        print "exposing"
        
        while rc_control.isExposing():
            t.sleep(0.2)

        while ifu_control.isExposing():
            t.sleep(0.2)
            
        ifu_control.go()
        rc_control.go()
        t.sleep(5)
        
        while not rc_control.isExposureComplete():
            t.sleep(0.2)
        

        while not ifu_control.isExposureComplete():
            t.sleep(0.2)
        
    def go_shift(pos):
        ''' Move pos[0] and pos[1] in arcsec '''
        print "to: ",  pos
        
        cmd = GXN.Commands()
        cmd.pt(*pos)


    def helper():
        global abort_grid
        
        # GO TO START

        for pos in positions:
            name, delta = pos
            if abort_grid: return
            go_shift(delta)
            rc_control.setobject("%s - Position %s" % (rc_name, name))
            ifu_control.setobject("%s - Position: %s" % (ifu_name, name))
            expose()
            
            
        while rc_control.isExposing():
            t.sleep(0.2)
        
        while ifu_control.isExposing():
            t.sleep(0.2)
            

        rc_control.setobject(rc_name)
        
        if ifu_control is not None:
            ifu_control.setobject(ifu_name)
    

    ifu_readout_speed = ifu_control.getall()[7]
    rc_readout_speed = rc_control.getall()[7]
    
    ifu_control.setreadout(2.0)
    rc_control.setreadout(2.0)
    
    T = Thread(target=helper)
    T.start()
    T.join()
    

    ifu_control.setreadout(ifu_readout_speed)
    rc_control.setreadout(rc_readout_speed)
    


if __name__ == '__main__':
    print magic_func()
