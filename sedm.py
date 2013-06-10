
import serial as ps
import time

COM10 = 9

c = ps.Serial(COM10, 
    baudrate=57600,
    bytesize=8,
    parity='N',
    stopbits=1,
    timeout=1,
    xonxoff=True)
    
print c


#nw = c.write("1RS\r\n")
nw = c.write("1RS\n\r")
nw += c.write("1TP?\n\r")
print "%i bytes written" % nw

time.sleep(1)
while c.inWaiting() > 0:
    print c.read(c.inWaiting())
    time.sleep(1)


c.close()