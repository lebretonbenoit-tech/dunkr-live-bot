import requests
import json
import os

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]

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

def check_streaks(state, team_name, team_id, won):
    streaks = state.setdefault("streaks", {})
    team_streak = streaks.get(team_id, {"count": 0, "type": None})

    streak_type = "W" if won else "L"

    if team_streak["type"] == streak_type:
        team_streak["count"] += 1
    else:
        if team_streak["count"] > 5:
            old_type = "win" if team_streak["type"] == "W" else "losing"
            send_message(f"⛔ STREAK SNAPPED\n{team_name}'s {team_streak['count']}-game {old_type} streak comes to an end.")
        team_streak = {"count": 1, "type": streak_type}

    streaks[team_id] = team_streak

    if team_streak["count"] >= 5:
        if streak_type == "W":
            send_message(f"📈 WIN STREAK\n{team_name} have won {team_streak['count']} straight games!")
        else:
            send_message(f"📉 LOSING STREAK\n{team_name} have lost {team_streak['count']} straight games.")

def process_games():
    state = load_state()
    games = get_games()

    for game in games:
        game_id = game["id"]
        season_type = game.get("season", {}).get("type") # 1 = preseason, 2 = regular season, 3 = playoffs
        competition = game["competitions"][0]
        status = competition["status"]["type"]["name"]
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

            # Streak tracking (regular season only)
            if season_type == 2:
                home_won = home_score > away_score
                check_streaks(state, home_name, home["team"]["id"], home_won)
                check_streaks(state, away_name, away["team"]["id"], not home_won)

            # Player stats leaders (points, rebounds, assists, triple-double)
            leaders = competition.get("leaders", [])
            player_stats = {}
            for leader_cat in leaders:
                cat_name = leader_cat["name"]
                for leader in leader_cat.get("leaders", []):
                    athlete = leader["athlete"]["displayName"]
                    value = int(leader["value"])
                    player_stats.setdefault(athlete, {})[cat_name] = value

            for athlete, stats in player_stats.items():
                pts = stats.get("pointsLeader", 0)
                reb = stats.get("reboundsLeader", 0)
                ast = stats.get("assistsLeader", 0)

                reached = [t for t in POINT_THRESHOLDS if pts >= t]
                if reached:
                    highest = max(reached)
                    send_message(f"🔥 {highest}+ PTS\n{athlete}: {pts} PTS")

                if pts >= 10 and reb >= 10 and ast >= 10:
                    send_message(f"💫 TRIPLE-DOUBLE\n{athlete}: {pts} PTS, {reb} REB, {ast} AST")

        state[game_id] = {"status": status, "period": period}

    save_state(state)

if __name__ == "__main__":
    process_games()
