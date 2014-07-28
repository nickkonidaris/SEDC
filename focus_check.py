import numpy as np
import pylab as pl
import pyfits as pf

def analyize_files(files):
    
    focuss = []
    metric =[]
    q1 = []
    q2 = []
    q3 = []
    q4 = []
    
    for file in files:
        print file
        f = pf.open(file)
        PHDU = f[0]
        
        header,data = PHDU.header, PHDU.data
        try: focus = header["IFUFOCUS"]
        except: continue
        
        focuss.append(focus)
        sort = np.sort(data.flatten())
        s1 = np.sort(data[:1024,:1024].flatten())
        s2 = np.sort(data[:1024,1024:].flatten())
        s3 = np.sort(data[1024:,:1024].flatten())
        s4 = np.sort(data[1024:,1024:].flatten())
        
        a,b = np.floor(len(sort)*.03), np.ceil(len(sort)*.9999)
        
        
        
        print file, sort[a],sort[b],(sort[b]-sort[a])/np.median(sort)
        metric.append(sort[b]-sort[a])
        
        a = np.floor(1024*1024*.01)
        b = np.floor(1024*1024*.99)
        
        q1.append(s1[b]-s1[a])
        q2.append(s2[b]-s2[a])
        q3.append(s3[b]-s3[a])
        q4.append(s4[b]-s4[a])
        
        
        
    return  focuss, metric, q1, q2, q3, q4