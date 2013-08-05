
from traits.api import *
from traitsui.api import View, Item, Handler

from multiprocessing import Process
from threading import Thread
from httplib import CannotSendRequest

import pyfits as pf
import time
import xmlrpclib

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
            time.sleep(20)
        
        
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
    
    def _home_button_fired(self):
        self.comms_thread.request_home = True
    
    def _reset_button_fired(self):
        self.comms_thread.request_reset = True
    
    def _go_button_fired(self):
        self.comms_thread.request_moveto = True
    
    def _target_changed(self):
        pass
    
    def __init__(self, connection):
        self.connection = connection
        self.comms_thread = CommsThread()
        self.comms_thread.stage = self
        self.comms_thread.start()



def stage_gui_connection(connection):
    
    stage = Stage(connection)
    stage_view = View(    
        Item(name="state"),
        Item(name="location"),
        Item(name="target"),
        Item(name="home_button"),
        Item(name="reset_button"),
        Item(name="go_button"),
        title="Spectrograph focus", width=300)
        
    stage.configure_traits(view=stage_view)
    
    return stage

    