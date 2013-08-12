
# P60 Telescope Status
from traits.api import *
from threading import Thread
import telnetlib
import re
import time
import numpy as np

from traitsui.api import View, Item, Handler, Action, TabularEditor, Group
from traitsui.menu import ApplyButton
from enthought.traits.ui.tabular_adapter \
    import TabularAdapter
 
 
 
class Target(HasTraits):
    lineno = Int
    name = Str
    ra = Str
    dec = Str
    dra = Float
    ddec = Float
 
class TargetAdapter( TabularAdapter ):

    columns = [ 
                ( 'l#',     'lineno'),
                ( 'Name',    'name' ), 
                ( 'RA',     'ra' ), 
                ( 'Dec', 'dec' ),
                ( 'dRA',  'dra' ),
                ( 'dDec', 'ddec') ]
                
    font                      = 'Courier 12'
    

def sd2g(s):
    sign = 1.0
    if s[0] == '-': sign = -1.0
    
    h,m,s = map(float, s.split(" "))
    
    
    return sign * float(sign*h + m/60. + s/3600.)


gxn_res = {0: "Success", -1: "Unknown command", -2: "Bad parameter", 
    -3: "Aborted", -6: "Do not have control"}


class TargetList(HasTraits):
    
    selected_row  = String()
    counter = Int(0)
    name = String
    cmd = String(enter_set=True, auto_set=False)
    data = List( Target )
    status = String()
    send_data = Button('Send Coordinates')
    send_cmd = Button("Send command")
    go = Button('Go')
    take_control = Button('Take Control')
    reload_data = Button("Reload Data from s:\\master.lst")
    tabular_editor = TabularEditor(
        selected_row='selected_row',
        adapter    = TargetAdapter(),
        operations = [ ]    )

    def _send_cmd_fired(self):
        print "cmd changed"

        try: 
            T = telnetlib.Telnet("pele.palomar.caltech.edu", 49300)
            print self.cmd
            
            T.write(self.cmd + "\n")
            
            r = T.expect(["-?\d"], 15)[2]
            print "'%s'" % r


        except Exception as e:
            print e
            self.status = "Bad connection"
            return      
            
                      
        try: res = int(r.rstrip())
        except: 
            self.status = "Unknown result '%s'" % str(r)
            return
        
        if res  == 0:
            self.status = "%i: %s: %s executed" % (self.counter, self.cmd, gxn_res[res])
        else:
            self.status = "%i: %s: %s failed" % (self.counter, self.cmd, gxn_res[res])

        self.cmd = ""
        self.counter += 1

  
            
        
    def _send_data_fired(self):

        
        try: r = np.int(self.selected_row)       
        except ValueError: return
        
        self.status ="-"
        
        targ =  self.data[r]
        name = targ.name
        ra = targ.ra
        dec = targ.dec
        dra = targ.dra
        ddec = targ.ddec
        
                        
        try: 
            T = telnetlib.Telnet("pele.palomar.caltech.edu", 49300)

            T.write("coords %f %f 2000.0 0 0\n" % (sd2g(ra), sd2g(dec)))
            r = T.expect(["-?\d"], 15)[2]
            print "'%s'" % r

        except Exception as e:
            print e
            self.status = "Bad connection"
            return
        
        try: res = int(r.rstrip())
        except: return
        
        if res  == 0:
            self.status = "%i: %s : [%s %s]" % (self.counter, gxn_res[res], ra, dec)
            self.name = name
        else:
            self.status = "%i: %s" % (self.counter, gxn_res[res])
        
        self.counter += 1
   
    def _take_control_fired(self):
        self.status = '-'
        
        try: 
            T = telnetlib.Telnet("pele.palomar.caltech.edu", 49300)

            T.write("takecontrol\n")
            r = T.read_until("\n", .1)

        except Exception as e:
            print e
            self.status = "Bad connection"
            return
            
        try: res = int(r.rstrip())
        except: return
        
        if res  == 0:
            self.status = "%i: %s: takecontrol excuted" % (self.counter, gxn_res[res])
        else:
            self.status = "%i: %s: takecontrol failed" % (self.counter, gxn_res[res])

        
        self.counter += 1
        
    def _go_fired(self):
        self.status = '-'
        
        try: 
            T = telnetlib.Telnet("pele.palomar.caltech.edu", 49300)

            T.write("gopos\n")
            r = T.expect(["-?\d"], 5)[2]
            print "'%s'" % r

        except Exception as e:
            print e
            self.status = "Bad connection"
            return
            
        try: res = int(r.rstrip())
        except: return
        
        if res  == 0:
            self.status = "%i: %s: gopos excuted" % (self.counter, gxn_res[res])
        else:
            self.status = "%i: %s: gopos failed" % (self.counter, gxn_res[res])

        
        self.counter += 1

    def _reload_data_fired(self):

        def helper():
            try:
                f = open("s:\\master.lst")
                lines = f.readlines()
                f.close()
            except Exception as e:
                print e
                self.status = "could not read s:\\master.lst"
                return
            
            data = []
            lineno = 0
            for line in lines:
                #print line
                lineno += 1
                line = line.lstrip()
                if len(line) == 0: continue
                if line[0] == '#': continue
                line = re.sub(' +', ' ', line)
                cmt = line.find("#")
                
                sp = line[0:cmt].split()
    
                name = sp[0]
                ra = " ".join(sp[1:4])
                dec = " ".join(sp[4:7])
                
                data.append(
                Target(name = " %s " % name,
                    ra = ra,
                    dec = dec,
                    dra = 0,
                    ddec = 0,
                    lineno = lineno)
                )

            self.data = data
            #self.status = "Processed %i lines" % len(lines)
        
        Thread(target=helper).start()
        time.sleep(0.0)
        

    view = View(
        Group(
            Item('data', editor = tabular_editor),
            Item('status'),
            Item('send_data'),

            Item('go'),
            Item('reload_data'),

            Item("cmd"),
            Item("send_cmd"),
            Item("take_control"),
            show_labels        = False,
        ),
        title     = 'Array Viewer',
        width     = 0.4,
        height    = 0.6,
        resizable = True,
        kind = 'live'
    )


