import requests
import json
import os

TELEGRAM_TOKEN = os.environ["8509941792:AAHmOTbW3BOfA2u6ms9vcECNNWuJx9N-isU"]
CHANNEL_ID = os.environ["-1004338659412"]

ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
STATE_FILE = "state.json"

POINT_THRESHOLDS = [30, 40, 50, 60, 70, 80]

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHANNEL_ID, "text": text})

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def get_games():
    response = requests.get(ESPN_URL)
    return response.json().get("events", [])

def process_games():
    state = load_state()
    games = get_games()

    for game in games:
        game_id = game["id"]
        competition = game["competitions"][0]
        status = competition["status"]["type"]["name"] # e.g. STATUS_FINAL, STATUS_IN_PROGRESS
        period = competition["status"]["period"]

        teams = competition["competitors"]
        home = next(t for t in teams if t["homeAway"] == "home")
        away = next(t for t in teams if t["homeAway"] == "away")

        home_name = home["team"]["displayName"]
        away_name = away["team"]["displayName"]
        home_score = int(home["score"])
        away_score = int(away["score"])

        prev = state.get(game_id, {})
        prev_status = prev.get("status")
        prev_period = prev.get("period")

        # --- End of period detection ---
        if status == "STATUS_IN_PROGRESS" and period != prev_period:
            if period == 2:
                send_message(f"🏀 END OF Q1\n{away_name} {away_score} - {home_score} {home_name}")
            elif period == 3:
                send_message(f"🏀 HALFTIME\n{away_name} {away_score} - {home_score} {home_name}")
            elif period == 4:
                send_message(f"🏀 END OF Q3\n{away_name} {away_score} - {home_score} {home_name}")
            elif period > 4:
                ot_number = period - 4
                send_message(f"🏀 END OF OT{ot_number}\n{away_name} {away_score} - {home_score} {home_name}")

        # --- Final detection ---
        if status == "STATUS_FINAL" and prev_status != "STATUS_FINAL":
            send_message(f"🔔 FINAL\n{away_name} {away_score} - {home_score} {home_name}")

            # Blowout check
            diff = abs(home_score - away_score)
            if diff >= 25:
                send_message(f"💥 BLOWOUT\n{away_name} {away_score} - {home_score} {home_name}")

            # Player stats leaders (points, rebounds, assists, triple-double)
            leaders = competition.get("leaders", [])
            player_stats = {}
            for leader_cat in leaders:
                cat_name = leader_cat["name"] # pointsLeader, reboundsLeader, assistsLeader
                for leader in leader_cat.get("leaders", []):
                    athlete = leader["athlete"]["displayName"]
                    value = int(leader["value"])
                    player_stats.setdefault(athlete, {})[cat_name] = value

            for athlete, stats in player_stats.items():
                pts = stats.get("pointsLeader", 0)
                reb = stats.get("reboundsLeader", 0)
                ast = stats.get("assistsLeader", 0)

                # Point threshold alert
                reached = [t for t in POINT_THRESHOLDS if pts >= t]
                if reached:
                    highest = max(reached)
                    send_message(f"🔥 {highest}+ PTS\n{athlete}: {pts} PTS")

                # Triple-double
                if pts >= 10 and reb >= 10 and ast >= 10:
                    send_message(f"💫 TRIPLE-DOUBLE\n{athlete}: {pts} PTS, {reb} REB, {ast} AST")

        # Save updated state
        state[game_id] = {"status": status, "period": period}

    save_state(state)

if __name__ == "__main__":
    process_games()
