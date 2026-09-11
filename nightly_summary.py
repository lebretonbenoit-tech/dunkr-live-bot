import requests
import os
from datetime import datetime, timedelta

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
STANDINGS_URL = "https://site.api.espn.com/apis/v2/sports/basketball/nba/standings"

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHANNEL_ID, "text": text})

def get_yesterday_games():
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y%m%d")
    url = f"{ESPN_SCOREBOARD_URL}?dates={yesterday}"
    response = requests.get(url)
    return response.json().get("events", [])

def get_team_ranks():
    response = requests.get(STANDINGS_URL)
    data = response.json()
    ranks = {}
    try:
        for group in data["children"]:
            for entry in group["standings"]["entries"]:
                team_id = entry["team"]["id"]
                for stat in entry["stats"]:
                    if stat["name"] == "playoffSeed":
                        ranks[team_id] = int(stat["value"])
    except (KeyError, TypeError):
        pass
    return ranks

def main():
    games = get_yesterday_games()
    finished_games = [g for g in games if g["competitions"][0]["status"]["type"]["name"] == "STATUS_FINAL"]

    if not finished_games:
        return

    ranks = get_team_ranks()

    results_lines = ["📋 TONIGHT'S RESULTS"]
    best_pts, best_reb, best_ast = (None, 0), (None, 0), (None, 0)
    biggest_upset = None
    biggest_blowout = None

    for game in finished_games:
        competition = game["competitions"][0]
        teams = competition["competitors"]
        home = next(t for t in teams if t["homeAway"] == "home")
        away = next(t for t in teams if t["homeAway"] == "away")

        home_name = home["team"]["displayName"]
        away_name = away["team"]["displayName"]
        home_score = int(home["score"])
        away_score = int(away["score"])

        results_lines.append(f"{away_name} {away_score} - {home_score} {home_name}")

        diff = abs(home_score - away_score)
        winner_id = home["team"]["id"] if home_score > away_score else away["team"]["id"]
        loser_id = away["team"]["id"] if home_score > away_score else home["team"]["id"]
        winner_name = home_name if home_score > away_score else away_name
        loser_name = away_name if home_score > away_score else home_name

        winner_rank = ranks.get(winner_id)
        loser_rank = ranks.get(loser_id)
        if winner_rank and loser_rank and winner_rank > loser_rank:
            rank_gap = winner_rank - loser_rank
            if not biggest_upset or rank_gap > biggest_upset[0]:
                biggest_upset = (rank_gap, f"{winner_name} (seed {winner_rank}) upset {loser_name} (seed {loser_rank})")

        if not biggest_blowout or diff > biggest_blowout[0]:
            biggest_blowout = (diff, f"{winner_name} won by {diff} points")

        leaders = competition.get("leaders", [])
        for leader_cat in leaders:
            cat_name = leader_cat["name"]
            for leader in leader_cat.get("leaders", []):
                athlete = leader["athlete"]["displayName"]
                value = int(leader["value"])
                if cat_name == "pointsLeader" and value > best_pts[1]:
                    best_pts = (athlete, value)
                elif cat_name == "reboundsLeader" and value > best_reb[1]:
                    best_reb = (athlete, value)
                elif cat_name == "assistsLeader" and value > best_ast[1]:
                    best_ast = (athlete, value)

    message = "\n".join(results_lines)
    message += "\n\n🔥 TOP PERFORMANCES"
    if best_pts[0]:
        message += f"\nPoints: {best_pts[0]} — {best_pts[1]} PTS"
    if best_reb[0]:
        message += f"\nRebounds: {best_reb[0]} — {best_reb[1]} REB"
    if best_ast[0]:
        message += f"\nAssists: {best_ast[0]} — {best_ast[1]} AST"

    if biggest_upset:
        message += f"\n\n🎯 UPSET OF THE NIGHT\n{biggest_upset[1]}"
    elif biggest_blowout:
        message += f"\n\n💥 TEAM OF THE NIGHT\n{biggest_blowout[1]}"

    send_message(message)

if __name__ == "__main__":
    main()
