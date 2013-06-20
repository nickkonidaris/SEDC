import subprocess as s
import xmlrpclib as xmlrpclib
from multiprocessing import Process, Event
import Queue
from threading import Thread
import numpy as np
import time as t
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
stage_pid = s.Popen([epy, "c:/sw/sedm/Stage.py"])
rc_pid = s.Popen([sedmpy, "c:/sw/sedm/camera.py", "-rc"])
ifu_pid = s.Popen([sedmpy, "c:/sw/sedm/camera.py", "-ifu"])
[pids.append(x) for x in [stage_pid, rc_pid, ifu_pid]]
t.sleep(.5)

#

''' Tail '''
    
snake_stage_pid = s.Popen([st, "c:/sedm/logs/stage.txt"])
snake_rc_pid = s.Popen([st, "c:/sedm/logs/rc.txt"])
snake_ifu_pid = s.Popen([st, "c:/sedm/logs/ifu.txt"])
[pids.append(x) for x in [snake_stage_pid, snake_rc_pid, snake_ifu_pid]]


stage_con = xmlrpclib.ServerProxy("http://127.0.0.1:8000")
rc_con = xmlrpclib.ServerProxy("http://127.0.0.1:8001")
ifu_con = xmlrpclib.ServerProxy("http://127.0.0.1:8002")


tel_gui = Telescope.telescope_gui_connection()
t.sleep(.1)
ifu_gui = gui.gui_connection(ifu_con, 'ifu', tel_gui, stage_con )
t.sleep(.1)
rc_gui = gui.gui_connection(rc_con, 'rc', tel_gui)
t.sleep(.1)
ifu_gui = gui.gui_connection(ifu_con, 'ifu', tel_gui, stage_con)
t.sleep(.1)
rc_gui = gui.gui_connection(rc_con, 'rc', tel_gui)

stage= stage_gui.stage_gui_connection(stage_con)


def focus_loop():
    
    def waitfor():
        while not stage.is_ready:
            print "waiting.."
            t.sleep(1)
    
    print "Starting focus loop"
    stage.comms_thread.request_focus = True
    
    if not stage.is_ready:
        print "Stage not homed"
        return    
    files = []
    
    for pos in np.arange(3.2,3.6,.025):
        print "Moving to %f...." % pos
        stage.target = float(pos)
        stage._go_button_fired()
        t.sleep(3)
            
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
            ctypes.windll.kernel32.TerminateProcess(int(p._handle), -1)
    except NameError:
        pass
    
    stage.request_abort = True
    ifu_gui.request_abort = True
    rc_gui.request_abort = True
    t.sleep(1)
    
    try: stage_con.close()
    except: pass
    try: rc_con.close()
    except: pass
    try: ifu_con.close()
    except: pass



print "Open up two instances of DS9 and get xpa->information->xpa_method"
print "Then set: rc_gui.xpa_class = c6ca7de8:4412"