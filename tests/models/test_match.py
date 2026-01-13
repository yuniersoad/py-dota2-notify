import pytest
from datetime import datetime, timezone, timedelta
from dota2_notify.models.match import DotaMatch

def test_parse_match_from_json():
    """Test parsing a match from JSON string and inspecting its properties"""
    json_payload = """{
        "match_id": 8642866804,
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
    
    match = DotaMatch.from_json(json_payload)
    
    # Basic properties
    assert match.match_id == 8642866804
    assert match.player_slot == 3
    assert match.radiant_win is True
    assert match.duration == 2285
    assert match.game_mode == 2
    assert match.lobby_type == 1
    assert match.hero_id == 100
    assert match.start_time == 1768015812
    assert match.kills == 4
    assert match.deaths == 5
    assert match.assists == 21
    
    # Computed properties
    assert match.is_radiant is True
    assert match.player_won is True
    assert match.hero_name == "Tusk"
    assert match.match_duration == timedelta(seconds=2285)
    assert match.start_time_utc == datetime.fromtimestamp(1768015812, tz=timezone.utc)


def test_parse_match_from_dict():
    """Test parsing a match from dictionary"""
    data = {
        "match_id": 8642866804,
        "player_slot": 130,
        "radiant_win": False,
        "duration": 1800,
        "hero_id": 14,
        "start_time": 1768015812,
        "kills": 10,
        "deaths": 3,
        "assists": 15
    }
    
    match = DotaMatch.from_dict(data)
    
    assert match.match_id == 8642866804
    assert match.player_slot == 130
    assert match.is_radiant is False
    assert match.player_won is True
    assert match.hero_name == "Pudge"


def test_match_serialization():
    """Test converting match to dictionary"""
    match = DotaMatch(
        match_id=123456,
        player_slot=5,
        radiant_win=True,
        duration=3000,
        hero_id=22,
        kills=8,
        deaths=2,
        assists=12
    )
    
    data = match.to_dict()
    
    assert data['match_id'] == 123456
    assert data['player_slot'] == 5
    assert data['radiant_win'] is True
    assert data['duration'] == 3000
    assert data['hero_id'] == 22
    assert data['kills'] == 8
    assert data['deaths'] == 2
    assert data['assists'] == 12


def test_unknown_hero():
    """Test handling of unknown hero ID"""
    match = DotaMatch(hero_id=9999)
    assert match.hero_name == "Unknown Hero (9999)"
    assert DotaMatch.get_hero_name(9999) == "Unknown Hero (9999)"


def test_match_string_representation():
    """Test string representation of match"""
    match = DotaMatch(
        match_id=123456,
        player_slot=3,
        radiant_win=True,
        hero_id=100,
        start_time=1768015812,
        kills=4,
        deaths=5,
        assists=21
    )
    
    str_repr = str(match)
    assert "Match 123456" in str_repr
    assert "Won" in str_repr
    assert "Tusk" in str_repr
    assert "4/5/21" in str_repr