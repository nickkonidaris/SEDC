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
import Util

import gui, stage_gui, Telescope_server

reload(Telescope_server)
reload(gui)
reload(stage_gui)
reload(Focus)

use_stage = True

pids = []


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
stage_control = xmlrpclib.ServerProxy("http://127.0.0.1:9004")

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
    
    for pos in np.arange(3.3,4.1,.05):
        print "Moving to %f...." % pos
        stage_control.set_target(float(pos))
        stage_control.go()
        t.sleep(10)

        waitfor()

        print "..Moved to %f" % pos
        ifu_control.setreadout(2)
        ifu_control.setshutter('normal')
        ifu_control.setexposure(25)
        ifu_control.go()

        while ifu_control.isExposing():
            t.sleep(0.2)
        
        files.append(ifu_control.getfilename())
        
    stage_control.request_focus(False)
    print files
    
def go_focus_loop():
    T = Thread(target=focus_loop)
    T.start()


abort_focus = False
def secfocus(positions = None):
    
    def expose():
        if abort_focus: return
        print "exposing"
        
        while rc_control.isExposing():
            t.sleep(0.2)
        
        rc_gui.go()
        t.sleep(1)
        
    def gof(pos_mm):
        print "to %s" % pos_mm
        GXN.gofocus(pos_mm)
    
    if positions is None:
        positions = np.arange(13.8, 15, 0.15)

    def helper():
        print "focusing at: ", positions
        gof(13)
        for pos in positions:  
            if abort_focus: return
            print pos
            gof(pos)
            expose()

        gof(13)
    Thread(target=helper).start()

abort_4 = False

def fourshot(ets = None):
    
    if ets == None:
        it = rc_gui.exposure
        ets = [it] * 4
        
    def expose(time):
        if abort_4: return
        rc_control.setexposure(time)
        
        
        print "exposing"
        while rc_control.isExposing():
            t.sleep(0.2)

        rc_control.go()
        
        while rc_control.isExposureComplete():
            t.sleep(0.2)

        
    def helper():
        
        to_move = np.array([180, 180])
        
        if ets[0] != 0:
            print "move to r"
            GXN.pt(*to_move)
            to_move = np.array([0,0])
            expose(ets[0])
        
        to_move += np.array([-360,0])
        if ets[1] != 0:
            print "move to i"
            GXN.pt(*to_move)
            to_move = np.array([0,0])
            expose(ets[1])
        
        to_move += np.array(0,-360)
        if ets[2] != 0:            
            print "move to g"
            GXN.pt(*to_move)
            to_move = np.array([0,0])
            expose(ets[2])
        
        to_move += np.array([360,0])
        if ets[3] != 0:
            print "move to u"
            GXN.pt(*to_move)
            to_move = np.array([0,0])
            expose(ets[3])
    
    Thread(target=helper).start()


def AB(n_times):
        
    import telnetlib
    T = telnetlib.Telnet("pele.palomar.caltech.edu", 49300)
    T.write("takecontrol\n")
    print T.read_until("\n", .1)

    def moveto(cmd):
        #if abort_4: return
        
        print cmd
        T.write(cmd)
        r = T.expect(["-?\d"], 15)[2]
        print "returned: %s" % r
        
        try: res = int(r)
        except: res = 0
        
        if res != 0: 
            print "Bad retcode in move: %s --> %i" % (cmd, r)
            raise Exception("bad")        

        t.sleep(6)
        
        while (tel_gui.Status != 'TRACKING') and (abort_4 == False):
            #print "'%s'" % tel_gui.Status
            t.sleep(.5)
        
    def expose():
        if abort_4: return
        print "exposing"
        rc_gui.num_exposures = 5
        rc_gui.exposure = 60
        ifu_gui.exposure = 300
        
        rc_gui._go_button_fired()
        ifu_gui._go_button_fired()
        
        t.sleep(5)
        
        while (rc_gui.state != 'Idle') or (ifu_gui.state != 'Idle'):
            t.sleep(1.5)

        
    def helper():
        
        obj_ifu = ifu_gui.object
        obj_rc = ifu_gui.object
        
        while n_times > 0:
            ifu_gui.object = "%s [A]" % obj_ifu
            rc_gui.object = "%s [A]" % obj_rc
            expose()
            moveto("pt 0 5\n")        
            ifu_gui.object = "%s [B]" % obj_ifu
            rc_gui.object = "%s [B]" % obj_rc
            expose() 
            moveto("pt 0 -5\n")  
            n_times -= 1
        
        ifu_gui.object = "%s" % obj_ifu
        rc_gui.object = "%s" % obj_rc

    
    Thread(target=helper).start()


