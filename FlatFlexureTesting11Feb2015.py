import GXN
import Options

import time
import xmlrpclib
import numpy as np


cmds = GXN.Commands()
ifu_control = xmlrpclib.ServerProxy("http://127.0.0.1:%i" % Options.ifu_port)


def do(ha, dec):
    cmd = "stow %s %s 90\n" % (ha, dec)

    print cmd
    T = cmds.write(cmd, slow=True)
    cmds.slow(300, T)
    
    ifu_control.setnumexposures(1)
    ifu_control.setobject("Flex: dome %s %s" % (ha, dec))
    ifu_control.setshutter("normal")
    ifu_control.setexposure(60)
    ifu_control.setreadout(2)
    ifu_control.go()
    
    while ifu_control.isExposing():
        time.sleep(1)
    
HAs = np.arange(4,-4,-1)
Decs = [15]

ha = 0
dec = 40

do(0, 40)


for dec in Decs:
    for HA in HAs:
       do(HA, dec)
    