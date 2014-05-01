import subprocess as SP
import psutil
import time



epy = "c:/users/sedm/appdata/local/enthought/canopy/user/scripts/python.exe"
sedmpy = "C:/Users/sedm/Dropbox/Python-3.3.0/PCbuild/amd64/python.exe"

rc_server_address    = 'http://127.0.0.1:9001'
ifu_server_address   = 'http://127.0.0.1:9002'
tel_server_address   = 'http://127.0.0.1:9003'
stage_server_address = 'http://127.0.0.1:9004'



def list_ds9s():
    startupinfo = SP.STARTUPINFO()
    startupinfo.dwFlags |= SP.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = SP.SW_HIDE

    p = SP.Popen("c:/ds9/xpaaccess.exe -v ds9", startupinfo=startupinfo, stdout=SP.PIPE)
    res = p.stdout.read()

    if res == '': return []
    xpa_methods = res.rstrip().split("\n")
    return xpa_methods


def check_and_start_ds9():
    '''Checks to see if two ds9s are running. If not, start them.
    
    Calls list_ds9() to return a list of running ds9 instances. IFU
    will use the second running ds9 and the RC will use the first.
    
    On windows xpans must be running for the xpa_method list to be activated.
    
    Returns:
        [] of XPA Methods to the running ds9s'''
    startupinfo = SP.STARTUPINFO()
    startupinfo.dwFlags |= SP.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = SP.SW_HIDE

    xpans_running = "xpans.exe" in [psutil.Process(i).name for i in psutil.get_pid_list()]
    
    if not xpans_running:
        print "xpans not running."
        SP.Popen("c:/ds9/xpans", startupinfo=startupinfo)
    
    methods = list_ds9s()
    
    if len(methods) == 0:
        print "No ds9s running"
        p1=SP.Popen("c:/ds9/ds9", startupinfo=startupinfo)
        p2=SP.Popen("c:/ds9/ds9", startupinfo=startupinfo)
        pids = [p1,p2]
        time.sleep(5)
    elif len(methods) == 1: 
        print "one ds9 running"
        p1 = SP.Popen("c:/ds9/ds9", startupinfo=startupinfo)
        pids = [p1]
        time.sleep(3)


    return list_ds9s()