class CommsThread(Thread):
    abort = False

    
    def run(self):       
        T = self.telescope 
        while not self.abort:
            self.telescope.telnet.write("?POS\n")
            while True:

                r= self.telescope.telnet.read_until("\n", .1)
                if r == "":
                    break               

                try:lhs,rhs = r.rstrip().split("=")
                except: continue


                if lhs == 'UTC': T.UTC = rhs
                if lhs == 'Dome_Azimuth': T.domeaz = float(rhs)
                if lhs == 'LST': T.LST = rhs
                if lhs == 'Julian_Date': T.JD = float(rhs)
                if lhs == 'Apparent_Equinox': T.appeq = float(rhs)
                if lhs == 'Telescope_HA': T.HA = rhs
                if lhs == 'Telescope_RA': T.RA = rhs
                if lhs == 'Telescope_Dec': T.Dec = rhs
                if lhs == 'Telescope_RA_Rate': T.RArate = rhs
                if lhs == 'Telescope_Dec_Rate': T.DECrate = rhs
                if lhs == 'Telescope_RA_Offset': T.RAoff = float(rhs)
                if lhs == 'Telescope_Dec_Offset': T.Decoff = float(rhs)
                if lhs == 'Telescope_Azimuth': T.Az = float(rhs)
                if lhs == 'Telescope_Elevation': T.El = float(rhs)
                if lhs == 'Telescope_Parallactic': T.prlltc = float(rhs)
                if lhs == 'Telescope_HA_Speed': T.HAspeed = float(rhs)
                if lhs == 'Telescope_Dec_Speed': T.Decspeed = float(rhs)
                if lhs == 'Telescope_HA_Refr(arcsec)': T.HArefr = float(rhs)
                if lhs == 'Telescope_Dec_Refr(arcsec)': T.Dec_refr = float(rhs)
                if lhs == 'Telescope_Motion_Status': T.Status = rhs
                if lhs == 'Telescope_Airmass': T.airmass = float(rhs)
                if lhs == 'Object_Name': T.Name = rhs.lstrip('"').rstrip('"')

                if lhs == 'Telescope_Equinox': T.equinox = rhs
                if lhs == 'Object_RA': T.obRA = rhs
                if lhs == 'Object_Dec': T.obDEC = rhs
                if lhs == 'Object_RA_Rate': T.obRArt = float(rhs)
                if lhs == 'Object_DEC_Rate': T.obDECrt = float(rhs)
                if lhs == 'Object_RA_Proper_Motion': T.obRApm = float(rhs)
                if lhs == 'Object_Dec_Proper_Motion': T.obDECpm = float(rhs)
                if lhs == 'Focus_Position': T.secfocus = float(rhs)
                if lhs == 'Dome_Gap(inch)': T.domegap = float(rhs)
                if lhs == 'Dome_Azimuth': T.domeaz = float(rhs)
                if lhs == 'Windscreen_Elevation': T.windsc = float(rhs)
                if lhs == 'UTSunset': T.UTSunset = rhs
                if lhs == 'UTSunrise': T.UTsnrs = rhs 

            time.sleep(0.7)


