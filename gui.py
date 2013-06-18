
from traits.api import *
from traitsui.api import View, Item, Handler

from threading import Thread

import pyfits as pf
import xmlrpclib
from httplib import CannotSendRequest
import time


class IncrementThread(Thread):
    stop = False
    def run(self):
        
        self.camera.int_time = 0
        
        while not self.stop:
            self.camera.int_time += 1
            time.sleep(1)

class ExposureThread(Thread):
    def run(self):
        nexp = self.camera.num_exposures
        while self.camera.num_exposures > 0:
            try:
                self.camera.state = "Exposing..."
                IT = IncrementThread()
                IT.camera = self.camera
                IT.start()
                filename = self.camera.connection.acquire().data
                IT.stop = True
            except:
                self.camera.state = "Exposure Failed due to communications problem"
                return
                
            self.camera.filename = filename
            self.camera.state = "Updating Fits %s" % filename
            try:
                hdus = pf.open(filename, mode="update")
                hdr = hdus[0].header
                hdr.update("OBJECT",self.camera.object)
            except:
                self.camera.state = "Could not append extension"
                return
            
            if self.camera.stage_connection is not None:
                try:
                    hdr.update("IFUFOCUS", 
                        self.camera.stage_connection.position_query(),
                        "focus stage position in mm")
                except CannotSendRequest:
                    hdr.update("IFUFOCUS", 
                        self.camera.stage_connection.position_query(),
                        "focus stage position in mm")
    
            try:
                hdus.flush()
            except:
                self.camera.state = "Could not write extension"
                return
            
            self.camera.num_exposures -= 1
        
        self.camera.num_exposures = nexp
        self.camera.state = "Idle"
        
        
class Camera(HasTraits):
    '''Exposure Control'''    
    object = String
    connection = None #xmlrpclib object to connect to PIXIS camera
    stage_connection = None #xmlrpclib object to connect to newport focus stage
    
    state = String("Idle")
    filename = String("")
    
    gain = Enum(2,1,3,
        desc="the gain index of the camera",
        label='gain')
    
    num_exposures = Int(1)
    
    int_time = Int(0)
    
    readout = Enum([0.1, 2.0],
        desc="Readout speed in MHz",
        label="readout")
        
    amplifier = Enum(1,2,
        desc="the amplifier index",
        label = 'amp')
    
    shutter = Enum('closed', 'normal', 'open')
    
    exposure = Float(10, desc="the exposure time in s",
        label = "Exposure")
    
    exposure_thread = Instance(ExposureThread)
    
    go_button = Button("Go")
   
    def _gain_changed(self): self.update_settings()
    def _readout_changed(self): self.update_settings()
    def _amplifier_changed(self): self.update_settings()
    def _exposure_changed(self): self.update_settings()
    def _shutter_changed(self):
        self.connection.set_shutter(self.shutter)
        
        
    def update_settings(self):
        try:
            self.connection.set([self.exposure, self.gain, self.amplifier, 
                self.readout])
        except CannotSendRequest:
            self.state = "DID NOT UPDATE. RETRY"
        except: 
            self.state = "DID NOT UPDATE. Retry"
        
    def _go_button_fired(self):

        if self.exposure_thread and self.exposure_thread.isAlive():
            print "alive"
            return
        else:
            self.state = "Exposure requested"
            self.exposure_thread = ExposureThread()
            self.exposure_thread.camera = self
            self.exposure_thread.start()
        

class Window(Handler):
    
    def setattr(self, info, object, name ,value):
        Handler.setattr(self, info, object, name, value)
        info.object._updated = True

        
    def object__updated_changed(self, info):
        if info.initialized:
            info.ui.title += "*"



def gui_connection(connection, name, stage_connection=None):
    camera = Camera()
    camera.connection = connection
    handler = Window()
    
    camera.stage_connection = stage_connection
    
    cam_view = View(    
            Item(name="state"),
            Item(name="object"),
            Item(name="gain"),
            Item(name="amplifier"),
            Item(name="readout"),
            Item(name="shutter"),
            Item(name="exposure"),
            Item(name="int_time"),
            Item(name="num_exposures"),
            Item(name="filename"),
            Item(name="go_button"),
            title=name, width=350)
            
    camera.configure_traits(view=cam_view)
    
    print "here"
    return camera
    