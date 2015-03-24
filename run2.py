


'''

This file is essentially a shell script that opens a variety of servers
and connects the servers together

[c] 2014 Nick Konidaris
nick.konidaris@gmail.com

'''
import logging
logger = logging.getLogger("SEDMControl")
logging.basicConfig(level=logging.INFO,
    filename="s:/logs/obslog.txt",
    filemode="a",
    format = "%(message)s    [%(asctime)-15s] %(name)s")
import subprocess as s
import xmlrpclib

import time as t
import GXN

import Focus
import Fourshot
import Secfocus
import Util

import Options
import gui, stage_gui, Telescope_server

reload(Telescope_server)
reload(gui)
reload(stage_gui)
reload(Focus)
reload(Secfocus)

logger = logging.getLogger("SEDMControl")
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
sedm_control_pid = s.Popen([epy, "c:/sw/sedm/SEDMControl.py"])

pids.append(rc_gui_pid)
pids.append(ifu_gui_pid)
pids.append(offset_gui_pid)
pids.append(tel_pid)
pids.append(stage_gui_pid)
pids.append(sedm_control_pid)
t.sleep(20)

rc_control = xmlrpclib.ServerProxy("http://127.0.0.1:%i" % Options.rc_port)
ifu_control = xmlrpclib.ServerProxy("http://127.0.0.1:%i" % Options.ifu_port)
tel_control = xmlrpclib.ServerProxy("http://127.0.0.1:%i" % Options.tel_port)
stage_control = xmlrpclib.ServerProxy(Util.stage_server_address)


rc_control.show()
ifu_control.show()
tel_control.show()
stage_control.show()

def focus_loop():
    SpecFocus.focus_loop(stage_control, ifu_control)

def secfocus(positions=None):
    Secfocus.secfocus(rc_control, positions)

def fourshot(ets = None):
    Fourshot.fourshot(rc_control, ets)



