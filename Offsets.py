
# P60 tel offset
from traits.api import *
from threading import Thread
import telnetlib
import re
import time
import numpy as np
from datetime import datetime
import Util

from traitsui.api import View, Item, Handler, Action, TabularEditor, Group
from traitsui.menu import ApplyButton
from enthought.traits.ui.tabular_adapter \
    import TabularAdapter
from subprocess import check_output


def hms_to_deg(hms):
    print hms
    try: h,m,s =map(float, hms.split(":"))
    except: 
        self.status ="Can't understand HMS: '%s'" % hms
        return float(hms)

    return 15*(h+m/60.+s/3600.)

def dms_to_deg(dms):
    try: d,m,s = map(float, dms.split(":"))
    except: 
        self.status = "Can't understand DMS: '%s'" % dms
        return 0
    
    if dms[0] == '-': sign = -1.0
    else: sign = 1.0
    
    return sign*(d+m/60.+s/3600.)
        

gxn_res = {0: "Success", -1: "Unknown command", -2: "Bad parameter", 
    -3: "Aborted", -6: "Do not have control"}

        
class Offsetter(HasTraits):
    counter = 0
    
    dx = Float()
    dy = Float()
    send = Button('Send')
    loadsend = Button('Load and Send Coordinates')
    toifu = Button("Send to IFU")
    status = String()
    
    
    view = View(
        Group(

            Item('status'),
            Item('loadsend'),
            #Item('toifu'),
    
            show_labels        = True,
        ),
        title     = 'Offsetter',
        width     = 0.15,
        resizable = True,
        kind = 'live'
    )
    
    def pt(self, dRA, dDec):
        try:
            T = telnetlib.Telnet("pele.palomar.caltech.edu", 49300)

            T.write("pt %f %f\n" % (dRA, dDec))
            r = T.expect(["-?\d"], 60)[2]

        except Exception as e:
            print e
            self.status = "Could not comm"
            return
        
        try: res = int(r)
        except: 
            self.status="Timeout."
            return
        
        if res  == 0:
            self.status = "%i: executed" % (self.counter)
            print "%s: %5.1f %5.1f" % (datetime.now(), dRA,dDec)
        else:
            self.status = "%i: %s failed" % (self.counter, gxn_res[res])
        
        self.counter +=1
    
    def handle(self, ruler):        
        s = ruler.split('(')[1]
        s = s.split(")")[0]
        start_ra, start_dec, end_ra, end_dec = s.split(",")
        
        sra = hms_to_deg(start_ra)
        era = hms_to_deg(end_ra)
        sdec = dms_to_deg(start_dec)
        edec = dms_to_deg(end_dec)
        
        dRA = (sra-era)*3600 * np.cos(np.radians((sdec+edec)/2.))
        dDec = (sdec-edec)*3600
    

        print dRA, dDec
        self.pt(dRA, dDec)
        
    
        
    def _toifu_fired(self):
        
        self.pt(-120, -120)
        
    def _loadsend_fired(self):
        xpa_methods = Util.check_and_start_ds9()
        xpa = xpa_methods[0]
        
        try: 
            regions = check_output("c:\\ds9\\xpaget %s regions -format ds9 -system wcs -skyformat sexagesimal" % (xpa), shell=True)
            lines = regions.split("\n")
        except Exception as e:
            print e
            return
        
        for line in lines:
            if line[0:3] == '# r':

                self.handle(line)
                return
        
        self.status = "%i No ruler found" % self.counter
        self.counter += 1


if __name__ == '__main__':
 
    os = Offsetter()
    os.configure_traits()
