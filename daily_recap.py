import requests
import os
from datetime import datetime
import pytz

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHANNEL_ID, "text": text})

def get_games():
    response = requests.get(ESPN_URL)
    return response.json().get("events", [])

def main():
    games = get_games()
    if not games:
        return

    today_utc = datetime.utcnow().date()
    et = pytz.timezone("US/Eastern")
    lines = ["🗓️ TODAY'S GAMES"]
    found_today = False

    for game in games:
        date_str = game["date"]
        game_time = datetime.strptime(date_str, "%Y-%m-%dT%H:%MZ")

        if game_time.date() != today_utc:
            continue

        found_today = True
        competition = game["competitions"][0]
        teams = competition["competitors"]
        home = next(t for t in teams if t["homeAway"] == "home")
        away = next(t for t in teams if t["homeAway"] == "away")

        game_time_et = pytz.utc.localize(game_time).astimezone(et)
        time_str = game_time_et.strftime("%-I:%M %p ET")

        lines.append(f"{time_str} — {away['team']['displayName']} @ {home['team']['displayName']}")

    if found_today:
        send_message("\n".join(lines))

if __name__ == "__main__":
    main()
