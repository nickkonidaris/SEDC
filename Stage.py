# -*- coding: utf-8 -*-

import serial as ps
import math, time
import logging as log
import pdb
import os

from SimpleXMLRPCServer import SimpleXMLRPCServer

    
    

class IFU:
    '''Integral field unit focus stage'''
    
    portno = -1
    c = None # Serial object to open port
    ADDY = "1"
    cur_pos = -99
    
    error_msgs = {
            "A": "Unknown message code or floating point controller address",
            "B": "Controller address not correct",
            "C": "Parameter missing or out of range",
            "D": "Execution not allowed",
            "E": "Home sequence already started",
            "G": "Target position out of limits",
            "H": "Execution not allowed in NOT REFERENCED state",
            "I": "Execution not allowed in CONFIGURATION state",
            "J": "Execution not allowed in DISABLE state",
            "K": "Execution not allowed in READY state",
            "L": "Execution not allowed in HOMING state",
            "M": "Execution not allowed in MOVING state",
            "@": "Ok."}
    
    def __init__(self):
        '''Open SMC100 com port portname'''
        
        portname = 'com10'
        if portname[0:3] != 'com':
            return "Portname must be in comN format"
        
        self.portno = int(portname[3:])
        
        log.info("Instantiated stage on port %s" % portname)
        self.ID = self.send_cmd_recv_msg("id?")
        if self.ID == '':
            log.error("Could not receive ID from stage. Comms error")
            raise Exception("Stage does not respond. ")
        log.info("Stage is '%s'" % self.ID)
        
    def __open(self):
        log.debug("opening port...")
        try: self.c = ps.Serial(self.portno-1, 
            baudrate=57600, 
            bytesize=ps.EIGHTBITS, 
            parity=ps.PARITY_NONE, 
            stopbits=ps.STOPBITS_ONE, 
            timeout=5, 
            xonxoff=True,
            rtscts=False,
            dsrdtr=False)
        except ps.SerialException:
            log.error("Could not open serial port, it may be disconnected or power off")
            raise ps.SerialException
            
        log.debug("Opened port %s" % self.c.name)
        log.debug(self.c)
    
    def __close(self):
        log.debug("Closing port %s" % self.c.name)
        self.c.close()
        self.c = None

    def __send_and_recv(self, msg):
        log.info("Sending message: %s", msg)
        self.__open()
        nw = self.c.write(msg + "\r\n")
        log.debug("tx(%i)[%s]" % (nw, msg))
        #self.c.flush()
        time.sleep(0.2)
        rb = 0
        recv = ""
        while self.c.inWaiting() > 0:
            rb += self.c.inWaiting()
            rv = self.c.read(self.c.inWaiting())
            log.debug("rv(%i)[%s]" % (rb, rv))
            recv += rv

        
        self.__close()
        return recv
        
    def get_error(self):
        str = self.send_cmd_recv_msg("tb?")
        log.info("Checking error message: '%s'" % str)
        if len(str) == 1: return "No error message"
        cmd, msg = str.split("TB")
        msg = msg.rstrip()
        
        return msg
    
    def get_state(self):
        errstate = self.send_cmd_recv_msg("ts?")
        state = errstate[-2:]
        
        msg = {
            "0A": "NOT REFERENCED from reset.",
            "0B": "NOT REFERENCED from HOMING.",
            "0C": "NOT REFERENCED from CONFIGURATION.",
            "0D": "NOT REFERENCED from DISABLE.",
            "0E": "NOT REFERENCED from READY.",
            "0F": "NOT REFERENCED from MOVING.",
            "10": "NOT REFERENCED ESP stage error.",
            "11": "NOT REFERENCED from JOGGING.",
            "14": "CONFIGURATION.",
            "1E": "HOMING commanded from RS-232-C.",
            "1F": "HOMING commanded by SMC-RC.",
            "28": "MOVING.",
            "32": "READY from HOMING.",
            "33": "READY from MOVING.",
            "34": "READY from DISABLE.",
            "35": "READY from JOGGING.",
            "3C": "DISABLE from READY.",
            "3D": "DISABLE from MOVING.",
            "3E": "DISABLE from JOGGING.",
            "46": "JOGGING from READY.",
            "47": "JOGGING from DISABLE."
        }
        print msg.get(state,"No such state?")
        log.info("%s: %s" % (state,msg.get(state, "No such state?")))
        
        return state, msg.get(state, "Unknown state??")
    
    
    def error_level(self):
        state = self.get_error()
        return state[0]
    
    def is_error(self):
        ''' Is the stage reporting an error'''
        err = self.get_error()
        if err == "@ No error":
            return False
        else:
            print err
            return True
    
    def is_ready(self):
        ''' Is the state of the stage READY?'''
        state, statename = self.get_state()

        return (state == '32') or (state == '33') or (state == '34') or (state == '35')
    
    def is_not_ref(self):
        ''' Is the state of the stage NOT REF?'''

        s, statename = self.get_state()
        if (s == '0A') or (s == '0B') or (s == '0C') or (s == '0D') or (s == '0E') or (s == '0F') or (s == '10') or (s == '11'):
            return True
        else: return False
            
    def is_moving(self):
        ''' Is the state of the stage MOVING?'''
        return self.get_state()[0] == '28'
        
    def is_configuration(self):
        ''' Is the state of the stage CONFIGURATION?'''
        return self.get_state()[0] == '14'
    
    def stored_position(self): return self.cur_pos
    
    def position_query(self):
        str = self.send_cmd_recv_msg("tp?")
        log.info("Queried position %s" % str)
        cmd, pos = str.split("TP")
        
        self.cur_pos = float(pos)
        return float(pos)
        
    def home(self):
        log.info("homing")
        
        if self.is_ready():
            log.info("Stage already homed")
            print "Staged already homed"
            return self.position_query()
            
        self.send_cmd_recv_msg("OR")
        lvl = self.error_level()
        msg = self.error_msgs.get(lvl, "Unknown error code")
        
        log.info(msg)
        print(msg)

        if lvl != "@": return self.position_query()

        while not self.is_ready():
            pos = self.position_query()
            print "Current position: % 2.3f" % pos

        
        log.info("home complete")
        return pos
        
        
    def move_unblocked(self, target):
        """ Move stage to target mm"""
        log.info("unblocked Moving stage to %f" % target)
        
        if (target < 0) or (target> 5):
            return False
        
        if not self.is_ready():
            print "Stage is not ready"
            log.info("Controller not ready for move, abort.")
            return False
 
        self.send_cmd_recv_msg("pa%f" % target)
        lvl = self.error_level()
        msg = self.error_msgs.get(lvl, "Unknown error code")
        
        log.info(msg)

        
        return True

        
    def moveto(self, target):
        """ Move stage to target mm"""
        log.info("Moving stage to %f" % target)
        
        if (target < 0) or (target> 5):
            return False
        
        if not self.is_ready():
            print "Stage is not ready"
            log.info("Controller not ready for move, abort.")
            return False
 
        self.send_cmd_recv_msg("pa%f" % target)
        lvl = self.error_level()
        msg = self.error_msgs.get(lvl, "Unknown error code")
        
        log.info(msg)

        if lvl != "@": return
        
        pos = self.position_query()
        while self.is_moving():
            print "%f-%f=%f" % (pos,target,pos-target)
            pos = self.position_query()
        
        if math.fabs(pos-target) > 0.005:
            log.info("Stage at %f instead of %f" % (pos, target))
            print("Stage did not achieve commanded position")
            return False
        
        return True
        


    def disable(self): self.send_cmd_recv_msg("MM0")
    def enable(self): self.send_cmd_recv_msg("MM1")
    def configuration(self): self.send_cmd_recv_msg("PW1")
    def un_configuration(self): self.send_cmd_recv_msg("PW0")
    def __reset(self): 
        self.send_cmd_recv_msg("RS")
        time.sleep(5)
    
    def reset_stage(self):
        log.info("Setting stage parameters")
        f = self.send_cmd_recv_msg

        vals = ["AC0.1", "VA0.15", "JR0.04", "SL0.0", "SR5"]
        
        self.__reset()
        self.configuration()
                
        if not self.is_configuration():
            log.info("Not in configuration state")
            print("Not in configuration state")
            return False
            
            
        for val in vals:
            f(val)
            if self.is_error():
                log.error("Could not set param %s" % val)
                return False


        self.un_configuration()
        self.enable()
        
        if self.is_not_ref(): return False
        log.info("Stage should be NOT REF but is in state: %s" % self.get_state())

    
    def send_cmd_recv_msg(self, cmd):
        recv = self.__send_and_recv(self.ADDY + cmd)
        return recv.rstrip()

