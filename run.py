import subprocess as s
import xmlrpclib as xmlrpclib
from multiprocessing import Process, Event
import Queue
from threading import Thread
import numpy as np
import time as t
import sched
import math

import Focus

import gui, stage_gui, Telescope

reload(Telescope)
reload(gui)
reload(stage_gui)
reload(Focus)

pids = []

''' SEDM python is used for running the PI detectors '''
''' Enthought python is used for high-level control'''


epy = "c:/python27/python.exe"
sedmpy = "C:/Users/sedm/Dropbox/Python-3.3.0/PCbuild/amd64/python.exe"
st = "C:/program files/snaketail/snaketail.exe"
stage_pid = 0
#stage_pid = s.Popen([epy, "c:/sw/sedm/Stage.py"])

rc_pid = s.Popen([sedmpy, "c:/sw/sedm/camera.py", "-rc"])
ifu_pid = s.Popen([sedmpy, "c:/sw/sedm/camera.py", "-ifu"])
[pids.append(x) for x in [stage_pid, rc_pid, ifu_pid]]
t.sleep(.5)

#

''' Tail '''
    
snake_stage_pid  = 0
#snake_stage_pid = s.Popen([st, "c:/sedm/logs/stage.txt"])
#snake_rc_pid = s.Popen([st, "c:/sedm/logs/rc.txt"])
#snake_ifu_pid = s.Popen([st, "c:/sedm/logs/ifu.txt"])
#[pids.append(x) for x in [snake_stage_pid, snake_rc_pid, snake_ifu_pid]]

stage_con = None
#stage_con = xmlrpclib.ServerProxy("http://127.0.0.1:8000")
rc_con = xmlrpclib.ServerProxy("http://127.0.0.1:8001")
ifu_con = xmlrpclib.ServerProxy("http://127.0.0.1:8002")

t.sleep(2)

tel_gui = Telescope.telescope_gui_connection()
#target_gui = Telescope.target_gui_connection()



ifu_gui, ifu_view = gui.gui_connection(ifu_con, 'ifu', tel_gui, stage_connection=stage_con)
rc_gui, rc_view = gui.gui_connection(rc_con, 'rc', tel_gui)


ifu_gui.configure_traits(view=ifu_view)
rc_gui.configure_traits(view=rc_view)
ifu_gui._shutter_changed()
ifu_gui.update_settings()
rc_gui._shutter_changed()
rc_gui.update_settings()


#stage= stage_gui.stage_gui_connection(stage_con)


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
        ifu_gui.exposure= 15
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
        if abort_4: return
        
        T.write(cmd)
        r = T.read_until("\n", .1).rstrip()
        print "returned: %s" % r
        
        try: res = int(r)
        except: 
            res = 0
        
        if res != 0: 
            print "Bad retcode in move: %s --> %i" % (cmd, r)
            raise Exception("bad")        

        t.sleep(4)
        
        while (tel_gui.Status != 'TRACKING') and (abort_4 == False):
            print "'%s'" % tel_gui.Status
            t.sleep(1)
        
    def expose(time):
        if abort_4: return
        rc_gui.exposure = time
        print "exposing"
        rc_gui._go_button_fired()
        t.sleep(1)
        
        while rc_gui.state != 'Idle': t.sleep(.5)
        
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
fourshot()



print "Open up two instances of DS9 and get xpa->information->xpa_method"
print "Then set: rc_gui.xpa_class = METHOD NAME"
print "Then set: ifu_gui.xpa_class = METHOD NAME"