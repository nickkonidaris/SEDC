# -*- coding: utf-8 -*-

from traits.api import *
from traitsui.api import View, Item, Handler

from multiprocessing import Process
from threading import Thread
from httplib import CannotSendRequest

import pyfits as pf
import time
import os
import subprocess
import xmlrpclib
import Util
from SimpleXMLRPCServer import SimpleXMLRPCServer


class CommsThread(Thread):
    stage = None
    request_moveto = False
    request_home = False
    request_reset = False
    request_focus = False
    processing_job = None
    request_abort = False
    
    def communicate(self):
        com = self.stage.connection
        stg = self.stage
        
        try:
            if self.request_home:
                com.home()
                self.request_home = False
            if self.request_moveto:
                com.move_unblocked(stg.target)
                self.request_moveto = False
            if self.request_reset:
                com.reset_stage()
                self.request_reset = False
        except CannotSendRequest:
            stg.state = "Could not execute, failed serial comms "
        except:
            stg.state = "Could not execute, failed interprocess-communications request"

        try:            
            stg.location = com.position_query()
            stg.state = com.get_state()[1]
            stg.is_ready = com.is_ready()
        except CannotSendRequest:
            stg.state = "Could not perform serial-line request"
        except:
            stg.state = "Could not perform inter-process request"
        
    def process(self):
        
        try:
            if self.processing_job.isAlive():
                return
                
        except AttributeError:
            pass
            
        self.processing_job = Thread(target=self.communicate)
        self.processing_job.start()
    
    def run(self):
        
        
        while self.request_abort == False:
            self.process()
            time.sleep(1)
        
        
class Stage(HasTraits):
    location = Float()
    target = Float()
    state = String()
    home_button = Button(desc="home")
    go_button = Button()
    reset_button = Button()
    comms_thread = Instance(CommsThread)
    connection = None
    is_ready = False
    
    def set_target(self, targ):
        self.target = targ
        return targ
    
    def get_is_ready(self):
        return self.is_ready
        
    def get_state(self):
        return self.state
        
    def home(self):
        self.comms_thread.request_home=True
        return True
        
    def get_location(self):
        return self.location
        
    def reset(self):
        self.comms_thread.request_reset = True
        return True
        
    def go(self):
        self.comms_thread.request_moveto = True
        return True
        
    def _home_button_fired(self):
        self.home()
    
    def _reset_button_fired(self):
        self.reset()
        
    def _go_button_fired(self):
        self.go()
    
    def _target_changed(self):
        pass
    
    def request_focus(self, val):
        self.comms_thread.request_focus = val
        return val
    
    def show(self):

        stage_view = View(    
            Item(name="state"),
            Item(name="location"),
            Item(name="target"),
            Item(name="home_button"),
            Item(name="reset_button"),
            Item(name="go_button"),
            title="Spectrograph focus", width=300)
    
        import thread
        thread.start_new_thread(self.configure_traits, (("view", stage_view)))
        
        return True

    
    def __init__(self, connection):
        self.connection = connection
        self.comms_thread = CommsThread()
        self.comms_thread.stage = self
        self.comms_thread.start()



if __name__ == '__main__':
    
    epy = Util.epy

    stage_pid = subprocess.Popen([epy, "c:/sw/sedm/Stage.py"])
    stage_con = xmlrpclib.ServerProxy("http://127.0.0.1:8500")
    
    stage = Stage(stage_con)
    port = 9004
    server = SimpleXMLRPCServer(("127.0.0.1", port), logRequests=True)
    print "Serving on port %i" % (port)

    server.register_instance(stage)
    
    os.system("title Telescope Monitoring")

    server.serve_forever()