from flask import Flask, render_template, request, jsonify
import pandas as pd
import requests

app = Flask(__name__)


# Route to home page
@app.route('/')
def home():
    return render_template('home.html')

# Load local data
try:
    travel_df = pd.read_csv('data/destinations.csv')  # Adjust path as needed
except Exception as e:
    print(f"Error loading CSV: {e}")
    travel_df = pd.DataFrame()

# Load API data
def fetch_api_data():
    url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchByCity"

    querystring = {
        "city_id": "Rome",  # adjust as needed
        "search_type": "city",
        "arrival_date": "2025-07-01",
        "departure_date": "2025-07-05",
        "room_qty": "1",
        "adults": "2",
        "children_age": "0"
    }

    headers = {
        "X-RapidAPI-Key": "02840474edmsh3baa31099fd145bp1e59bfjsn312bb0751f66",
        "X-RapidAPI-Host": "booking-com15.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"API fetch failed: {response.status_code}")
            return {}
    except Exception as e:
        print(f"Error fetching API data: {e}")
        return {}


api_data = fetch_api_data()

class TravelBot:
    def __init__(self, csv_data, api_data):
        self.csv_data = csv_data
        self.api_data = api_data

    def respond(self, question):
        question = question.lower()

        if "warm" in question:
            results = self.csv_data[self.csv_data['temperature'] > 75]
            return f"Try visiting: {', '.join(results['city'].head(3))}"

        elif "cheap flight" in question:
            results = self.csv_data.sort_values(by='flight_cost').head(3)
            return f"Cheap destinations: {', '.join(results['city'])}"

        elif "urban" in question:
            results = self.csv_data[self.csv_data['setting'] == 'urban']
            return f"Urban destinations: {', '.join(results['city'].head(3))}"

        elif "hotel" in question or "stay" in question:
            hotels = self.api_data.get("data", {}).get("hotels", [])
            if hotels:
                names = [hotel["property_name"] for hotel in hotels[:3]]
                return f"Here are some hotels: {', '.join(names)}"
            else:
                return "Sorry, I couldn't find hotel data right now."

        return "Tell me more about your preferences!"


my_travel_bot = TravelBot(travel_df, api_data)



@app.route('/about')
def about():
    return 'Welcome to our Travel Chatbot, Botty! Botty is excited to help you plan your next vacation and bring the spark back to travel!'

@app.route('/debug')
def debug():
    return 'This is the debug route. Botty hopes everything is fine'

@app.route("/ask", methods=["POST"])
def ask_bot():
    user_input = request.json.get("question")
    response = my_travel_bot.respond(user_input)
    return jsonify({"answer": response})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
