import sys


if sys.version_info[0] == 2:
    print("You are running the wrong version of python. This code runs under the SEDM python distribution")
    sys.exit()
    
import pypicam as cam
import logging as log
import subprocess as s
import os
import time

MEDIUM_GAIN = 2
LOW_RN_AMP = 1
FAST_READOUT = 2

from xmlrpc.server import SimpleXMLRPCServer

class PIXIS:
    c = None
    serial_num = b"04001312"
    name = "RC"
    
    def __init__(self, serial_num, name):
        
        self.serial_num = serial_num
        self.name = name
        
        ls = cam.list()
        if len(ls) == 0:
            raise Exception("Did not find two cameras")
        
        for l in ls:
            if l["serialno"] == serial_num:
                log.info("Opening {}".format(name))
                self.c = cam.open(l)
        
        if self.c is None:
            raise Exception("Could not find {} Camera [serial #{}]".
                format(name,serial_num))
            
    
    def set(self, setpoints):
        ''' Setpoints is: exptime, gain, amplifier, readout speed Mhz '''
        log.info("Setting")
        cam.set(self.c["handle"], *setpoints)

            
    def set_shutter(self, type):
        log.info("{} Shutter setting to {} mode".format(self.name, type))
        val = {'normal': 1,
                'closed': 2,
                'open': 3}[type]
        
        cam.set_shutter(self.c["handle"], val)
            
    def acquire(self):
        log.info("Begin {} acquisition".format(self.name))
        path = cam.acquire(self.c, self.name)
        log.info("Saved image at {}".format(path))
        return path

print(sys.argv)
if __name__ == "__main__":

    if sys.argv[1] == "-rc":
        name = "rc"
        serial_num =  b"04001312"
    elif sys.argv[1] == '-ifu':
        name = "ifu"
        serial_num = b"2803120001"
        
        
    path = "c:/sedm/logs/{}.txt".format(name)
    print("Logging to ", path)
    
    log.basicConfig(filename=path,
        format="%(asctime)s-%(filename)s:%(lineno)i-%(levelname)s-%(message)s",
        level = log.INFO)

    log.info("*************************RESTARTING************************")


        
    i = PIXIS(serial_num, name)

    i.set([1.0, MEDIUM_GAIN, LOW_RN_AMP, FAST_READOUT]) 
    i.set_shutter("closed")
    
    server = SimpleXMLRPCServer(("localhost", 8001), logRequests=True)

    server.register_instance(i)
    
    os.system("title {} Control".format(name, os.getpid()))
    server.serve_forever()




