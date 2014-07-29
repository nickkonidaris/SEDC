
from traits.api import *
from traitsui.api import View, Item, Handler

from threading import Thread, Timer

import numpy as np
import pyfits as pf
import os
import sys
from httplib import CannotSendRequest
import time
import tempfile
import xmlrpclib
from SimpleXMLRPCServer import SimpleXMLRPCServer
import winsound

import psutil
import subprocess as SP

import GXN
import Util
from subprocess import check_output

def ra_to_deg(ra):
    h,m,s = map(float,ra.split(":"))
    
    return 15 * h + 0.25*m + 0.0042*s

def dec_to_deg(dec):
    d,m,s = map(float,dec.split(":"))
    
    return d + m/60. + s/3600.
    
    

def ds9_image(xpa_class,  filename):
    
    if xpa_class is None:
        return
        
    retains = ["scale mode", "scale", "cmap",  "zoom", "pan to"]
    vals = []
    try:
        check_output("c:\\ds9\\xpaset -p %s frame 1" % (xpa_class), shell=True)
        for retain in retains:
            value = check_output("c:\\ds9\\xpaget %s %s" % (xpa_class, retain), shell=True)
            vals.append((retain, value))
            
    
        check_output("c:\\ds9\\xpaset -p %s file %s" % (xpa_class, filename), shell=True)
        check_output("c:\\ds9\\xpaset -p %s frame match wcs" % (xpa_class), shell=True)
        
        for key, val in vals:
            check_output("c:\\ds9\\xpaset -p %s %s %s" % (xpa_class, key, val), shell=True)
        
        if filename.find("rc") != -1:
            check_output("C:\\ds9\\xpaset -p %s regions load c:/sw/sedm/ds9.reg" % (xpa_class), shell=True)

    
    #check_output("c:\\ds9\\xpaset -p %s cmap invert yes" % (xpa_class), shell=True)
    except Exception as e:
        #FIXME
        print "Skipping exception:"
        print e
        pass

def play_sound(snd="SystemAsterix"):
    
    try:
        Play = Thread(target=winsound.PlaySound, args=(snd, 
            winsound.SND_ALIAS))
        Play.start()
    except:
        pass

class IncrementThread(Thread):
    stop = False
    def run(self):
        
        self.camera.int_time = 0
        
        while not self.stop:
            self.camera.int_time += 1
            
            if self.camera.readout == 2: overhead = 6
            else: overhead = 50
            
            if self.camera.int_time > (self.camera.exposure+overhead):
                play_sound("SystemAsterisk")
            time.sleep(1)

