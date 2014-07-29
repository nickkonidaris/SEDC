
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

import psutil
import subprocess as SP

import GXN
import Util
from subprocess import check_output
from astropy.table import Table
import Options
import xmlrpclib 
import Secfocus, Fourshot, Nodder

import logging

import Util

import pyfits as pf


reload(Secfocus)
reload(Options)
reload(Nodder)


def evaluate_file_for_cnts(filename):
    '''evaluate_file_for_cnts -> float
    
    Returns required exposure time to achieve between 20,000 to 40,000 cts'''
    
    FF = pf.open(filename)
    dat = FF[0].data
    exptime = FF[0].header['exptime']
    
    # Check median range
    bias = np.median(dat[2047,:])
    
    dat -= bias
    fdat = np.reshape(dat, dat.shape[0]*dat.shape[1])
    sfdat = np.sort(fdat)
    val = sfdat[-30]
    
    if 20000 < val < 40000:
        return exptime
    
    else:
        return exptime * 30000./val
        
    
def test_exposure(controller, itime):
    '''test_exposure -> float
    Returns the exposure time to use for calibration filee
    
    Args:
        controller-- the camera_control_gui instance
        itime-- integration time guess in seconds'''
    
    controller.setshutter('normal')
    controller.setnumexposures(1)
    controller.setexposure(itime)
    fn = controller.go() [0]
    
    logging.info("%s -- test exposure" % fn)
    
    return evaluate_file_for_cnts(fn)
    

