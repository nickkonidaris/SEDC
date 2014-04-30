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

import gui, stage_gui, Telescope

reload(Telescope)
reload(gui)
reload(stage_gui)
reload(Focus)

use_stage = True

pids = []

''' SEDM python is used for running the PI detectors '''
''' Enthought python is used for high-level control'''


epy = "c:/users/sedm/appdata/local/enthought/canopy/user/scripts/python.exe"
sedmpy = "C:/Users/sedm/Dropbox/Python-3.3.0/PCbuild/amd64/python.exe"
st = "C:/program files/snaketail/snaketail.exe"



if use_stage: stage_pid = s.Popen([epy, "c:/sw/sedm/Stage.py"])
else: stage_pid = 0

pids.append(stage_pid)
#
#rc_pid = s.Popen([sedmpy, "c:/sw/sedm/camera.py", "-rc"])
#ifu_pid = s.Popen([sedmpy, "c:/sw/sedm/camera.py", "-ifu"])
#[pids.append(x) for x in [stage_pid, rc_pid, ifu_pid]]
t.sleep(.5)

#


if use_stage: stage_con = xmlrpclib.ServerProxy("http://127.0.0.1:8000")
else: stage_con = None

#tel_gui = Telescope.telescope_gui_connection()
tel_gui = None
#target_gui = Telescope.target_gui_connection()



rc_gui_pid = s.Popen([epy, "c:/sw/sedm/camera_control_gui.py", "-rc"])
ifu_gui_pid = s.Popen([epy, "c:/sw/sedm/camera_control_gui.py", "-ifu"])
t.sleep(10)


pids.append(rc_gui_pid)
pids.append(ifu_gui_pid)

rc_control = xmlrpclib.ServerProxy("http://127.0.0.1:9001")
ifu_control = xmlrpclib.ServerProxy("http://127.0.0.1:9002")

rc_control.show()
ifu_control.show()

if use_stage: stage = stage_gui.stage_gui_connection(stage_con)
else: state = None


def focus_loop():
    
    def waitfor():
        t.sleep(3)
        while not stage.is_ready:
            print "waiting.."
            t.sleep(1)
    
    print "Starting focus loop"
    stage.comms_thread.request_focus = True
    
    if not stage.is_ready:
        print "Stage not homed"
        return    
    files = []
    
    for pos in np.arange(3.0,3.6,.05):
        print "Moving to %f...." % pos
        stage.target = float(pos)
        stage._go_button_fired()
        t.sleep(.2)
        T = Thread(target=waitfor)
        T.start()
        T.join()

        print "..Moved to %f" % pos
        ifu_gui.gain = 2
        ifu_gui.amp = 1
        ifu_gui.readout=2
        ifu_gui.shutter = 'normal'
        ifu_gui.exposure= 25
        ifu_gui._go_button_fired()
        while ifu_gui.exposure_thread.isAlive():
            t.sleep(1)
        
        files.append(ifu_gui.filename)
    stage.comms_thread.request_focus = False
    print files
    
def go_focus_loop():
    T = Thread(target=focus_loop)
    T.start()


def killall():
    import ctypes
 
    try:
        for p in pids:
            try: ctypes.windll.kernel32.TerminateProcess(int(p._handle), -1)
            except: pass
    except NameError:
        pass
    
    try:
        stage.request_abort = True
        ifu_gui.request_abort = True
        rc_gui.request_abort = True
    except: pass

    
    try: stage_con.close()
    except: pass
    try: rc_con.close()
    except: pass
    try: ifu_con.close()
    except: pass

abort_focus = False
def secfocus(positions = None):
    import telnetlib
    T = telnetlib.Telnet("pele.palomar.caltech.edu", 49300)
    T.write("takecontrol\n")
    print T.read_until("\n", .1)
    
    def expose():
        if abort_focus: return
        print "exposing"
        
        while rc_gui.state != 'Idle': t.sleep(0.1)
        
        rc_gui._go_button_fired()
        t.sleep(1)
        #while rc_gui.state != 'Idle': t.sleep(0.1)

        
        # FIXME: Once headers are stored before exposure begins 
        # this should be uncommented.
        while rc_gui.int_time < (rc_gui.exposure + 2):
            t.sleep(0.5)
        
    def gof(pos_mm):
        print "to %s" % pos_mm
        T.write("gofocus %s\n" % pos_mm)
        res=T.read_until("0", 10)
        if res != '0': 
            abort_focus = True
            return
    
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
        
    def expose(time):
        if abort_4: return
        rc_gui.exposure = time
        print "exposing"
        rc_gui._go_button_fired()
        t.sleep(1)
        
        while rc_gui.int_time < (rc_gui.exposure + 3):
            t.sleep(0.5)

        
    def helper():
        
        print "move to r"
        moveto("pt 180 180\n")        
        expose(ets[0])    
        print "move to i"
        moveto("pt -360 0\n")        
        expose(ets[1])
        print "move to g"
        
        moveto("pt 0 -360\n")        
        expose(ets[2])
        print "move to u"
        moveto("pt 360 0\n")        
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