class ExposureThread(Thread):
    
    def append_headers_by_trait(self, traits, hdrvalues_to_update):
        
        if traits is not None:
            for trait in traits.trait_names():
                trait_val = traits.trait_get(trait)
                # Check if trait is {trait: trait_val} or just {}
                if trait_val.has_key(trait):
                    hdrvalues_to_update.append((trait, trait_val[trait]))
                else:
                    pass
        
        return hdrvalues_to_update
        
    def run(self):
        nexp = self.camera.num_exposures
        filenames = []
        
        while self.camera.num_exposures > 0:
            
            hdrvalues_to_update = []
            
            hdrvalues_to_update = self.append_headers_by_trait(self.camera.status_threads.telescope, hdrvalues_to_update)
            hdrvalues_to_update = self.append_headers_by_trait(self.camera.status_threads.weather, hdrvalues_to_update)            
                                
            try:
                self.camera.state = "Exposing..."
                IT = IncrementThread()
                IT.camera = self.camera
                IT.start()
                filename = self.camera.connection.acquire().data
                IT.stop = True
            except:
                self.camera.state = "Exposure Failed due to communications problem"
                return False
                
            self.camera.filename = filename
            filenames.append(filename)
            
            self.camera.state = "Updating Fits %s" % filename
            try:
                hdus = pf.open(filename)
                hdr = hdus[0].header
                hdr.update("OBJECT",self.camera.object)
            except:
                self.camera.state = "Could not open raw fits"
                return False
            

            for el in hdrvalues_to_update:
                trait, val = el
                #print trait, val
                try: hdr.update(trait, val)
                except: pass
            
            if self.camera.name == 'ifu':
                if self.camera.amplifier == 1:
                    if self.camera.readout == 0.1:
                        if self.camera.gain == 1: gain = 3.29
                        if self.camera.gain == 2: gain = 1.78
                        if self.camera.gain == 3: gain = 0.89
                    if self.camera.readout == 2:
                        if self.camera.gain == 1: gain = 3.49
                        if self.camera.gain == 2: gain = 1.82
                        if self.camera.gain == 3: gain = 0.90
                if self.camera.amplifier == 2:
                    if self.camera.readout == 0.1:
                        if self.camera.gain == 1: gain = 14.72
                        if self.camera.gain == 2: gain = 7.03
                        if self.camera.gain == 3: gain = 3.49
                    if self.camera.readout == 2:
                        if self.camera.gain == 1: gain = 13.92
                        if self.camera.gain == 2: gain = 6.88
                        if self.camera.gain == 3: gain = 3.43
            elif self.camera.name == 'rc':
                if self.camera.amplifier == 1:
                    if self.camera.readout == 0.1:
                        if self.camera.gain == 1: gain = 3.56
                        if self.camera.gain == 2: gain = 1.77
                        if self.camera.gain == 3: gain = 0.90
                    if self.camera.readout == 2:
                        if self.camera.gain == 1: gain = 3.53
                        if self.camera.gain == 2: gain = 1.78
                        if self.camera.gain == 3: gain = 0.88
                if self.camera.amplifier == 2:
                    if self.camera.readout == 0.1:
                        if self.camera.gain == 1: gain = 14.15
                        if self.camera.gain == 2: gain = 7.27
                        if self.camera.gain == 3: gain = 3.79
                    if self.camera.readout == 2:
                        if self.camera.gain == 1: gain = 14.09
                        if self.camera.gain == 2: gain = 7.02
                        if self.camera.gain == 3: gain = 3.52
                        
            hdr.update("GAIN", gain, 'gain in e-/ADU')
            try:
                stage_control = xmlrpclib.ServerProxy(Util.stage_server_address)

                hdr.update("IFUFOCUS", 
                    stage_control.get_location(),
                    "focus stage position in mm")
            except:
                pass    
                
            hdr.update("CHANNEL", self.camera.name, "Instrument channel")
            hdr.update("TNAME", self.camera.target_name, "Target name")
            
            try:
                if self.camera.name == 'rc':
                    hdr.update("CRPIX1", 1293, "Center pixel position")
                    hdr.update("CRPIX2", 1280, "")
                    hdr.update("CDELT1", -0.00010944, "0.394 as")
                    hdr.update("CDELT2" ,-0.00010944, "0.394 as")
                    hdr.update("CTYPE1", "RA---TAN")
                    hdr.update("CTYPE2", "DEC--TAN")
                    hdr.update("CRVAL1", ra_to_deg(hdr["RA"]), "from tcs")
                    hdr.update("CRVAL2", dec_to_deg(hdr["Dec"]), "from tcs")
                elif self.camera.name == 'ifu':
                    hdr.update("CRPIX1", 1075, "Center pixel position")
                    hdr.update("CRPIX2", 974, "Center pixel position")
                    hdr.update("CDELT1", -0.0000025767, "0.00093 as")
                    hdr.update("CDELT2", -0.0000025767, "0.00093 as")
                    hdr.update("CTYPE1", "RA---TAN")
                    hdr.update("CTYPE2", "DEC--TAN")
                    as120 = 0.03333
                    hdr.update("CRVAL1", ra_to_deg(hdr["ra"]) - as120, "from tcs")
                    hdr.update("CRVAL2", dec_to_deg(hdr["dec"]) - as120, "from tcs")
            except Exception as e:
                print "Could not update header:"
                print type(e)     # the exception instance
                print e.args      # arguments stored in .args
                print e          
                
                
            new_hdu = pf.PrimaryHDU(np.uint16(hdus[0].data), header=hdr)
            hdus.close()

            tempname = "c:/users/sedm/appdata/local/temp/sedm_temp.fits"
            origname = filename

            
            try: os.remove(tempname)
            except WindowsError: pass
            
            try:
                os.rename(origname, tempname)
            except Exception as e:
                print e
                self.camera.state = "Rename %s to %s failed" % (filename, tempname)
                play_sound("SystemExclamation")
                return False
            
            try:
                new_hdu.writeto(filename)
            except:
                os.rename(tempname, filename)
                self.camera.state = "Could not write extension [2]"
                play_sound("SystemExclamation")
                return False
                

            play_sound("SystemAsterix")    
            
            xpa_methods = Util.check_and_start_ds9()
            if self.camera.name == 'rc': method = xpa_methods[0]
            else: method = xpa_methods[1]
            ds9_image(method,  filename)
            self.camera.num_exposures -= 1
        self.camera.num_exposures = 1
        self.camera.state = "Idle"
        if nexp > 1: play_sound("SystemExclamation")
    
        return filenames
        
