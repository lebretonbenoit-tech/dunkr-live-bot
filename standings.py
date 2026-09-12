import requests
import os
import json

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
STANDINGS_URL = "https://site.api.espn.com/apis/v2/sports/basketball/nba/standings"
PLAYOFF_STATE_FILE = "playoff_state.json"

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHANNEL_ID, "text": text})

def load_playoff_state():
    if os.path.exists(PLAYOFF_STATE_FILE):
        with open(PLAYOFF_STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_playoff_state(state):
    with open(PLAYOFF_STATE_FILE, "w") as f:
        json.dump(state, f)

def get_standings():
    response = requests.get(STANDINGS_URL)
    return response.json()

def format_conference(entries, conf_name):
    lines = [f"{conf_name}"]
    sorted_entries = sorted(entries, key=lambda e: next(
        (s["value"] for s in e["stats"] if s["name"] == "playoffSeed"), 99))
    for entry in sorted_entries:
        team = entry["team"]["displayName"]
        wins = next((s["value"] for s in entry["stats"] if s["name"] == "wins"), "?")
        losses = next((s["value"] for s in entry["stats"] if s["name"] == "losses"), "?")
        seed = next((s["value"] for s in entry["stats"] if s["name"] == "playoffSeed"), "?")
        lines.append(f"{int(seed)}. {team} ({int(wins)}-{int(losses)})")
    return "\n".join(lines)

def check_playoff_status(entries, playoff_state):
    for entry in entries:
        team_id = entry["team"]["id"]
        team_name = entry["team"]["displayName"]
        note = entry.get("note", {}).get("description", "") if entry.get("note") else ""
        seed = next((s["value"] for s in entry["stats"] if s["name"] == "playoffSeed"), None)

        prev = playoff_state.get(team_id, {})

        clinched = "clinch" in note.lower()
        eliminated = "eliminat" in note.lower()
        top6 = seed is not None and seed <= 6

        if clinched and not prev.get("clinched"):
            send_message(f"🎟️ CLINCHED PLAYOFFS\n{team_name} have officially secured a playoff spot!")
        if eliminated and not prev.get("eliminated"):
            send_message(f"❌ ELIMINATED\n{team_name} have been mathematically eliminated from playoff contention.")
        if top6 and not prev.get("top6"):
            send_message(f"🔓 LOCKED IN TOP 6\n{team_name} have secured a top-6 seed — no play-in for them this year.")

        playoff_state[team_id] = {"clinched": clinched, "eliminated": eliminated, "top6": top6}

    return playoff_state

def main(conference):
    data = get_standings()
    playoff_state = load_playoff_state()

    for group in data["children"]:
        conf_name = group["name"]
        entries = group["standings"]["entries"]

        playoff_state = check_playoff_status(entries, playoff_state)

        if conference.lower() in conf_name.lower():
            message = format_conference(entries, f"📊 {conf_name.upper()} STANDINGS")
            send_message(message)

    save_playoff_state(playoff_state)

if __name__ == "__main__":
    import sys
    conference = sys.argv[1] if len(sys.argv) > 1 else "eastern"
    main(conference)
