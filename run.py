import subprocess as s
import xmlrpclib as x
import threading as t



''' SEDM python is used for running the PI detectors '''
''' Enthought python is used for high-level control'''


epy = "c:/python27/python.exe"
sedmpy = "C:/Users/sedm/Dropbox/Python-3.3.0/PCbuild/amd64/python.exe"
st = "C:/program files/snaketail/snaketail.exe"
#stage_pid = s.Popen([epy, "c:/sw/sedm/Stage.py"])
rc_pid = s.Popen([sedmpy, "c:/sw/sedm/camera.py", "-rc"])
rc_pid = s.Popen([sedmpy, "c:/sw/sedm/camera.py", "-ifu"])



''' Tail '''

#snake_stage_pid = s.Popen([st, "c:/sedm/logs/stage.txt"])
snake_rc_pid = s.Popen([st, "c:/sedm/logs/rc.txt"])
snake_rc_pid = s.Popen([st, "c:/sedm/logs/ifu.txt"])




c = x.ServerProxy("http://127.0.0.1:8001")

import Queue
q = Queue.Queue()

def take_img():
    q.put(c.acquire())