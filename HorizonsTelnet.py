
''' From http://stackoverflow.com/questions/19845525/accessing-a-telnet-session-in-python '''

import telnetlib
import os
import time
from astropy.coordinates import Angle
from collections import namedtuple
import numpy as np


def st_to_num(st):
    return st.tm_yday + st.tm_hour/24.0 + st.tm_min/(24.0*60.)

def find_neareast(obj_id=None, path='.'):

    results = return_ephem(obj_id, path)
        
    now = st_to_num(time.gmtime())    

    
    deltas = []
    for res in results:
        objtime = st_to_num(res.etime)
        deltas.append( now-objtime)

    deltas = np.array(deltas)
    
    ix = np.argmin(np.abs(deltas))
    return (results[ix].RA.hour, results[ix].Dec.deg, results[ix].dRA, 
        results[ix].dDec, results[ix].apmag)

def return_ephem(obj_id=None, path='.'):

    filepath = os.path.join(path, "%s.txt" % obj_id)    
    try:

        f = open(filepath, 'r')
        lines = f.readlines()
        f.close()
    except Exception, e:
        print "Couldn't read %s: %s" % (filepath, e)
    eline = namedtuple('ephemeris', 'etime RA Dec dRA dDec airmass apmag')    
    results = []
    in_data = False
    for line in lines:
        if line.startswith("$$SOE"): 
            in_data=True        
            continue
        if line.startswith("$$EOE"): 
            in_data=False
            continue
        
        if in_data: 
        
            etime  = time.strptime(line[0:18], " %Y-%b-%d %H:%M")
            RA = Angle("%s hour" % line[23:35])
            Dec = Angle("%s deg" % line[35:47])
            dRA = float(line[47:55])
            dDec = float(line[56:65])
            airmass = line[65:74]
            apmag = float(line[74:82])
            

            results.append(eline(etime, RA, Dec, dRA, dDec, airmass, apmag))
            

    return results
    

def write_ephemeris(obj_id=None, start_date=None, end_date=None, path='.'):
    '''Writes a file, obj_id.txt, with output from JPL's Horizon telnet.
    
    Args:
            obj_id: Unique object identifier
            start_date/end_date: Start/end date (e.g., 2014-jul-31 23:00)
    
    Result
    '''
    t = telnetlib.Telnet()
    t.open('horizons.jpl.nasa.gov', 6775)
    
    expect = ( ( r'Horizons>', '%i \n' % obj_id),
            ( r'Continue.*:', 'y\n' ),
            ( r'Select.*E.phemeris.*:', 'E\n'),
            ( r'Observe.*:', 'o\n' ),
            ( r'Coordinate center.*:', '675\n' ),
            ( r'Confirm selected station.*>', 'y\n'),
            ( r'Accept default output.*:', 'y\n'),
            ( r'Starting *UT.* :', '%s\n' % (start_date) ),
            ( r'Ending *UT.* :', '%s\n' % end_date ),
            ( r'Output interval.*:', '10m\n' ),
            ( r'Select table quant.* :', '1,3,8,9\n'),
            ( r'Scroll . Page: .*%', ' '),
            ( r'Select\.\.\. .A.gain.* :', 'X\n' )
    )
    
    with open('%i.txt' % obj_id, 'w') as fp:
        while True:
            try:
                answer = t.expect(list(i[0] for i in expect), 10)
            except EOFError:
                break
            fp.write(answer[2])
            fp.flush()
            t.write(expect[answer[0]][1])

if __name__ == '__main__':
    #write_ephemeris(obj_id=3028, start_date='2014-Jul-30 00:00',
     #   end_date='2014-Jul-31 23:00')
    find_neareast(obj_id=3028)