if __name__ == "__main__":
    
    print "Logging to c:/sedm/logs/stage.txt"

    log.basicConfig(filename="C:\\sedm\\logs\\stage.txt",
        format="%(asctime)s-%(filename)s:%(lineno)i-%(levelname)s-%(message)s",
        level = log.INFO)
    
    log.info("*************************RESTARTING************************")
    
    server = SimpleXMLRPCServer(("localhost", 8000), logRequests=True)

    server.register_instance(IFU())
    
    os.system("title Stage Control %i" % os.getpid())
    server.serve_forever()
    

    
# The Commands from SMC100 user manual:
'''
AC    Set/Get acceleration 
BA  Set/Get backlash compensation 
BH  Set/Get hysteresis compensation 
DV  Set/Get driver voltage Not for PP
FD   Set/Get low pass filter for Kd Not for PP
FE   Set/Get following error limit Not for PP
FF   Set/Get friction compensation Not for PP
FR  Set/Get stepper motor configuration Not for CC
HT  Set/Get HOME search type 
ID  Set/Get stage identifier 
JD  Leave JOGGING state 
JM    Enable/disable keypad 
JR    Set/Get jerk time 
KD   Set/Get derivative gain Not for PP
KI   Set/Get integral gain Not for PP
KP   Set/Get proportional gain Not for PP
KV   Set/Get velocity feed forward Not for PP
MM   Enter/Leave DISABLE state 
OH  Set/Get HOME search velocity 
OR  Execute HOME search 
OT  Set/Get HOME search time-out 
PA  Move absolute 
PR  Move relative 
PT    Get motion time for a relative move 
PW   Enter/Leave CONFIGURATION state 
QI  Set/Get motor’s current limits 
RA       Get analog input value 
RB       Get TTL input value 
RS    Reset controller 
SA  Set/Get controller’s RS-485 address 
SB     Set/Get TTL output value 
SC   Set/Get control loop state Not for PP
SE  Configure/Execute simultaneous started move 
SL    Set/Get negative software limit 
SR    Set/Get positive software limit 
ST    Stop motion 
SU  Set/Get encoder increment value Not for PP
TB       Get command error string 
TE      Get last command error 
TH       Get set-point position 
TP       Get current position 
TS       Get positioner error and controller state 
VA    Set/Get velocity 
VB    Set/Get base velocity Not for CC
VE       Get controller revision information 
ZT      Get all axis parameters 
ZX  Set/Get SmartStage configuration '''
