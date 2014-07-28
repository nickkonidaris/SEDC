'''
Devices to control the P60 GXN interface.

Written by Nick Konidaris [c] 2014

Released under GPLv2
'''

from threading import Thread
import telnetlib
from traits.api import *
import time
import logging as log

import astropy
from astropy.coordinates import Angle

PELE = "198.202.125.194"
PELEPORT = 49300

log.basicConfig(filename="C:\\sedm\\logs\\rcrc.txt",
    format="%(asctime)s-%(filename)s:%(lineno)i-%(levelname)s-%(message)s",
    level = log.DEBUG)

class TCSConnectionError(Exception):
    def __init__(self, value):
        self.value = value
        log.error("Could not connect to TCS. Fatal error.")
    
    def __str__(self):
        return str(self.value)
        
class TCSReadError(Exception):
    def __init__(self, value):
        self.value = value
        
        log.error("Could not read response from TCS.")
    
    def __str__(self):
        return str(self.value)

class SlowCommandFailed(Exception):
    def __init__(self, value):
        self.value = value
        log.error("Slow command returned failure")
    
    def __str__(self):
        return str(self.value)



class Commands:
    '''Wrapper around the GXN/Telnet interface'''
    
    gxn_res = {0: "Success", -1: "Unknown command", -2: "Bad parameter", 
        -3: "Aborted", -6: "Do not have control"}
    
    def __init__(self):
        log.info("GXN Interface initalizing")

    
    def close(self):
        log.info("Closing ")
        
    def __del__(self):
        self.close()
        
    def write(self, str, slow=False):
        T = telnetlib.Telnet("pele.palomar.caltech.edu", 49300) 
        log.debug("Sending '%s'" % str.rstrip())
        T.write(str)
        
        if slow: return T
        
        T.close()
        
    def read_until(self, s,timeout):
        T = telnetlib.Telnet("pele.palomar.caltech.edu", 49300) 
        try:
            r=T.read_until(s, timeout)
        except Exception as e:
            T.close()
            raise TCSReadError(e)
        log.info("GXN Cmd returned: '%s'" % r.rstrip())
        T.close()
        
    def slow(self, timeout, T):
        '''Handle a slow command block until timeout'''
        # A slow command is defined by John Henning as a blocking command.
        log.info("Handling slow command")
        try:
            r = T.expect(["-?\d"], timeout)[2]
        except Exception as e:
            T.close()
            log.error("GXN Slow command returned garbage")
            return
 
        log.info("Returned: %s" % r)
        try: res = int(r)
        except:
            log.error("GXN Command timed out")
            SlowCommandFailed("Time out")
            T.close()
            return
        
        log.info("GXN Slow command returned %i" % res)
        if res == 0:
            log.debug("GXN Executed command")
            T.close()
        else:
            log.error("GXN Command failed: %s" % self.gxn_res[res])
            T.close()
            raise SlowCommandFailed("%i: %s" % (res, self.gxn_res[res]))

        
    def pt(self, dRA, dDec):
        '''PT (Slow) offsets the telescope by requested amount at MRATES rates.
        Telescope_Motion_Status must be TRACKING or IN_POSITION and changes to
        MOVING during move.'''
        log.info("GXN: pt %f %f" % (dRA, dDec))
                
        T = self.write("pt %f %f\n" % (dRA, dDec), slow=True)
        self.slow(60, T)
    
    def takecontrol(self):
        '''Send takecontrol command'''
        log.info("GXN takecontrol")
        self.write("takecontrol\n")
        self.read_until("\n", .1)
        
        
    def telinit(self):
        '''Send telinit command, block for 300 s'''
        
        log.info("GXN telinit")
        T = self.write("telinit\n", slow=True)
        return self.slow(300, T)
    
    def stow_flats(self):
        '''Stow to flat position, block for 300 s'''
        
        log.info("GXN stow flats")
        T = self.write("stow 0.0 85.0 90\n", slow=True)
        return self.slow(300, T)
    
    def stow_twilight(self):
        '''Stow to flat position, block for 300 s'''
        
        log.info("GXN stow flats")
        T = self.write("stow 0.0 85.0 355\n", slow=True)
        return self.slow(300, T)
    
    def lamps_on(self):
        log.info("GXN lamp on")
        T = self.write("lampon\n", slow=True)
        time.sleep(1)
        self.slow(30, T)
 
    
    def stop(self):
        log.info("GXN stop")
        self.write("stop\n")
        self.read_until("\n", .1)
           
    def lamps_off(self):
        log.info("GXN lamp off")
        self.write("lampoff\n")
        self.read_until("\n", .1)
        
    def open_dome(self):
        log.info("GXN open dome")
        T=self.write("open\n", slow=True)
        self.slow(300,T)
    
    def close_dome(self):
        log.info("GXN close dome")
        T = self.write("close\n", slow=True)
        self.slow(300,T)
    
    def gofocus(self, pos_mm):
        log.info("GXN Set focus stage to %2.3f" % (pos_mm))
        
        T=self.write("gofocus %3.6f\n" % pos_mm, slow=True)
        self.slow(30,T)
        
        
    def coords(self, ra, # in decimal hours
                    dec, # in decimal degrees
                    equinox, # 0 means apparent
                    ra_rate, dec_rate, 
                    flag, # adjusts rates. 0: 0.0001sec/yr, 1,2: as/hr
                    epoch=None,
                    name=None): # for non sidereal
        '''From Henning:
        COORDS (FAST) accepts information to specify a TARGET Position.  If no 
non-sidereal motion needs to be specified, parameters 6&7 may be omitted.  
Parameters: 
(1) Right Ascension in decimal hours;
(2) Declination in decimal degrees;
(3) Equinox of coordinates in decimal years -- zero means apparent; 
(4) RA rate: 0.0001sec/yr if flag (see parameter 6) is 0, arcsec/hr if 
flag is 1, sec/hr if flag is 2;
(5) Dec rate: 0.001 arcsec/yr if flag is 0, arcsec/hr if flag is 1 or 2;
[(6) Motion flag: 0=proper motion, which is the default if this parameter 
is absent; 1=non-sidereal rates (RA spatial rate), 2=non-sidereal rates 
(RA angular rate);
[(7) Epoch of coordinates for non-sidereal targets in decimal hours
(current UTC if omitted).]]
'''
        try: aRa = Angle(ra)
        except: aRa = Angle("%f h" % ra)
        try: aDec = Angle(dec)
        except: aDec = Angle("%f d" % dec)
        
        hRA  = aRa.hour
        dDec = aDec.deg
        
        log.info("GXN coords")
        
        if name is None:
            nm = ""
        else:
            nm = '"%s"' % name
            
        if epoch is not None:
            self.write("coords %f %f %f %f %f %i %f %s\n" %
                (hRA, dDec, equinox, ra_rate, dec_rate, flag, epoch,
                    nm))
        else:
            self.write("coords %f %f %f %f %f %i %s\n" %
                (hRA, dDec, equinox, ra_rate, dec_rate, flag, nm))
        
        self.read_until("\n", .1)
    
    
    def go(self):
        log.info ('GXN.gopos')
        T = self.write('gopos\n', slow=True)
        return self.slow(300, T)
    
    def stow_day(self):
        '''Daystow, block for 300 s'''
        
        log.info('GXN daystow')
        T = self.write("stow 3.6666666666 50.0 40\n", slow=True)
        
        return self.slow(300, T)        
    
