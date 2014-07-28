import xmlrpclib
import numpy as np
import pyfits as pf
import pylab as pl
import time as t
from threading import Thread
import GXN

abort_4 = False

def fourshot(rc_control, ets = None):
    global abort_4
    
    if ets is None:
        itime = rc_control.getall()[-1]
        ets = [itime] * 4
        
    def expose(time):
        if abort_4: return
        rc_control.setexposure(time)
        
        
        print "exposing"
        while rc_control.isExposing():
            t.sleep(0.2)

        rc_control.go()
        t.sleep(5)
        
        while not rc_control.isExposureComplete():
            t.sleep(0.2)

        
    def helper():
        
        files = []
        
        cmds = GXN.Commands()
        to_move = np.array([180, 180])
        accu = -to_move[:] # accumulated move
        name = rc_control.getall()[1]
        if ets[0] != 0:
            print "move to r"
            cmds.pt(*to_move)
            accu += to_move
            t.sleep(1)
            to_move = np.array([0,0])
            rc_control.setobject("[r] %s" % name)
            files.append("[r]: %s" % rc_control.getfilename())
            expose(ets[0])
        
        to_move += np.array([-360,0])
        if ets[1] != 0:
            print "move to i"
            cmds.pt(*to_move)
            accu += to_move
            t.sleep(1)
            to_move = np.array([0,0])
            rc_control.setobject("[i] %s" % name)
            files.append("[i] %s" % rc_control.getfilename())
            expose(ets[1])
        
        to_move += np.array([0,-360])
        if ets[2] != 0:            
            print "move to g"
            cmds.pt(*to_move)
            accu += to_move
            t.sleep(1)
            to_move = np.array([0,0])
            rc_control.setobject("[g] %s" % name)
            files.append("[g] %s" % rc_control.getfilename())
            expose(ets[2])
        
        to_move += np.array([360,0])
        if ets[3] != 0:
            print "move to u"
            cmds.pt(*to_move)
            accu += to_move
            t.sleep(1)
            to_move = np.array([0,0])
            rc_control.setobject("[u] %s" % name)
            files.append("[u] %s" % rc_control.getfilename())
            expose(ets[3])
            
        rc_control.setobject("%s" % name)
        return files
    
    t= Thread(target=helper)
    t.start()
    return t.join()
    