class Telescope(HasTraits):
    comms_thread = Instance(CommsThread)
    
    telnet = Instance(telnetlib.Telnet)
    UTC = String()
    LST = String()
    JD = Float()
    appeq = Float()
    HA = String()
    RA = String()
    Dec = String()
    RArate = String()
    DECrate = String()
    RAoff = Float()
    Decoff = Float()
    Az = Float()
    El = Float()
    prlltc = Float()
    HAspeed = Float()
    Decspeed = Float()
    HArefr = Float()
    Dec_refr = Float()
    Status = String()
    airmass = Float()
    Name = String()
    equinox=String()
    obRA = String()
    obDEC = String()
    obRArt = Float()
    obDECrt = Float()
    obRApm = Float()
    obDECpm = Float()
    secfocus = Float()
    domegap = Float()
    domeaz = Float()
    windsc = Float()
    UTSunset = String()
    UTsnrs = String()
    
    
    def __init__(self):
        
        self.telnet = telnetlib.Telnet("pele.palomar.caltech.edu", 49300)
        self.comms_thread = CommsThread()
        self.comms_thread.telescope = self


class Weather(HasTraits):
    UTC = String()
    Windspeed_Avg_Threshold = Float()
    Gust_Speed_Threshold = Float()
    Gust_Hold_Time = Float()
    Outside_DewPt_Threshold = Float()
    Inside_DewPt_Threshold = Float()
    Wetness_Threshold = Float()
    Wind_Dir_Current = Float()
    Windspeed_Current = Float()
    Windspeed_Average = Float()
    Outside_Air_Temp = Float()
    Outside_Rel_Hum = Float()
    Outside_DewPt = Float()
    Inside_Air_Temp = Float()
    Inside_Rel_Hum = Float()
    Inside_DewPt = Float()
    Mirror_Temp = Float()
    Floor_Temp = Float()
    Bot_Tube_Temp = Float()
    Mid_Tube_Temp = Float()
    Top_Tube_Temp = Float()
    Top_Air_Temp = Float()
    Primary_Cell_Temp = Float()
    Secondary_Cell_Temp = Float()
    Wetness = Int()
    Weather_Status = String()
    
    def __init__(self):
        
        self.telnet = telnetlib.Telnet("pele.palomar.caltech.edu", 49300)
        self.comms_thread = WeatherCommsThread()
        self.comms_thread.weather = self
    
        
class WeatherCommsThread(Thread):
    abort = False

        
    def run(self):       
        W = self.weather 
        while not self.abort:
            W.telnet.write("?WEATHER\n")
            while True:

                r= W.telnet.read_until("\n", .1)

                if r == "":
                    break               

                try:lhs,rhs = r.rstrip().split("=")
                except: continue
                
                type_fun = type(getattr(W, lhs))
                setattr(W, lhs, type_fun(rhs))
            time.sleep(1)
            
def weather_gui_connection():
    w = Weather()
    w.configure_traits()
    w.comms_thread.start()
    
    return w

def target_gui_connection():
    tl = TargetList()
 
    tl.configure_traits()
    return tl


def telescope_gui_connection():
    
    t = Telescope()
    
    tel_view = View(    
        Item(name="RA"),
        Item(name="Dec"),
        Item(name="HA"),
        Item(name="LST"),
        Item(name="UTC"),
        Item(name="HA"),
        Item(name="airmass"),
        Item(name="RAoff"),
        Item(name="Decoff"),
        Item(name="Status"),
        Item(name="Name"),
        Item(name="secfocus"),
        Item(name="El"),
        Item(name="Az"),
        title="60-inch Telescope", width=300)
        
    
    t.configure_traits(view=tel_view)
    t.comms_thread.start()
    
    return t

    
if __name__ == '__main__':
 
    data = []

 
    demo = TargetList()
 
    #telescope_gui_connection()
    #weather_gui_connection()
    demo.configure_traits()
