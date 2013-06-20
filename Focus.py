
import os
import numpy as np
import pyfits as pf


def rc_focus_check(last_n=5):
    
    path = "s:\\2013jun19\\"
    files = os.listdir(path)
    
    
    rcs = [f for f in files if f[0:2] == "rc"][-last_n:]
    
    fpos = []
    metrics = []
    for fn in rcs:
        f = os.path.join(path, fn)
        F = pf.open(f)
        
        dat,hdr = F[0].data, F[0].header
        sort = np.sort(dat.flatten())
        a,b = np.floor(len(sort)*.03), np.ceil(len(sort)*.97)
        metric = (sort[b]-sort[a])/np.median(sort)
        fpos.append(hdr["secfocus"])
        metrics.append(metric)
        
        print fn, hdr["secfocus"], metric
    
    return fpos, metrics