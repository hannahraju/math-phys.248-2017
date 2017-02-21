import json as js
import pprint as pp
import os as os
import fnmatch as fn
import datetime as dt

from operator import attrgetter
from collections import defaultdict
from collections import namedtuple
from pathlib import Path

print("Loading the VicPD library.")

sfile = Path("../data/vic_crimereports.json")
if (sfile.is_file()==False):
    print("data/vic_crimereports.json does not exist.  Please unzip crimereports.zip")
    exit()
        
with open('../data/vic_crimereports.json') as data_file:    
    pdata = js.load(data_file)

## reverse-lookup for defining our reduced data set. 
RLU = dict([(pdata['meta']['view']['columns'][x]['name'], x) for x in range(28)])

keepFields = ['latitude', 'longitude', 'incident_type_primary', 'case_number',\
              'incident_datetime','address_1', 'created_at', 'updated_at',\
              'parent_incident_type']

pdatt = namedtuple('pdatt', keepFields)

def isfloat(value):
  try:
    float(value)
    return True
  except ValueError:
    return False

cdata = []
for x in pdata['data']:
    ## convert to dictionary
    tdict = dict([(y, x[RLU[y]]) for y in keepFields])
    
    ## check to see if any terms undefined
    nexists = False
    for key, value in tdict.items():
        if value==None:
            nexists = True
    ## let's ignore the records with no location data. 
    if nexists==True: 
        continue
            
    ## convert the numbers to floats
    if isfloat(tdict['latitude']):
        tdict['latitude'] = float(tdict['latitude'])
    else:
        print("Invalid lat.")
        continue
    if isfloat(tdict['longitude']):
        tdict['longitude'] = float(tdict['longitude'])
    else:
        print("Invalid long.")
        continue
    
    ## and the dates to python datetime objects
    tdict['incident_datetime'] = dt.datetime.strptime(tdict['incident_datetime'],\
                                            '%Y-%m-%dT%H:%M:%S')
    tdict['created_at'] = dt.datetime.strptime(tdict['created_at'],\
                                            '%Y-%m-%dT%H:%M:%S')
    tdict['updated_at'] = dt.datetime.strptime(tdict['updated_at'],\
                                            '%Y-%m-%dT%H:%M:%S')
   
    ## convert dict to pdatt
    pdat = pdatt(**tdict)
    cdata.append(pdat)


## let's get the earliest and most recent records, respectively. 
date_cdate = sorted(cdata, key = attrgetter('incident_datetime'))
print("[cdata] ", (date_cdate[-1].incident_datetime - date_cdate[0].incident_datetime).days//365,\
      " years and ", (date_cdate[-1].incident_datetime - date_cdate[0].incident_datetime).days % 365,\
      " days of crime data. ", len(cdata), " records total.", sep='')

## let's tabulate the "Crime Types" as a structure. 
ctypes = defaultdict(set)
for x in cdata:
    if x.parent_incident_type in ctypes.keys():
        ctypes[x.parent_incident_type].add(x.incident_type_primary)
    else:
        ctypes[x.parent_incident_type] = set([x.incident_type_primary])

print("[ctypes] tree structure of crime types")
#pp.pprint(ctypes)

## Let's do a more detailed frequency analysis of the crime types.  

tot = 0
all_tots = defaultdict(int)
for x in cdata:
    tot += 1
    all_tots[x.parent_incident_type] += 1
    all_tots[(x.parent_incident_type, x.incident_type_primary)] += 1

## compute the parent incident type frequencies
all_freq = defaultdict(float)

for x in ctypes.keys():
    all_freq[x] = 100*all_tots[x] / tot
    for y in ctypes[x]:
        all_freq[(x,y)] = 100*all_tots[(x,y)] / all_tots[x]

print("[all_tots] totals for crime types")
print("[all_freq] relative frequencies of crime types")

## let's write something that counts the occurances of a crime type 
## by the day of the week crtype can be a string, or a pair of 
## strings as in the above code
def weekdaycount(crtype):
    daycount = [0]*7
    if (isinstance(crtype, str)):
        for x in cdata:
            if x.parent_incident_type == crtype:
                daycount[x.incident_datetime.weekday()] += 1
    elif (isinstance(crtype, tuple)) and (len(crtype)==2) and\
         (isinstance(crtype[0], str)) and (isinstance(crtype[1], str)):
        for x in cdata:
            if x.parent_incident_type == crtype[0] and x.incident_type_primary == crtype[1]:
                daycount[x.incident_datetime.weekday()] += 1
    return daycount

def weekdaypct(crtype):
    wdk = weekdaycount(crtype)
    T = all_tots[crtype]
    return ['{:.1f}'.format(100*x/T) for x in wdk]

def presentBDWeek(crtype):
    retval = "Mon, Tue, Wed, Thu, Fri, Sat, Sun\n";
    retval += str(weekdaypct(crtype))
    return retval

print("[weekdaycount] loaded")
print("[weekdaypct] loaded")
print("[presentBDWeek] loaded")

files = fn.filter(os.listdir('../data'), "eng-daily*.csv")

## let's store the weather data as a dictionary. 

wdatlist = {}

for f in files:
    with open("../data/"+f) as fo:
        content = fo.readlines()
        for j in range(26, len(content)):
            ab = content[j].split(',')
            for k in range(len(ab)):
                ab[k] = ab[k].translate({ord(c): None for c in '"'})
            date = dt.date(int(ab[1]), int(ab[2]), int(ab[3]))
            if len(ab[5])>0 and len(ab[7])>0 and len(ab[9])>0 and len(ab[15])>0 and len(ab[17])>0:
                wdatlist[date] = ( float(ab[5]), float(ab[7]), float(ab[9]), float(ab[15]), float(ab[17]) )
            
## wdatlist[date] = (max, min, mean, rain cm, snow cm) 
print("[wdatlist] ",len(wdatlist.keys()) // 365, " years and ", len(wdatlist.keys()) % 365,\
      " days of weather data, dict of (max c, min c, mean c, rain cm, snow cm) indexed on date", sep='')

## let's find all the common dates with data, and put into one big array. 

## we have wdatlist dict dates -> triples
## and cdata a list of cstruc objects, that have datetimes. . .
## so we need to convert cdata to an object indexed by dates, containing counts of 
## everything that occured on those dates. 
comdates = []

ccdata = defaultdict(int)
for xd in cdata:
    ## only record if we have weather data
    if xd.incident_datetime.date() in wdatlist.keys():
        comdates.append(xd.incident_datetime.date())
        ccdata[(xd.incident_datetime.date(),xd.parent_incident_type, xd.incident_type_primary)] += 1

## takes as input parent_incident_type and incident_type primary, 
## builds list x,y coordinates of weather data, counts of crimes. 
## k = 0, 1, 2 for max min mean temps
def xyplot(pit, itp, k):
    x = [wdatlist[date][k] for date in comdates]
    y = [ccdata[(date, pit, itp)] for date in comdates]
    return x,y

print("VicPD library loaded.")