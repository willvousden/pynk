#!/usr/bin/env python
import sys
import argparse
import iso8601
import numpy
import scipy.interpolate
import scipy.optimize
import math
from pylab import *
from lxml import etree

parser = argparse.ArgumentParser(description='Do some stuff.')
parser.add_argument('gps', metavar='FILE', type=argparse.FileType('rw'), help='The TCX file to augment with power data.')
parser.add_argument('power', metavar='FILE', type=argparse.FileType('r'), help='The TCX file containing the power data.')
args = parser.parse_args()

ns = { 'tcx': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2',
       'ext': 'http://www.garmin.com/xmlschemas/ActivityExtension/v2' }

# Get speed data from GPS file.
ts1 = [ ]
vs1 = [ ]
gps = etree.parse(args.gps)
for trackpoint in gps.xpath('//tcx:Trackpoint', namespaces=ns):
    t = iso8601.parse_date(trackpoint.xpath('.//tcx:Time', namespaces=ns)[0].text)
    v = float(trackpoint.xpath('.//ext:Speed', namespaces=ns)[0].text)
    ts1.append(t)
    vs1.append(v)
gpsStartTime = ts1[0]

# Get power data (including speed).
ts2 = [ ]
vs2 = [ ]
Ps2 = [ ]
power = etree.parse(args.power)
for trackpoint in power.xpath('//tcx:Trackpoint', namespaces=ns):
    t = iso8601.parse_date(trackpoint.xpath('.//tcx:Time', namespaces=ns)[0].text)
    v = float(trackpoint.xpath('.//ext:Speed', namespaces=ns)[0].text)
    P = float(trackpoint.xpath('.//ext:Watts', namespaces=ns)[0].text)
    ts2.append(t)
    vs2.append(v)
    Ps2.append(P)
powerStartTime = ts2[0]

# Calculate the offset from the first track point in seconds.
dts1 = numpy.array([ (t - gpsStartTime).total_seconds() for t in ts1 ])
dts2 = numpy.array([ (t - powerStartTime).total_seconds() for t in ts2 ])

# Convert them to numpy arrays.
vs1 = numpy.array(vs1)
vs2 = numpy.array(vs2)
Ps2 = numpy.array(Ps2)

vInterpolation = scipy.interpolate.interp1d(dts1, vs1)
minDt, maxDt = min(dts1), max(dts1)
def residuals(dt0):
    result = []
    for dt, v in zip(dts2, vs2):
        x = dt - dt0
        if x > minDt and x < maxDt:
            result.append(vInterpolation(x) - v)
    return numpy.array(result)
    #return numpy.array([ vInterpolation(dt - dt0) for dt in vs2Restricted ]) - vs2Restricted
    #return vInterpolation(x - dt0) - y

def meanSquareResidual(dt0):
    rs = residuals(dt0)
    return sum(rs ** 2) / len(rs) ** 2

optS = None
optdt = None
for x in numpy.linspace(20.6, 20.7, 5):
    S = meanSquareResidual(x)
    if optS == None or optS > S:
        optS = S
        optdt = x
        #print x, S

#print optdt
#plot(dts1, vs1)
#plot(dts2 - optdt, vs2)
#show()

# Now re-write the XML file!
dts2 -= optdt
PInterpolation = scipy.interpolate.interp1d(dts2, Ps2)

#plot(dts1, vs1)
#plot(dts2 - optdt, vs2)
#show()

Ps1 = []
for trackpoint in gps.xpath('//tcx:Trackpoint', namespaces=ns):
    t = (iso8601.parse_date(trackpoint.xpath('.//tcx:Time', namespaces=ns)[0].text) - gpsStartTime).total_seconds()

    try:
        P = float(PInterpolation(t))
    except ValueError:
        P = 0

    Ps1.append(P)
    tpx = trackpoint.xpath('.//ext:TPX', namespaces=ns)[0]
    watts = etree.SubElement(tpx, 'Watts')
    watts.text = '%f' % P
    #print etree.tostring(tpx)

#Ps1 = numpy.array(Ps1)
#plot(dts1, Ps1/100)
#plot(dts1, vs1)
#show()

#print '<?xml version="1.0"?>'
print etree.tostring(gps, pretty_print=True, xml_declaration=True)
