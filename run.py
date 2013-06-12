import subprocess as s
import xmlrpclib as x
import threading
import numpy as np
import time as t

import gui, 


''' SEDM python is used for running the PI detectors '''
''' Enthought python is used for high-level control'''


epy = "c:/python27/python.exe"
sedmpy = "C:/Users/sedm/Dropbox/Python-3.3.0/PCbuild/amd64/python.exe"
st = "C:/program files/snaketail/snaketail.exe"
stage_pid = s.Popen([epy, "c:/sw/sedm/Stage.py"])
rc_pid = s.Popen([sedmpy, "c:/sw/sedm/camera.py", "-rc"])
ifu_pid = s.Popen([sedmpy, "c:/sw/sedm/camera.py", "-ifu"])

#

''' Tail '''

snake_stage_pid = s.Popen([st, "c:/sedm/logs/stage.txt"])
snake_rc_pid = s.Popen([st, "c:/sedm/logs/rc.txt"])
snake_rc_pid = s.Popen([st, "c:/sedm/logs/ifu.txt"])



stage_con = x.ServerProxy("http://127.0.0.1:8000")
rc_con = x.ServerProxy("http://127.0.0.1:8001")
ifu_con = x.ServerProxy("http://127.0.0.1:8002")


reload(gui)
gui.gui_connection(rc_con, 'rc')
ifu_gui = gui.gui_connection(ifu_con, 'ifu', stage_con)

def focus_loop():
    if not stage_con.is_ready():
        print "Stage requires homing"
        stage_con.home()
    
    files = []
    for pos in np.arange(3.2,3.9,.1):
        if not stage_con.moveto(float(pos)):
            print "stage hit limit"
            return
        print "Moved to %f" % pos
        ifu_gui.gain = 2
        ifu_gui.amp = 1
        ifu_gui.readout=2
        ifu_gui.shutter = 'normal'
        ifu_gui.exposure=1
        ifu_gui._go_button_fired()
        while ifu_gui.exposure_thread.isAlive():
            t.sleep(1)
        
        files.append(ifu_gui.filename)
    print files
    return files

def go_focus_loop():
    T=threading.Thread(target=focus_loop)
    T.start()
    