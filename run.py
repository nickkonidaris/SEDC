import subprocess as s



''' SEDM python is used for running the PI detectors '''
''' Enthought python is used for high-level control'''

epy = "c:/python27/python.exe"
sedmpy = "C:/Users/sedm/Dropbox/Python-3.3.0/PCbuild/amd64/python.exe"
st = "C:/program files/snaketail/snaketail.exe
stage_pid = s.Popen([epy, "c:/sw/sedm/Stage.py"])
#rc_pid = s.Popen(["sedmpy", "c:/sw/sedm/camera.py", "/ifu"])



