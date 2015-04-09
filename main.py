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

if 'dynamodb' in os.environ:
    ddb_conn = dynamodb2.connect_to_region(os.environ['aws_region'])
    count_table = Table(table_name=os.environ['count_table'],
                      connection=ddb_conn)

class DataGetter:
    countries = "This will be populated in the 'with' statement in __init__."
    cities = "Same thing for cities."
    def __init__(self, mapfile):
        with open("maps/%s" % mapfile) as f:
            self.countries = [x.replace("\n", "").replace("\r", "") for x in f.readlines()]
        with open("cities/%s" % mapfile) as f:
            self.cities = [x.replace("\n", "").replace("\r", "") for x in f.readlines()]
    def getData(self, time):
        data = {
            "countries": {},
            "cities": {}
        }
        for country in self.countries:
            data["countries"][country] = random.randrange(1000)
        for city in self.cities:
            data["cities"][city] = random.randrange(100)
        return data

class DynamoDBDataGetter:
    countries = "This will be populated in the 'with' statement in __init__."
    cities = "Same thing for cities."
    def __init__(self, mapfile, entity, prefix=None):
        self.entity = entity
        self.prefix = prefix
        with open("maps/pop%s" % mapfile) as f:
            self.countries_by_pop = {}
            for kvp in [x.split(' ') for x in f.read().splitlines()]:
                logging.info("kvp: {0} - {1}".format(kvp[0], kvp[1]))
                self.countries_by_pop[kvp[0]] = float(kvp[1])
        with open("maps/%s" % mapfile) as f:
            self.countries = {}
            for x in f.read().splitlines():
                self.countries[x] = 1.0
        with open("cities/%s" % mapfile) as f:
            self.cities = [x.replace("\n", "").replace("\r", "") for x in f.readlines()]

    def getData(self, time):
        logging.info("get {1} data for time {0}".format(time, self.entity))
        data = {
            "countries": {},
            "cities": {}
        }
        for country in self.countries:
            data["countries"][country] = 0

        time_lower = time * 60000
        time_upper = (time + 1) * 60000
        logging.info("Fetching data over {0} to {1}".format(time_lower, time_upper))
        iterator = count_table.query_2(
            entity__eq=self.entity,
            ts__gte=time_lower,
            ts__lt=time_upper
        )

        cnt = 0
        for item in iterator:
            cnt += 1
            for key in item.keys():
                if key == 'ts' or key == 'entity':
                    continue
                name = self.prefix + '-' + key if not self.prefix is None else key
                if not name in self.countries:
                    continue
                if name in data["countries"]:
                    data["countries"][name] += 100000.0 * float(item[key])
                else:
                    data["countries"][name] = 100000.0 * float(item[key])

        logging.info("Fetched data over {0} to {1} total {2}".format(time_lower, time_upper, cnt))

        maxval = 1000000
        for country in data["countries"].keys():
            if country == 'US':
                maxval = data["countries"][country] / self.countries_by_pop[country]

        logging.info("Max val {0}".format(maxval))
        for country in data["countries"].keys():
            if country in self.countries_by_pop:
                data["countries"][country] = data["countries"][country] / self.countries_by_pop[country]
                if data["countries"][country] > maxval:
                    data["countries"][country] = maxval
            else:
                data["countries"][country] = 0

        logging.info("Returning")

        return data

if 'dynamodb' in os.environ:
    getters = {
        "world": DynamoDBDataGetter("world.txt", 'C'),
        "US": DynamoDBDataGetter("US.txt", 'S', prefix='US')
    }
else:
    getters = {
        "world": DataGetter("world.txt"),
        "US": DataGetter("US.txt")
    }

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

def getFlaskApp():
    return app

def begin():
    app.debug = True
    app.run(host="0.0.0.0")
if __name__ == "__main__":
    begin()