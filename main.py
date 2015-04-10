#!/usr/bin/python2
from flask import Flask, abort, Response
import json
import logging
import random
import os
import sys
from boto import dynamodb2
from boto.dynamodb2.table import Table

reload(sys)
sys.setdefaultencoding("UTF-8")

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

exampleHotspotData = ""
try:
    with open("static/hotspot.json") as f:
        exampleHotspotData = "".join(f.readlines())
except:
    exampleHotspotData = {}

if 'dynamodb' in os.environ:
    ddb_conn = dynamodb2.connect_to_region(os.environ['aws_region'])
    count_table = Table(table_name=os.environ['count_table'],
                      connection=ddb_conn)

class DataGetter:
    def __init__(self, mapfile):
        with open("maps/%s" % mapfile) as f:
            self.countries = [x.replace("\n", "").replace("\r", "") for x in f.readlines()]
    def getData(self, time):
        data = {
            "countries": {},
            "cities": {}
        }
        for country in self.countries:
            data["countries"][country] = random.randrange(1000)
        return data

class DynamoDBDataGetter:
    def __init__(self, mapfile, entity, prefix=None, is_region=False):
        self.entity = entity
        self.is_region = is_region
        self.prefix = prefix
        with open("maps/%s" % mapfile) as f:
            self.countries = {}
            for x in f.read().splitlines():
                self.countries[x] = 1.0

    def getData(self, time):
        logging.info("get {1} data for time {0}".format(time, self.entity))
        countries = {}
        for country in self.countries:
            countries[country] = 0

        time_lower = time * 60000
        time_upper = (time + 1) * 60000
        logging.info("Fetching data over {0} to {1}".format(time_lower, time_upper))
        iterator = count_table.query_2(
            entity__eq=self.entity,
            ts__gte=time_lower,
            limit=60
        )

        cnt = 0
        for item in iterator:
            if int(item['ts']) > time_upper:
                continue

            if 'scale' in item:
                scale = float(item['scale'])
            else:
                scale = 1.0

            cnt += 1
            for key in item.keys():
                if key == 'entity' or key == 'ts' or key == 'scale':
                    continue
                if self.is_region:
                    if len(key) < 3:
                        name = self.prefix + '-' + key
                    elif key.startswith(self.prefix):
                        name = key
                    else:
                        continue
                else:
                    name = key
                if not name in self.countries:
                    continue
                if name in countries:
                    countries[name] += scale * float(item[key])
                else:
                    countries[name] = scale * float(item[key])

        logging.info("Fetched data over {0} to {1} total {2}".format(time_lower, time_upper, cnt))

        data = {
            "countries": countries,
            "cities": {}
        }

        return data

class DynamoDBLatLongGetter:
    def __init__(self):
        pass

    def getData(self, time, limit=50):
        time_lower = time * 60000
        time_upper = (time + 1) * 60000
        logging.info("Fetching latlongs over {0} to {1}".format(time_lower, time_upper))
        iterator = count_table.query_2(
            entity__eq="L",
            ts__gte=time_lower,
            limit=60
        )

        cnt = 0
        latlongs = {}
        for item in iterator:
            if int(item['ts']) > time_upper:
                continue

            if 'scale' in item:
                scale = float(item['scale'])
            else:
                scale = 1.0

            cnt += 1
            for key in item.keys():
                if key == 'entity' or key == 'ts' or key == 'scale':
                    continue
                if key in latlongs:
                    latlongs[key] += scale * float(item[key])
                else:
                    latlongs[key] = scale * float(item[key])

        srt = sorted(latlongs.values(), reverse=True)
        if len(srt) > limit:
            trim_val = srt[limit]
            new_latlongs = {}
            for key in latlongs.keys():
                if latlongs[key] > trim_val:
                    new_latlongs[key] = latlongs[key]
            latlongs = new_latlongs

        logging.info("Fetched latlongs over {0} to {1} total {2}".format(time_lower, time_upper, cnt))

        data = {
            "latlongs": latlongs
        }

        return data

if 'dynamodb' in os.environ:
    getters = {
        "world": DynamoDBDataGetter("world.txt", 'C'),
        "US": DynamoDBDataGetter("US.txt", 'S', prefix='US', is_region=True)
    }
    latLongGetter = DynamoDBLatLongGetter()
else:
    getters = {
        "world": DataGetter("world.txt"),
        "US": DataGetter("US.txt")
    }
    latLongGetter = None
def getHotspotExample():
    return exampleHotspotData


def getGetter(mapName):
    if not mapName in getters.keys():
        raise ValueError("Invalid map '%s'. Valid maps are: %s" % (mapName, ", ".join(getters.keys())))
    return getters[mapName]

@app.route("/get/<mapName>/<int:time>")
def serveGet(mapName, time):
    try:
        return Response(json.dumps(getGetter(mapName).getData(time)), mimetype="application/json")
    except ValueError, e:
        return "%s" % e, 400

@app.route("/all/<mapName>/<int:time1>/<int:time2>")
def getBetween(mapName, time1, time2):
    try:
        data = {}
        for i in xrange(time1, time2):
            data[i] = getGetter(mapName).getData(i)
        return Response(json.dumps(data), mimetype="application/json")
    except ValueError, e:
        return "%s" % e, 400

@app.route("/alllatlongs/<mapName>/<int:time1>/<int:time2>")
def getLatLongsBetween(mapName, time1, time2):
    if latLongGetter is None:
        data = {}
        for i in xrange(time1, time2):
            data[i] = json.loads(getHotspotExample())
        return Response(json.dumps(data), mimetype="application/json")
    try:
        data = {}
        for i in xrange(time1, time2):
            data[i] = latLongGetter.getData(i)
        return Response(json.dumps(data), mimetype="application/json")
    except ValueError, e:
        return "%s" % e, 400

@app.route("/latlong/<mapName>/<int:time>")
def getLatLongs(mapName, time):
    if latLongGetter is None:
        return Response(getHotspotExample(), mimetype="application/json")
    try:
        data = latLongGetter.getData(time)
        return Response(json.dumps(data), mimetype="application/json")
    except ValueError, e:
        return "%s" % e, 400

def getFlaskApp():
    return app

def begin():
    app.debug = True
    app.run(host="0.0.0.0")
if __name__ == "__main__":
    begin()