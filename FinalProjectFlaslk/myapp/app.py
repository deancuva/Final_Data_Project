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
    travel_df = pd.read_csv('data/destinations_300 (1).csv')  # Adjust path as needed
except Exception as e:
    print(f"Error loading CSV: {e}")
    travel_df = pd.DataFrame()


import requests
import re


class TravelBot:
    def __init__(self, csv_data, api_key):
        self.csv_data = csv_data
        self.api_key = api_key

    def get_season_from_input(self, question):
        for season in ["winter", "spring", "summer", "fall", "autumn"]:
            if season in question:
                return "fall" if season == "autumn" else season
        return None

    def extract_temp_range(self, question):
        match = re.search(r'between (\d{2,3}) and (\d{2,3})', question)
        if match:
            return int(match.group(1)), int(match.group(2))
        match = re.search(r'(\d{2,3}) to (\d{2,3})', question)
        if match:
            return int(match.group(1)), int(match.group(2))
        match = re.search(r'around (\d{2,3})', question)
        if match:
            base = int(match.group(1))
            return base - 3, base + 3
        return None

    def geocode_city(self, city):
        url = f"https://api.geoapify.com/v1/geocode/search?text={city}&limit=1&apiKey={self.api_key}"
        response = requests.get(url)
        if response.status_code == 200:
            result = response.json()
            features = result.get("features", [])
            if features:
                coords = features[0]["geometry"]["coordinates"]
                return coords[1], coords[0]  # lat, lon
        return None, None

    def get_top_restaurants(self, lat, lon, radius=5000, limit=3):
        url = (
            f"https://api.geoapify.com/v2/places?"
            f"categories=catering.restaurant&"
            f"filter=circle:{lon},{lat},{radius}&"
            f"limit={limit}&"
            f"apiKey={self.api_key}"
        )
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get("features", [])
        return []

    def respond(self, question):
        question = question.lower()
        filtered = self.csv_data.copy()
        score = pd.Series(0, index=filtered.index)

        # Season-based temperature scoring
        season = self.get_season_from_input(question)
        temp_col = f"temperature_{season}" if season else None
        if temp_col and temp_col in filtered.columns:
            temp_range = self.extract_temp_range(question)
            if temp_range:
                low, high = temp_range
                midpoint = (low + high) / 2
                distance = (filtered[temp_col] - midpoint).abs()
                max_distance = distance.max() if distance.max() != 0 else 1
                score += (1 - (distance / max_distance)) * 10
            else:
                distance = (filtered[temp_col] - 70).abs()
                max_distance = distance.max() if distance.max() != 0 else 1
                score += (1 - (distance / max_distance)) * 8
        elif "warm" in question:
            score += (filtered['temperature'] - 65).clip(lower=0)
        elif "cold" in question:
            score += (65 - filtered['temperature']).clip(lower=0)

        # Setting preference scoring
        setting_preferences = {
            "urban": 10,
            "rural": 10,
            "beach": 12,
            "tropical": 12,
            "historical": 8
        }
        for setting, weight in setting_preferences.items():
            if setting in question:
                score += (filtered['setting'].str.lower() == setting) * weight

        if score.sum() == 0:
            return ("Tell me more about your preferences! For example:\n"
                    "- 'Tropical cities in winter with temps around 80'\n"
                    "- 'Beach destinations between 70 and 78 degrees in summer'")

        # Get top cities
        top_indices = score.nlargest(3).index
        top_cities = filtered.loc[top_indices, 'city']
        top_scores = score.loc[top_indices].astype(int)

        response = "🎯 Based on your preferences, consider:\n\n"
        for city, s in zip(top_cities, top_scores):
            response += f"🏙️ {city} (match score: {s})\n"
            lat, lon = self.geocode_city(city)
            if lat and lon:
                restaurants = self.get_top_restaurants(lat, lon)
                if restaurants:
                    for i, r in enumerate(restaurants):
                        name = r["properties"].get("name", "Unnamed")
                        addr = r["properties"].get("formatted", "No address listed")
                        cuisine = r["properties"].get("cuisine", "Cuisine unknown")
                        response += f"   🍽️ {i+1}. {name} — {cuisine}\n       📍 {addr}\n"
                else:
                    response += "   🍽️ No restaurant data available right now.\n"
            else:
                response += "   🌐 Could not find coordinates for this city.\n"
            response += "\n"

        return response.strip()

my_travel_bot = TravelBot(travel_df, api_key="bf3563606ea84aae982b322ba8d0f8c6")



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
