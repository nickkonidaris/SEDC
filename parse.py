import astropy
import astropy.io.ascii
from astropy.coordinates.angles import Angle
from astropy.table import Table
import numpy as np
import GXN


def parse_file2(fname):
    f = open(fname)
    lines = f.readlines()
    f.close()


    names = []
    ras = []
    decs = []
    epochs = []
    comments = []
    for line in lines:
        if line[0] == '#': continue
        sp = line.split()
        if len(sp) < 8:
            continue

        name = sp[0]
        ra = sp[1:4]
        dec = sp[4:7]
        epoch = sp[7]
        comment = sp[8:]

        #print sp
        ra = Angle("%sh%sm%ss" % (ra[0], ra[1], ra[2]))
        dec = Angle("%sd%sm%ss" % (dec[0], dec[1], dec[2]))
        names.append(name)

        ras.append(ra.hour)
        decs.append(dec.degree)
        epochs.append(epoch)
        comments.append(comment)
    
    t = Table([names, ras, decs, epochs, comments], 
        names=('name', 'ra', 'dec', 'epoch', 'comment'))

    return t

def parse_file(fname):
    sc = astropy.io.ascii.convert_numpy(np.str)
    data = astropy.io.ascii.read("lines.txt", delimiter="\t", comment='#',
        guess=False)
        #converters={'name': sc, 'ra': sc, 'dec': sc, 'comment': sc})

    return data

def convert_file(data):
    
    lines = []
    for datum in data:
        print datum
        ra = Angle(datum['ra'], unit='h')
        dec = Angle(datum['dec'], unit='deg')
        epoch = datum['epoch']
        comment = datum['comment']

        lines.append("%15s %14s %14s %6s %s" % (datum['name'],
            ra, dec, epoch, " ".join(comment)))

    return lines 
        

#data = parse_file2("lines.txt")