class CommsThread(Thread):
    abort = False

    telescope = None
            
    def run(self):       
        T = self.telescope 
        while not self.abort:
            try:
                Tel = telnetlib.Telnet("pele.palomar.caltech.edu", 49300) 
                Tel.write("?POS\n")
            except Exception as e:
                raise TCSReadError(e)
                
            while True:

                r= Tel.read_until("\n", .1)
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

            Tel.close()
            time.sleep(2)

class Telescope(HasTraits):
    comms_thread = Instance(CommsThread)
    
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
        log.info("Telescope status thread initialized")


        self.comms_thread = CommsThread()
        self.comms_thread.telescope = self            
        





class GenericCommsThread(Thread):
    abort = False
    resultobj = None
    
    def run(self):
        
        R = self.resultobj
        log.info("Starting a communications thread")

        while not self.abort:
            try:
                Tel = telnetlib.Telnet("pele.palomar.caltech.edu", 49300) 
                Tel.write("%s\n" % self.command)
            except Exception as e:
                raise TCSReadError(e)
                
            while True:

                r= Tel.read_until("\n", .1)
                
                if r == "":
                    break               

                try:lhs,rhs = r.rstrip().split("=")
                except: continue
                
                try:
                    type_fun = type(getattr(R, lhs))
                    setattr(R, lhs, type_fun(rhs))
                except:
                    log.info("Ignored malformed line:'%s'" % r.rstrip())
                    
            Tel.close()
            time.sleep(2)
            
                
        