class SEDMControl(HasTraits):
    '''Instrument control GUI'''

    
    # Telescope location: this is an object name
    location = String("Not defined")
    
    # Position of target on instrument
    position = Enum(["undefined","u","g","r","i","ifu","on the way"])
    
    # For reference, the comment string in the target list
    comment = String("")
    
    # RC camera exposure time [u,g,r,i] in s
    cam_exp_time = Array(np.float,[4])
    
    # Spectrograph exposure time in s + number of IFU exposures to take
    spec_exp_time = Float(0)
    n_spec = Int(0)
    
    # Dithering pattern
    pattern = Enum(['ABCD', 'AB', 'A'])
    
    # Focus controls
    focus_range = String("13.8, 14.1, 0.1")
    
    # Calibration type
    calib_type = Enum(["dome", "twilight", "Hg", "Ne", "Xe", "dark", "bias"])
    
    # Telescope positions
    telescope_position = Enum(['day stow', 'flat stow', 'twilight stow', 'open', 'close'])

    go_next_field_button=Button("Go to next field")
    
    move_target_to_ifu_button=Button("Move to IFU") 
    take_spectra_button=Button("Take spectra") 
    take_rc_button=Button("Take images") 
    go_focus=Button("Take focus")
    go_conf=Button("Confirmation image")
    go_x=Button("X here")
    go_calib=Button("Calibration")
    go_stow=Button("Telescope")
    
    def show(self):
        '''show: establishes the GUI layout'''
        c_view  = View(
            Item(name="location"),
            Item(name="position"),
            Item(name="comment"),
            Item(name="go_next_field_button"),
            Item("_"),
            Item(name="cam_exp_time"),
            Item(name="take_rc_button"),
            Item("_"),
            Item(name="spec_exp_time"),
            Item(name="n_spec"),
            Item(name="pattern"),
            Item(name="take_spectra_button"),
            Item("_"),
            Item(name="go_conf"),
            Item(name='go_x'),
            Item("_"),
            Item(name='focus_range'),
            Item(name='go_focus'),
            Item("_"),

            Item(name='calib_type'),
            Item(name='go_calib'),
            Item(name='telescope_position'),
            Item(name='go_stow'),          

            width=400)
        
        self.configure_traits(view=c_view)
        
        
    def _go_conf_fired(self):
        ''' Take a 30-s confirmation image, returns after 32 s '''
        
        rc_control = xmlrpclib.ServerProxy("http://127.0.0.1:%i" % Options.rc_port)
        

        rc_control.setnumexposures(1)
        rc_control.set_shutter('normal')
        rc_control.setexposure(30)
        rc_control.setobject("%s [%s] confirmation" % (self.location, self.position))
        
        rc_control.go()
        
        while not rc_control.isExposing():
            time.sleep(1)
        
        logging.info("%s - 30 s confirmation image" % rc_control.getfilename())

    def _take_spectra_button_fired(self):
        ''' Takes rc + ifu spectra '''
        rc_control = xmlrpclib.ServerProxy("http://127.0.0.1:%i" % Options.rc_port)
        ifu_control = xmlrpclib.ServerProxy("http://127.0.0.1:%i" % Options.ifu_port)

        
        files = Nodder.nodder(self.location, rc_control, ifu_control, spec_exp_time,
            positions=self.pattern)
            
        for rc in files.rc:
            logging.info("%s [science Rc]" % rc)
        
        for ifu in files.ifu:
            logging.info("%s [science IFU]" % ifu)

    def connect_global_server(self):
        ''' returns a xmlrpc object connected to the global server'''
        
        addy = "http://127.0.0.1:%i" % Options.global_port
        global_server = xmlrpclib.ServerProxy(addy)
        
        return global_server
    
    
    def _take_rc_button_fired(self):
        ''' Take fourshot '''
        
        rc_control = xmlrpclib.ServerProxy("http://127.0.0.1:%i" % Options.rc_port)
        files = Fourshot.fourshot(rc_control)
        
        for t in files:
            logging.info("%s -- fourshot" % t)
        
        
    def _go_next_field_button_fired(self):
        ''' Go to next field button fired '''
        t = Table.read(Options.targets_outfile, format='ascii.ipac')[0]

        gs = self.connect_global_server()
        self.comment = str(t['comment'])
        self.location = "OTW: %s" % str(t['name'])
        self.position = "on the way"

        gs.moveto(      str(t['name']),
                        float(t['RA']),
                        float(t['Dec']),
                        float(t['epoch']))
        
        self.location = "%s" % str(t['name'])
        self.position = "r"
        
        logging.info("--- Move to %s ---" % t['name'])
        logging.info("%s %s (%s)" % (t['name'], t['RA'], t['Dec'], t['epoch']))
        
        
        
    def _go_focus_fired(self):
        ''' Secondary mirror focus requested'''
        rc_control = xmlrpclib.ServerProxy("http://127.0.0.1:%i" % Options.rc_port)
        
        mn,mx,df = self.focus_range.split(",")
        logging.info("Starting focus over %s,%s,%s" % (mn,mx,df))
        positions = np.arange(mn,mx,df)
        files = Secfocus.secfocus(rc_control, positions)
        print files
        
        for f in files:
            logging.info("%s -- focus loop" % f)
            
        Secfocus.analyze(files)

    def _go_calib_fired(self):
        self.handle_calib('ifu')
    
        
    def handle_calib(self, channel):
        
        cmds = GXN.Commands()
        
        rc_control = xmlrpclib.ServerProxy("http://127.0.0.1:%i" % 
            Options.rc_port)
        ifu_control = xmlrpclib.ServerProxy("http://127.0.0.1:%i" % 
            Options.ifu_port)
            
        if self.calib_type == 'bias':
            logging.info("--- Taking bias frames ---")
            rc_control.setshutter('closed')
            rc_control.setobject('Calib: bias')

            rc_control.setnumexposures(10)
            rc_control.setexposure(0)
            rc_files = rc_control.go()
            ifu_control.setshutter('closed')
            ifu_control.setnumexposures(10)
            ifu_control.setexposure(0)
            ifu_control.setobject('Calib: bias')
            ifu_files = ifu_control.go()        
            
            logging.info(rc_files)
            logging.info(ifu_files)
        
        if self.calib_type == 'dome':
            logging.info("--- Taking dome lamps with 120 s warmup ---")

            cmds.lamps_on()
            time.sleep(120)
            
            new_rc_itime = test_exposure(rc_control, 5)            
            logging.info("    New RC itime is %s" % new_rc_itime)
            new_ifu_itime = test_exposure(ifu_control, 15)            
            logging.info("    New IFU itime is %s" % new_ifu_itime)
               
            # now handle real exposures            
            rc_control.setnumexposures(10)
            ifu_control.setobject('Calib: dome lamp')
            rc_control.setexposure(new_rc_itime)
            rc_files = rc_control.go()
            
            for fn in rc_files:
                logging.info("%s -- rc lamp" % fn)
                
            
            ifu_control.setobject('Calib: dome lamp')

            ifu_control.setnumexposures(10)
            rc_control.setexposure(new_ifu_itime)
            ifu_files = ifu_control.go()
            
            for fn in ifu_files:
                logging.info("%s -- ifu lamp" % fn)
                 
            
            cmds.lamps_off()
            time.sleep(10)
            logging.info("--- Dome flats off ---")

            
    def _go_stow_fired(self):
        if self.telescope_position == 'flat stow':
            logging.info("--- Flat stow position ")
            cmds.stow_flats()
            
        elif self.telescope_position == 'twilight stow':
            logging.info("--- Twilight stow position ")
            cmds.stow_flats()
        
        elif self.telescope_position == 'day stow':
            logging.info("--- Day stow position ")
            cmds.stow_day()
            
        elif self.telescope_position == 'open':
            logging.info("--- DOME OPEN ")
            cmds.open_dome()

        elif self.telescope_position == 'close':
            logging.info("--- DOME CLOSE ")
            cmds.close_dome()


if __name__ == '__main__':
    
    logging.basicConfig(filename = os.path.join(Options.obs_log_path, "obslog.txt"),
        level=logging.INFO)
    
    logging.info("LOG STARTING")
    C = SEDMControl()
    C.show()