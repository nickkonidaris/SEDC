import traits.api as TA
from traits.api import Enum, CInt, Float, String

import enthought.traits.ui
from enthought.traits.ui.api import View,Item,Group,Handler,Action,Label

class Exposure(TA.HasTraits):
    '''Exposure Control'''    
    comment = String
    
    state = String("unknown")
    
    gain = Enum(2,1,3,
        desc="the gain index of the camera",
        label='gain')
        
    amplifier = Enum(1,2,
        desc="the amplifier index",
        label = 'amp')
    
    shutter = Enum('normal', 'closed', 'open')
    
    exposure = Float(10, desc="the exposure time in s",
        label = "Exposure")
    

class ExposureHandler(Handler):

        
    
    def setattr(self, info, object, name ,value):
        Handler.setattr(self, info, object, name, value)
        info.object._updated = True
        print value
        
    def object__updated_changed(self, info):
        if info.initialized:
            info.ui.title += "*"

    def go(self, info):
        camera.state = 'going'


def guify_connection(connection, name):

    camera = Exposure()
    handler = ExposureHandler()
    go = Action(name='go', action='go')

    
    cam_view = View(    
            Item(name="state"),
            Item(name="comment"),
            Item(name="gain"),
            Item(name="amplifier"),
            Item(name="shutter"),
            Item(name="exposure"),
            handler=handler,
            buttons = [go],
            title=name)
            
    camera.configure_traits(view=cam_view)
    