
'''

SED Machine global server

Handles telescope and instrument control of following XML RPC Servers:
    P60 Telescope
    SED Machine focus
    RC Camera
    IFU Camera
    
    [c] 2014 Nick Konidaris

'''

import math, time
import logging as log
import pdb
import os

import Options

from SimpleXMLRPCServer import SimpleXMLRPCServer
import GXN

reload(Options)
reload(GXN)

class GlobalServer:
    
    def __init__(self):
        pass
        
    
    def moveto(self, name, ra, dec, epoch):

        c = GXN.Commands()
        
        if Options.TESTING:
            print "Send coords command"
            time.sleep(5)
            return True

        try:
            c.coords(ra, dec, 0.0, 0,0,0, name=name)
            c.go()
        except:
            return False
        
        return True
            
    
    
    
if __name__ == '__main__':
    server = SimpleXMLRPCServer(("127.0.0.1", Options.global_port))
    
    gs = GlobalServer()
    server.register_instance(gs)
    server.serve_forever()
    
    


