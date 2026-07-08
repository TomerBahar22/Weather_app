from flask import Flask , render_template , request
import requests
import os
from datetime import datetime

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def home():
    """return a page with a search bar check if the search bar input is valid and return in response"""
    weather_data = None # the object of filtered data
    error = None # the object of error

    if request.method == 'POST': # check if http request is POST
        if request.form.get('city', '').strip().isascii() and request.form.get('country', '').strip().isascii():
            city = request.form.get('city', '').strip()
            country = request.form.get('country', '').strip()
            if city and country: #if both city and country were given location is city and country
                weather_location = f"{city}{country}"
            elif city and not country: # if only city was given location is city
                weather_location = city
            elif country and not city: # if only country was given location is country
                weather_location = country
            else: # if Unvalid input was given return None
                weather_location = None
        else:
            weather_location = None
            error = "Couldn't read the language please write in english "

        if weather_location: #if the weather location is valid make an API call to get the data
            weather_data = get_weather(weather_location)
            if weather_data is None: # if the input was unvalid return error message
                error = "Couldn't find weather for that location. Try again."

    return render_template('home.html', weather=weather_data, error=error)


@app.errorhandler(404)
def handle_not_found(e):
    return render_template("not_found.html"), 404

def get_weather(weather_location):
    """get the user input send an API request return the weather forcast of this location in json and filter the json for relevant data"""

    api_key = os.environ.get("WEATHER_API_KEY")

    if weather_location.strip().lower() in ("usa", "us", "united states"): # specific case
        weather_location = "United States of America"
    if weather_location.strip().lower() == "israel":# specific case
        weather_location ="jerusalem israel"

    try: # URL for API
        response = requests.get(
            "https://api.weatherapi.com/v1/forecast.json",
            params={
                "key": api_key,
                "q": weather_location,
                "days": 7
            }
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
        days[date] = {
            "average_temperature": day["day"]["avgtemp_c"],
            "average_humidity": day["day"]["avghumidity"],
            "day_temperature": day["hour"][12]["temp_c"],
            "night_temperature": day["hour"][0]["temp_c"]
        }
    return days

if __name__ == '__main__':
    app.run()