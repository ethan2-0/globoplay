import json
with open("maps/world.json") as f:
    global blah
    blah = "".join(f.readlines())
print json.loads(blah)