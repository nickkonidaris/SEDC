
from traits.api import *
from traitsui.api import View, Item, Handler

from threading import Thread

import pyfits as pf


class ExposureThread(Thread):
    def run(self):

        self.camera.state = 'Exposing'
        
        filename = self.camera.connection.acquire().data
        self.camera.filename = filename
        self.camera.state = "Updating Fits %s" % filename
        hdus = pf.open(filename, mode="update")
        hdr = hdus[0].header
        hdr.update("OBJECT",self.camera.object)
        if self.camera.stage_connection is not None:
            hdr.update("IFUFOCUS", 
                self.camera.stage_connection.position_query(),
                "focus stage position in mm")
        hdus.flush()
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
        self.connection.set([self.exposure, self.gain, self.amplifier, 
            self.readout])
        
    def _go_button_fired(self):
        self.state = "Exposing"

        if self.exposure_thread and self.exposure_thread.isAlive():
            print "alive"
            return
        else:
            print "exposing"
            self.state = "Exposing"
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
    
    if stage_connection is not None:
        camera.stage_connection = stage_connection
    
    cam_view = View(    
            Item(name="state"),
            Item(name="object"),
            Item(name="gain"),
            Item(name="amplifier"),
            Item(name="readout"),
            Item(name="shutter"),
            Item(name="exposure"),
            Item(name="filename"),
            Item(name="go_button"),
            handler=handler,
            title=name)
            
    camera.configure_traits(view=cam_view)
    
    return camera
    