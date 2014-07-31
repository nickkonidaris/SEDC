import numpy as np
import pylab as pl
import pyfits as pf
import time as t
import numpy as np


def focus_loop(stage_control, ifu_control, focus_pos=np.arange(3.0,3.7,.1)):
    
    name = ifu_control.getall()[1] # 2nd element is object name
    
    def waitfor():
        t.sleep(3)
        while not stage_control.get_is_ready():
            t.sleep(.2)
    
    print "Starting focus loop"
    stage_control.request_focus(True)

    
    if not stage_control.get_is_ready():
        print "Stage not homed"
        return    
    files = []
    
    for pos in focus_pos:
        print "Moving to %f...." % pos
        stage_control.set_target(float(pos))
        stage_control.go()
        t.sleep(10)

        waitfor()
#
        print "..Moved to %f" % pos
        ifu_control.setreadout(2)
        ifu_control.setshutter('normal')
        ifu_control.setobject("%s - IFU Focus: %s" % (name, pos))
        ifu_control.go()

        while ifu_control.isExposing():
            t.sleep(0.2)
        
        files.append(ifu_control.getfilename())
        
    stage_control.request_focus(False)
    ifu_control.setobject(name)
    print files
    
    return files


def analyze(files):
    '''Measures a focus metric on the list of files 
    '''    
    focuss = []
    metric =[]
    q1 = []
    q2 = []
    q3 = []
    q4 = []
    qc = []
    mns =[]
    
    for file in files:
        print file
        f = pf.open(file)
        PHDU = f[0]
        
        header,data = PHDU.header, PHDU.data
        try: 
            focus = header["object"]
            print focus
            focus = float(focus.split(":")[-1])
        except: continue
        
        focuss.append(focus)
        sort = np.sort(data.flatten())
        s1 = np.sort(data[:1024,:1024].flatten())
        s2 = np.sort(data[:1024,1024:].flatten())
        s3 = np.sort(data[1024:,:1024].flatten())
        s4 = np.sort(data[1024:,1024:].flatten())
        sc = np.sort(data[512:1536,500:1536].flatten())
        
        a,b = np.floor(len(sort)*.001), np.ceil(len(sort)*.999)
        
    
        print file, sort[a],sort[b],(sort[b]-sort[a])/np.median(sort)
        metric.append(sort[b]-sort[a])
        
        a = np.floor(1024*1024*.01)
        b = np.floor(1024*1024*.99)
        
        q1.append(s1[b]-s1[a])
        q2.append(s2[b]-s2[a])
        q3.append(s3[b]-s3[a])
        q4.append(s4[b]-s4[a])
        qc.append(sc[b]-sc[a])
        mns.append(np.mean(s4))
        
        

    pl.ion()
    pl.figure(100)
    pl.clf()
    pl.plot(focuss, metric, 'o')
    pl.show()
    return  focuss, metric, q1, q2, q3, q4, mns
