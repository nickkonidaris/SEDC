
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
import Secfocus, Fourshot

import logging

import Util




reload(Secfocus)
reload(Options)


class SEDMControl(HasTraits):
    '''Instrument control GUI'''

    location = String("Not defined")
    position = Enum(["undefined","u","g","r","i","ifu","on the way"])
    comment = String("")
    cam_exp_time = Array(np.float,[4])
    spec_exp_time = Float(0)
    n_spec = Int(0)
    pattern = Enum(['ABCD', 'AB', 'A'])
    focus_min=Float(18)
    focus_max=Float(20)
    dfocus=Float(.1)
    

    go_next_field_button=Button("Go to next field")
    
    move_target_to_ifu_button=Button("Move to IFU") 
    take_spectra_button=Button("Take spectra") 
    take_rc_button=Button("Take images") 
    go_focus=Button("Take focus")
    go_conf=Button("Confirmation image")
    go_x=Button("X here")
    
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
            Item("_"),
            Item(name='focus_min'),
            Item(name='focus_max'),
            Item(name='dfocus'),
            Item(name='go_focus'),
            Item("_"),
            Item(name='go_x'),

            width=400)
        
        self.configure_traits(view=c_view)
        
        
    def _go_conf_fired(self):
        ''' Take a 30-s confirmation image, returns after 32 s '''
        
        rc_control = xmlrpclib.ServerProxy("http://127.0.0.1:%i" % Options.rc_port)
        

        rc_control.setnumexposures(1)
        rc_control.set_shutter('normal')
        rc_control.setexposure(30)
        rc_control.setobject("%s [%s]" % (self.location, self.position))
        
        rc_control.go()
        
        while not rc_control.isExposing():
            time.sleep(1)
        
        logging.info("%s - 30 s confirmation image" % rc_control.getfilename())
        
    

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
        
        positions = np.arange(self.focus_min, self.focus_max, self.dfocus)
        files = Secfocus.secfocus(rc_control, positions)
        print files
        
        for f in files:
            logging.info("%s -- focus loop" % f)
            
        Secfocus.analyze(files)


if __name__ == '__main__':
    
    logging.basicConfig(filename = os.path.join(Options.obs_log_path, "obslog.txt"),
        level=logging.INFO)
    
    logging.info("LOG STARTING")
    C = SEDMControl()
    C.show()