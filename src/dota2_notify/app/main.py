import json
from dota2_notify.models.match import DotaMatch

def main():
    payload = """{"match_id": 8642866804,
        "player_slot": 3,
        "radiant_win": true,
        "duration": 2285,
        "game_mode": 2,
        "lobby_type": 1,
        "hero_id": 100,
        "start_time": 1768015812,
        "version": 22,
        "kills": 4,
        "deaths": 5,
        "assists": 21,
        "average_rank": 75,
        "leaver_status": 0,
        "party_size": 10,
        "hero_variant": 1
 }"""
    match = DotaMatch.from_json(payload)
    # print(match)
    print(match.match_duration)


if __name__ == "__main__":
    main()