class WeatherCommsThread(GenericCommsThread):
    abort = False
    command = "?WEATHER"



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
    comms_thread = Instance(WeatherCommsThread)
    
    def __init__(self):
        log.info("Weather status thread initalized")
        self.comms_thread = WeatherCommsThread()
        self.comms_thread.resultobj = self


class StatusCommsThread(GenericCommsThread):
    abort = False
    command = "?STATUS"


class Status(HasTraits):
    UTC = String()
    Telescope_ID = Int()
    Telescope_Control_Status = String()
    Lamp_Status = String()
    Lamp_Current = Float()
    Dome_Shutter_Status = String()
    WS_Motion_Mode = String()
    Dome_Motion_Mode = String()
    Telescope_Power_Status = String()
    Oil_Pad_Status = String()
    Weather_Status = String()
    Sunlight_Status = String()
    Remote_Close_Status = String()
    Telescope_Ready_Status = String()
    HA_Axis_Hard_Limit_Status = String()
    Dec_Axis_Hard_Limit_Status = String()
    Focus_Hard_Limit_Status = String()
    Focus_Soft_Up_Limit_Value = Float()
    Focus_Soft_Down_Limit_Value = Float()
    Focus_Soft_Limit_Status = String()
    Focus_Motion_Status = String()
    East_Soft_Limit_Value = Float()
    West_Soft_Limit_Value = Float()
    North_Soft_Limit_Value = Float()
    South_Soft_Limit_Value = Float()
    Horizon_Soft_Limit_Value = Float()
    HA_Axis_Soft_Limit_Status = String()
    Dec_Axis_Soft_Limit_Status = String()
    Horizon_Soft_Limit_Status = String()
    comms_thread = Instance(StatusCommsThread)
    
    def __init__(self):
        log.info("Status thread initalized")
                    
        self.comms_thread = StatusCommsThread()
        self.comms_thread.resultobj = self
    
        

class StatusThreads():
    '''
    Maintains the status watching threads and provides convenience wrappers
    around them.
    '''
    telescope  = None
    weather = None
    status = None
    started = False
    
    def __init__(self):
        log.info("StatusThreads initialized")
        self.telescope = Telescope()
        self.weather = Weather()
        self.status = Status()
    
    def start(self):
        
        if not self.started:
            log.info("Starting threads")
            self.telescope.comms_thread.start()
            self.weather.comms_thread.start()
            self.status.comms_thread.start()
            self.started = True
    
    def stop(self):
        if self.started:
            self.telescope.comms_thread.abort= True
            self.weather.comms_thread.abort= True
            self.status.comms_thread.abort= True
            self.started = False
        
        self.telescope.UTC = self.weather.UTC = self.status.UTC = ''
