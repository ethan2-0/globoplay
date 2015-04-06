#!/usr/bin/python2
from flask import Flask, abort, Response
import json
import random

app = Flask(__name__)

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

def begin():
    app.run(debug=True)
if __name__ == "__main__":
    begin()