population_scale = 1000000000
$("#map-select").on("change", function() {
    location.href = "index.html?map=" + $("#map-select")[0].selectedIndex;
});
function isNaN(num) {
    return !(num < 0 || num > 0 || num == 0);
}
var urlparams = (function() {
    var url = location.href;
    url = url.split("?")[1];
    if(typeof url == "undefined") {
        return {};
    }
    var parts = url.split("&");
    var ret = {};
    parts.forEach(function(elm) {
        var parts2 = elm.split("=");
        ret[parts2[0]] = parts2[1];
    });
    return ret;
})();
var mapname = "world";
maps = {
    world: world,
    US: US
};
if(typeof urlparams["map"] != "undefined") {
    var num = parseInt(urlparams["map"]);
    $(function() {
        document.getElementById("map-select").selectedIndex = num;
    });
    var index = 0;
    for(key in maps) {
        if(index++ == num) {
            mapname = key;
            break;
        }
    }
}
for(map in maps) {
    $("#map-select").append($("<option>")
        .html(map));
}
function loadMap(map) {
    data = maps[map];
}
//Thanks Pablo on StackOverflow; question @ http://stackoverflow.com/questions/5560248/programmatically-lighten-or-darken-a-hex-color-or-rgb-and-blend-colors
function shadeColor(color, percent) {
    var R = parseInt(color.substring(1,3),16);
    var G = parseInt(color.substring(3,5),16);
    var B = parseInt(color.substring(5,7),16);
    R = parseInt(R * (100 + percent) / 100);
    G = parseInt(G * (100 + percent) / 100);
    B = parseInt(B * (100 + percent) / 100);
    R = (R<255)?R:255;
    G = (G<255)?G:255;
    B = (B<255)?B:255;
    var RR = ((R.toString(16).length==1)?"0"+R.toString(16):R.toString(16));
    var GG = ((G.toString(16).length==1)?"0"+G.toString(16):G.toString(16));
    var BB = ((B.toString(16).length==1)?"0"+B.toString(16):B.toString(16));
    return "#"+RR+GG+BB;
}
var map = $("#map");
var lastMouseMove = null;
function updateTimeDisplay() {
    $("#display-time").html(prettyPrintMinutestamp(time));
}
var mapData = null;
var divByPop = true;
function displayTime(time) {
    //Update time display
    updateTimeDisplay();
    //Get the data
    fetch("/get/" + mapname + "/" + time).then(function(response) {
        return response.text();
    }).then(function(body) {
        try {
            body = JSON.parse(body);
            mapData = body;
            data = body["countries"];
            if(divByPop) {
                for(var index in data) {
                    if(maps[mapname]["pop"][index] == 0) {
                        alert("whoops");
                    }
                    if(typeof maps[mapname]["pop"][index] == "undefined") {
                        maps[mapname]["pop"][index] = 1;
                    }
                    data[index] *= population_scale
                    data[index] /= maps[mapname]["pop"][index];
                }
            }
            setTimeout(function() {
                for(var city in body["cities"]) {
                    updateCity(city, {
                        size: body["cities"][city]
                    });
                }
            }, 102);
            reload();
        } catch(e) {
            console.log(e);
            console.log(body);
        }
    });
    fetch("/latlong/" + mapname + "/" + time).then(function(response) {
        return response.text();
    }).then(function(body) {
        removePulsyThingies();
        body = JSON.parse(body)["latlongs"];
        var pulsyThingies = [];
        for(var key in body) {
            var parts = key.split(",");
            var lat = parseInt(parts[0]) / 1000 - 180;
            var lng = parseInt(parts[1]) / 1000 - 180;
            pulsyThingies.push({
                lat: lat,
                lng: lng,
                amt: body[key] < 1 ? 0 : Math.log(body[key])
            });
            // addPulsyThingy(lat, lng, 5);
        }
        console.log(pulsyThingies);
        var largest = {amt: -1};
        pulsyThingies.forEach(function(elm) {
            largest = largest.amt > elm.amt ? largest : elm;
        });
        pulsyThingies.forEach(function(elm) {
            var percentage = elm.amt / largest.amt;
            percentage *= 5;
            percentage = Math.round(percentage);
            if(percentage >= 2) {
                console.log("Position (" + elm.lat + "," + elm.lng + ")")
                addPulsyThingy(elm.lat, elm.lng, percentage);
            }
        });
    });
}
var heldClickables = {};
$(".clickable").on("mousedown", function(evt) {
    heldClickables[$(this).attr("data-name")] = true;
}).each(function() {
    heldClickables[$(this).attr("data-name")] = false;
}).on("mouseup", function(evt) {
    heldClickables[$(this).attr("data-name")] = false;
}).on("click", function() {
    updateClickables(true);
});
//back forward faster slower
var clickableUpdates = 0;
function updateClickables(forceUpdate) {
    if(typeof(forceUpdate) == "undefined") {
        forceUpdate = false;
    }
    clickableUpdates++;
    if(heldClickables["faster"] == true) {
        speed += 3;
        updateSpeedInterval();
    } else if(heldClickables["slower"] == true) {
        speed -= 3;
        updateSpeedInterval();
    }
    if(clickableUpdates % 3 == 0 || forceUpdate) {
        var originalTime = time;
        if(heldClickables["back"] == true) {
            time--;
            updateTimeDisplay();
        } else if(heldClickables["forward"] == true) {
            time++;
            updateTimeDisplay();
        }
        if(time < 0) {
            time = 0;
        }
        if(time != originalTime) {
            displayTime(time);
        }
    }
}
function getMapmode() {
    return $("#city-mapmode")[0].checked ? "city" : "political";
}
function minutestampToDate(time) {
    return new Date(time * 60 * 1000);
}
function dateToMinutestamp(date) {
    return Math.floor(+(date) / 1000 / 60)
}
function prettyPrintDate(date) {
    return date.toLocaleString();
}
function prettyPrintMinutestamp(time) {
    return prettyPrintDate(minutestampToDate(time));
}
function latLngToPt(lat, lng) {
    return mapObj.latLngToPoint(lat, lng);
}
var cities = {};
function updateCity(name, params) {
    if(typeof cities[name] == "undefined") {
        cities[name] = {};
    }
    var city = cities[name];
    for(var key in params) {
        city[key] = params[key];
    }
    if(typeof city["elm"] == "undefined") {
        city["elm"] = $("<div>").addClass("city").appendTo($(document.body));
    }
    if(city["mouseoverHandled"] != true) {
        city["mouseoverHandled"] = true;
        city["elm"].on("mouseenter", function(evt) {
            $(".jvectormap-tip").show().html(city["name"]).css("left", evt.pageX + 10).css("top", evt.pageY + 10);
        }).on("mouseleave", function(evt) {
            $(".jvectormap-tip").hide();
        });
    }
    var pos = latLngToPt(city["lat"], city["lng"]);
    var scaleFactor = 2 / 5;
    city["elm"].css("left", pos.x - city["size"] * scaleFactor * 0.5).css("top", pos.y - city["size"] * scaleFactor * 0.5)
        .css("width", city["size"] * scaleFactor).css("height", city["size"] * scaleFactor);
    if(getMapmode() == "political") {
        city["elm"].hide();
    } else {
        city["elm"].show();
    }
}
function updateCities() {
    for(var city in cities) {
        updateCity(city, {});
    }
}
$(window).on("resize", function() {
    updateCities();
    updatePulsyThingies();
});
$(function() {
    setTimeout(function() {
        var obj = maps[mapname]["cities"];
        for(var key in obj) {
            updateCity(key, obj[key]);
        }
    }, 100);
});
function updateMapmode() {
    updateCities();
    reload();
}
$(".mapmode-selector").on("change", function() {
    updateMapmode();
});
setInterval(updateClickables, 100);
var time = Math.floor(dateToMinutestamp(new Date())) - 1;
var mapObj = null;
norms = ["polynomial", "linear", "log"];
var normFunc = 0;
function reload() {
    $(".jvectormap-tip").remove();
    var newMap = $("<div>").appendTo($(document.body)).css("height", "100vh");
    var blah = new jvm.Map({
        container: newMap,
        map: mapname + "_mill_en",
        backgroundColor: shadeColor("#87ceeb", 0),
        regionStyle: {
            initial: {
                fill: getMapmode() == "political" ? "rgb(80, 80, 80)" : "#F7F7F7"
            }
        },
        series: {
            regions: [{
                values: getMapmode() == "political" ? data : maps[map],
                scale: ['#F7F7F7', '#505050'],
                normalizeFunction: norms[normFunc]
            }]
        },
        zoomMax: 1,
        onRegionTipShow: function(e, tip, code) {
            value = data[code]
            if (divByPop) {
                value *= maps[mapname]["pop"][code]
                value /= population_scale
                value = Math.round(value)
            }
            $("#traffic").html(value);
            $("#info-title").html(tip.html());
            $("#population").html(maps[mapname]["pop"][code]);
            $("#info").show();
        },
        onRegionOut: function() {
            $("#info").hide();
        }
    });
    mapObj = blah;
    map.remove();
    newMap.show();
    map = newMap;
};
function loadNext() {
    time++;
    displayTime(time);
}
$(loadNext);
var speed = 60;
var updateInterval = -1;//updateSpeedInterval
function updateSpeedInterval() {
    if(updateInterval != -1) {
        clearInterval(updateInterval);
    }
    var timeToUpdate = 3600000 / speed;
    console.log("Update in " + timeToUpdate + "ms");
    updateInterval = setInterval(loadNext, timeToUpdate);
    $("#speed").html(speed);
}
updateSpeedInterval();
function updateNorm() {
    normFunc = $("#normSelect")[0].selectedIndex;
    reload();
}
$(function() {
    setTimeout(function() {
        $("#info").hide();
    }, 1000);
});
function updateDivByPop() {
    divByPop = $("#divByPopCheckbox")[0].checked;
    reloadCurrentTime();
}
function reloadCurrentTime() {
    displayTime(time);
}





function addPulsyThingy(lat, lng, tier) {
    var pt = latLngToPt(lat, lng);
    var elm = $("<div>").addClass("latlng latlng-t" + tier)
        .css("left", pt.x)
        .css("top", pt.y)
        .appendTo($("#lat-lng-layer"))
        .attr("data-lat", lat)
        .attr("data-lng", lng);
}
function updatePulsyThingies() {
    $(".latlng").each(function() {
        var lat = parseFloat($(this).attr("data-lat"));
        var lng = parseFloat($(this).attr("data-lng"));
        var pt = latLngToPt(lat, lng);
        $(this).css("left", pt.x).css("top", pt.y);
    });
}
function removePulsyThingies() {
    $(".latlng").remove();
}
$("#type-selector").hide();
