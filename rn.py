# Measure RN of bias frames

import numpy as np
import pyfits as pf


def measure_rn(fnames):
    
    
    f = pf.open(fnames[0])[0]
    h,A = f.header, f.data
    
    
    rns = []
    for fname in fnames[1:]:
        
        f = pf.open(fname)[0]
        h,d = f.header, f.data
        
        
        rns.append(np.std((A-d).flatten()) * h["gain"]/np.sqrt(2))
    
    print rns
    print "Read noise is %3.2f+-%3.2f" % (np.mean(rns), np.std(rns))