class Camera(HasTraits):
    '''Exposure Control'''  
    name = String("unknown")  
    target_name = String()
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
    
    shutter = Enum('normal', 'closed')
    
    xpa_class = String()
    
    exposure = Float(10, desc="the exposure time in s",
        label = "Exposure")
    
    exposure_thread = Instance(ExposureThread)
    
    go_button = Button("Go")
   
    def setnumexposures(self, val):
        self.num_exposures = val
        return val
        
    def setreadout(self, val):
        self.readout = val
        return self.readout
        
    def setshutter(self, val):
        self.shutter = val
        self.connection.set_shutter(self.shutter)
        return self.shutter
    
    def setexposure(self, val):
        self.exposure = val
        return self.exposure
    
    def isExposing(self):
        if self.exposure_thread:
            return self.exposure_thread.isAlive()
        else:
            return False
    
    def isExposureComplete(self):
        return (self.int_time) > (self.exposure + 1.5)
    
    def setobject(self, val):
        self.object = val
        return self.object
        
    def getfilename(self):
        return self.filename
        
    def getall(self):
        '''For XMLRPCServer, provides access to variables'''
        
        return (self.name, self.object, self.state, self.filename, 
            self.gain, self.num_exposures, self.int_time, self.readout, 
            self.amplifier, self.shutter, self.exposure)

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
            return False
        except: 
            self.state = "DID NOT UPDATE. Retry"
            return False
        
        return True

    def go(self):
        
        if self.exposure_thread and self.exposure_thread.isAlive():
            print "alive"
            return True
        else:
            self.state = "Exposure requested"
            try:

                self.target_name = self.target_gui.name

            except Exception as e:
                pass

            print "Exposing.."
            self.exposure_thread = ExposureThread()
            self.exposure_thread.camera = self
            self.exposure_thread.start()
            return True
        
        return True
    
    def _go_button_fired(self):
        self.go()
    def show(self):
        cam_view = View(    
            Item(name="state"),
            Item(name="object"),
            #Item(name="gain"),
            #Item(name="amplifier"),
            Item(name="readout"),
            Item(name="shutter"),
            Item(name="exposure"),
            Item(name="int_time"),
            Item(name="num_exposures"),
            Item(name="filename"),
            Item(name="go_button"),
            title=self.name, width=350, kind='live')
        
        import thread
        thread.start_new_thread(self.configure_traits, (("view", cam_view)))

        
        return True
        
class Window(Handler):
    
    def setattr(self, info, object, name ,value):
        Handler.setattr(self, info, object, name, value)
        info.object._updated = True

        
    def object__updated_changed(self, info):
        if info.initialized:
            info.ui.title += "*"


def open_camera(name):

    sedmpy = "C:/Users/sedm/Dropbox/Python-3.3.0/PCbuild/amd64/python.exe"

    if name == "rc":
        pid = SP.Popen([sedmpy, "c:/sw/sedm/camera.py", "-rc"])
        port = 8001
        time.sleep(3)

    else:
        pid = SP.Popen([sedmpy, "c:/sw/sedm/camera.py", "-ifu"])
        port = 8002
        time.sleep(3)
        
    c = Camera()
    c.name = name
    
    Status = GXN.StatusThreads()
    Status.start()
    
    connection = xmlrpclib.ServerProxy("http://127.0.0.1:%s" % port)
    
    c.connection = connection
    c.status_threads = Status
    if name == 'rc': c.readout = 2
    
    c.setshutter("normal")

    server = SimpleXMLRPCServer(("127.0.0.1", port+1000), logRequests=True)
    print "Serving on port %i" % (port+1000)

    server.register_instance(c)
    
    os.system("title {} Control".format(name, os.getpid()))

    server.serve_forever()


if __name__ == '__main__':

    if sys.argv[1] == "-rc":
        open_camera("rc")
    elif sys.argv[1] == '-ifu':
        open_camera("ifu")
        
