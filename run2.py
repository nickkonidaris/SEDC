import subprocess as s
import xmlrpclib
from multiprocessing import Process, Event
import Queue
from threading import Thread
import numpy as np
import time as t
import sched
import math
import GXN

import Focus
import Fourshot
import Secfocus
import Util

import gui, stage_gui, Telescope_server

reload(Telescope_server)
reload(gui)
reload(stage_gui)
reload(Focus)
reload(Secfocus)

use_stage = True

pids = []

c = GXN.Commands()
###
###   STARTUP
###

''' SEDM python is used for running the PI detectors '''
''' Enthought python is used for high-level control'''
epy = Util.epy
sedmpy = Util.sedmpy

tel_pid = s.Popen([epy, "c:/sw/sedm/Telescope_server.py"])
rc_gui_pid = s.Popen([epy, "c:/sw/sedm/camera_control_gui.py", "-rc"])
ifu_gui_pid = s.Popen([epy, "c:/sw/sedm/camera_control_gui.py", "-ifu"])
offset_gui_pid = s.Popen([epy, "c:/sw/sedm/Offsets.py"])
stage_gui_pid = s.Popen([epy, "c:/sw/sedm/stage_server.py"])
pids.append(rc_gui_pid)
pids.append(ifu_gui_pid)
pids.append(offset_gui_pid)
pids.append(tel_pid)
pids.append(stage_gui_pid)
t.sleep(12)

rc_control = xmlrpclib.ServerProxy("http://127.0.0.1:9001")
ifu_control = xmlrpclib.ServerProxy("http://127.0.0.1:9002")
tel_control = xmlrpclib.ServerProxy("http://127.0.0.1:9003")
stage_control = xmlrpclib.ServerProxy(Util.stage_server_address)

rc_control.show()
ifu_control.show()
tel_control.show()
stage_control.show()


def focus_loop():
    
    def waitfor():
        t.sleep(3)
        while not stage_control.get_is_ready():
            t.sleep(.2)
    
    print "Starting focus loop"
    stage_control.request_focus(True)

    
    if not stage_control.get_is_ready():
        print "Stage not homed"
        return    
    files = []
    
    for pos in np.arange(3.4,3.8,.1):
        print "Moving to %f...." % pos
        stage_control.set_target(float(pos))
        stage_control.go()
        t.sleep(10)

        waitfor()
#
        print "..Moved to %f" % pos
        ifu_control.setreadout(2)
        ifu_control.setshutter('normal')
        ifu_control.setexposure(15)
        ifu_control.go()

        while ifu_control.isExposing():
            t.sleep(0.2)
        
        files.append(ifu_control.getfilename())
        
    stage_control.request_focus(False)
    print files
    
def go_focus_loop():
    T = Thread(target=focus_loop)
    T.start()

def secfocus(positions=None):
    Secfocus.secfocus(rc_control, positions)

def fourshot(ets = None):
    Fourshot.fourshot(rc_control, ets)


abort_abcd = False
def ABCD():
    global abort_abcd    
    def expose():
        global abort_abcd
        if abort_abcd: return
        
        while (rc_control.isExposing()) or (ifu_control.isExposing()):
            t.sleep(0.5)
            
        rc_control.setnumexposures(5)
        rc_control.setexposure(60)
        ifu_control.setnumexposures(1)
        ifu_control.setexposure(300)
        ifu_control.setreadout(2.0)
        
        rc_control.go()
        ifu_control.go()
        
        t.sleep(5)
        
        while (not rc_control.isExposureComplete()) or (not 
            ifu_control.isExposureComplete()):
            t.sleep(0.5)
            
            
    def helper():
        obj_ifu = ifu_control.getall()[1]
        obj_rc = rc_control.getall()[1]
        cmds = GXN.Commands()
        
        # A
        ifu_control.setobject("%s [A]" % obj_ifu)
        rc_control.setobject("%s [A]" % obj_rc)
        expose()
        cmds.pt(0,-5)

        # B
        ifu_control.setobject("%s [B]" % obj_ifu)
        rc_control.setobject("%s [B]" % obj_rc)
        expose() 
        cmds.pt(5, 0)
        
        # C
        ifu_control.setobject("%s [C]" % obj_ifu)
        rc_control.setobject("%s [C]" % obj_rc)
        expose()
        cmds.pt(0,5)

        # D
        ifu_control.setobject("%s [D]" % obj_ifu)
        rc_control.setobject("%s [D]" % obj_rc)
        expose() 
        cmds.pt(-5, 0)
        
        ifu_control.setobject("%s" % obj_ifu)
        rc_control.setobject("%s" % obj_rc)

    
    Thread(target=helper).start()



def AB(n_times):
        
    def expose():
        if abort_4: return
        
        while (rc_control.isExposing()) or (ifu_control.isExposing()):
            t.sleep(0.5)
            
        rc_gui.num_exposures = 10
        rc_gui.setexposure(60)
        ifu_control.setexposure(600)
        
        rc_control.go()
        ifu_control.go()
        
        t.sleep(5)
        
        while (not rc_control.isExposureComplete()) or (not 
            ifu_control.isExposureComplete()):
            t.sleep(0.5)

        
    def helper():
        
        obj_ifu = ifu_gui.object
        obj_rc = ifu_gui.object
        
        while n_times > 0:
            ifu_gui.object = "%s [A]" % obj_ifu
            rc_gui.object = "%s [A]" % obj_rc
            expose()
            GXN.pt(0,5)

            ifu_gui.object = "%s [B]" % obj_ifu
            rc_gui.object = "%s [B]" % obj_rc
            expose() 
            GXN.pt(0, -5)
            n_times -= 1
        
        ifu_gui.object = "%s" % obj_ifu
        rc_gui.object = "%s" % obj_rc

    
    Thread(target=helper).start()


