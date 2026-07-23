from flask import Flask , render_template , request
import requests
import os
from datetime import datetime
import geonamescache

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def home():
    """render the search page; on POST, look up weather by coordinates
    (if a suggestion was picked) or by the typed city name as fallback"""
    weather_data = None
    error = None

    if request.method == 'POST':
        lat = request.form.get('lat', '').strip()
        lon = request.form.get('lon', '').strip()
        city = request.form.get('city', '').strip()

        if lat and lon:  # user picked a suggestion -> exact coordinates
            weather_location = f"{lat},{lon}"
        elif city:
            weather_location = city
        else:
            weather_location = None
            error = "Please enter a city or country."

        if weather_location:
            weather_data = get_weather(weather_location)
            if weather_data is None:
                error = "Couldn't find weather for that location. Try again."
            elif lat and lon and city:  # picked from dropdown -> show the picked label
                weather_data["display_name"] = city
            else:  # free-typed -> show what the API resolved
                weather_data["display_name"] = f'{weather_data["city"]}, {weather_data["country"]}'

    return render_template('home.html', weather=weather_data, error=error)

@app.route('/api/suggest')
def suggest():
    """return up to 10 city suggestions matching the typed prefix, biggest cities first"""
    q = request.args.get('q', '').strip().lower()
    if len(q) < 2:
        return {"results": []}
    results = []
    for c in CITIES:
        if c["name_lower"].startswith(q):
            results.append({
                "label": f'{c["name"]}, {c["country"]}' if c["country"] else c["name"],
                "lat": c["lat"],
                "lon": c["lon"]
            })
            if len(results) == 10:
                break
    return {"results": results}

@app.errorhandler(404)
def handle_not_found(e):
    return render_template("not_found.html"), 404

def get_weather(weather_location):
    """get the user input send an API request return the weather forcast of this location in json and filter the json for relevant data"""
    api_key = os.getenv("API_WEATHER")

    try: # URL for API
        response = requests.get(
            "https://api.weatherapi.com/v1/forecast.json",
            params={
                "key": api_key,
                "q": weather_location,
                "days": 7
            },
            timeout=10
        )
    except requests.exceptions.RequestException:
        return None

    try:
        data = response.json() # API response saved in json
    except ValueError:
        return None

    if not response.ok or "error" in data:
        return None

    #The dict after filtering the json to what i need
    filtered = {
        "city": data["location"]["name"],
        "country": data["location"]["country"],
        "days": get_days_table(data)
    }

    return filtered

def get_day_month(data):
    """get the date and return the actuall day + month , day of the month """
    date = datetime.strptime(data, "%Y-%m-%d")
    return date.strftime("%A %m-%d")

def get_days_table(data):
    """get the json data from API call and make a dict of days with each day have date , temperature and humidity """
    days = {}
    for day in data["forecast"]["forecastday"]:
        date = get_day_month(day["date"])
        hours = day.get("hour", [])
        days[date] = {
            "average_temperature": day["day"]["avgtemp_c"],
            "average_humidity": day["day"]["avghumidity"],
            "day_temperature": hours[12]["temp_c"] if len(hours) > 12 else day["day"]["avgtemp_c"],
            "night_temperature": hours[0]["temp_c"] if hours else day["day"]["avgtemp_c"]
        }
    return days

def load_cities():
    """load ~32k world cities + ~250 countries into one list sorted by population,
    with precomputed lowercase names for fast prefix search"""
    gc = geonamescache.GeonamesCache()
    countries = gc.get_countries()
    cities_raw = gc.get_cities().values()

    # index capitals: countrycode -> (lat, lon), to give countries coordinates
    capitals = {}
    for c in cities_raw:
        if c["name"] == countries.get(c["countrycode"], {}).get("capital"):
            capitals[c["countrycode"]] = (c["latitude"], c["longitude"])

    entries = []
    for c in cities_raw:
        entries.append({
            "name": c["name"],
            "name_lower": c["name"].lower(),
            "country": countries.get(c["countrycode"], {}).get("name", c["countrycode"]),
            "lat": c["latitude"],
            "lon": c["longitude"],
            "population": c["population"]
        })

    for code, country in countries.items():
        if code in capitals:
            lat, lon = capitals[code]
            entries.append({
                "name": country["name"],
                "name_lower": country["name"].lower(),
                "country": "",                    # it IS the country
                "lat": lat,
                "lon": lon,
                "population": country["population"]
            })

    entries.sort(key=lambda c: c["population"], reverse=True)
    return entries

CITIES = load_cities()

if __name__ == '__main__':
    app.run()