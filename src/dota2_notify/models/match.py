from datetime import datetime, timezone, timedelta
import json

class DotaMatch:
    """
    Dota 2 match data class with hero information mapping
    """
    
    # Hero information - maps hero IDs to localized names
    HERO_NAMES = {
        1: "Anti-Mage", 2: "Axe", 3: "Bane", 4: "Bloodseeker",
        5: "Crystal Maiden", 6: "Drow Ranger", 7: "Earthshaker",
        8: "Juggernaut", 9: "Mirana", 10: "Morphling",
        11: "Shadow Fiend", 12: "Phantom Lancer", 13: "Puck",
        14: "Pudge", 15: "Razor", 16: "Sand King",
        17: "Storm Spirit", 18: "Sven", 19: "Tiny",
        20: "Vengeful Spirit", 21: "Windranger", 22: "Zeus",
        23: "Kunkka", 25: "Lina", 26: "Lion",
        27: "Shadow Shaman", 28: "Slardar", 29: "Tidehunter",
        30: "Witch Doctor", 31: "Lich", 32: "Riki",
        33: "Enigma", 34: "Tinker", 35: "Sniper",
        36: "Necrophos", 37: "Warlock", 38: "Beastmaster",
        39: "Queen of Pain", 40: "Venomancer", 41: "Faceless Void",
        42: "Wraith King", 43: "Death Prophet", 44: "Phantom Assassin",
        45: "Pugna", 46: "Templar Assassin", 47: "Viper",
        48: "Luna", 49: "Dragon Knight", 50: "Dazzle",
        51: "Clockwerk", 52: "Leshrac", 53: "Nature's Prophet",
        54: "Lifestealer", 55: "Dark Seer", 56: "Clinkz",
        57: "Omniknight", 58: "Enchantress", 59: "Huskar",
        60: "Night Stalker", 61: "Broodmother", 62: "Bounty Hunter",
        63: "Weaver", 64: "Jakiro", 65: "Batrider",
        66: "Chen", 67: "Spectre", 68: "Ancient Apparition",
        69: "Doom", 70: "Ursa", 71: "Spirit Breaker",
        72: "Gyrocopter", 73: "Alchemist", 74: "Invoker",
        75: "Silencer", 76: "Outworld Destroyer", 77: "Lycan",
        78: "Brewmaster", 79: "Shadow Demon", 80: "Lone Druid",
        81: "Chaos Knight", 82: "Meepo", 83: "Treant Protector",
        84: "Ogre Magi", 85: "Undying", 86: "Rubick",
        87: "Disruptor", 88: "Nyx Assassin", 89: "Naga Siren",
        90: "Keeper of the Light", 91: "Io", 92: "Visage",
        93: "Slark", 94: "Medusa", 95: "Troll Warlord",
        96: "Centaur Warrunner", 97: "Magnus", 98: "Timbersaw",
        99: "Bristleback", 100: "Tusk", 101: "Skywrath Mage",
        102: "Abaddon", 103: "Elder Titan", 104: "Legion Commander",
        105: "Techies", 106: "Ember Spirit", 107: "Earth Spirit",
        108: "Underlord", 109: "Terrorblade", 110: "Phoenix",
        111: "Oracle", 112: "Winter Wyvern", 113: "Arc Warden",
        114: "Monkey King", 119: "Dark Willow", 120: "Pangolier",
        121: "Grimstroke", 123: "Hoodwink", 126: "Void Spirit",
        128: "Snapfire", 129: "Mars", 131: "Ringmaster",
        135: "Dawnbreaker", 136: "Marci", 137: "Primal Beast",
        138: "Muerta", 145: "Kez", 155: "Largo",
    }
    
    @classmethod
    def from_json(cls, json_str: str) -> 'DotaMatch':
        data = json.loads(json_str)
        return cls.from_dict(data)

    def __init__(self, match_id: int = 0, player_slot: int = 0, radiant_win: bool = False,
                 duration: int = 0, game_mode: int = 0, lobby_type: int = 0,
                 hero_id: int = 0, start_time: int = 0, kills: int = 0,
                 deaths: int = 0, assists: int = 0):
        self.match_id = match_id
        self.player_slot = player_slot
        self.radiant_win = radiant_win
        self.duration = duration
        self.game_mode = game_mode
        self.lobby_type = lobby_type
        self.hero_id = hero_id
        self.start_time = start_time
        self.kills = kills
        self.deaths = deaths
        self.assists = assists
    
    @property
    def player_won(self) -> bool:
        """Returns whether the player won this match"""
        return self.radiant_win if self.is_radiant else not self.radiant_win
    
    @property
    def is_radiant(self) -> bool:
        """Returns True if player is on Radiant team"""
        return self.player_slot < 128
    
    @property
    def start_time_utc(self) -> datetime:
        """Returns the match start time as UTC datetime"""
        return datetime.fromtimestamp(self.start_time, tz=timezone.utc)
    
    @property
    def match_duration(self) -> timedelta:
        """Returns the match duration as a timedelta object"""
        return timedelta(seconds=self.duration)
    
    @property
    def hero_name(self) -> str:
        """Returns the localized hero name"""
        return self.get_hero_name(self.hero_id)
    
    @staticmethod
    def get_hero_name(hero_id: int) -> str:
        """
        Gets the localized hero name based on hero ID
        
        Args:
            hero_id: The hero ID
            
        Returns:
            Localized hero name or "Unknown Hero" if not found
        """
        return DotaMatch.HERO_NAMES.get(hero_id, f"Unknown Hero ({hero_id})")
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DotaMatch':
        """Create a DotaMatch instance from a dictionary (for JSON deserialization)"""
        return cls(
            match_id=data.get('match_id', 0),
            player_slot=data.get('player_slot', 0),
            radiant_win=data.get('radiant_win', False),
            duration=data.get('duration', 0),
            game_mode=data.get('game_mode', 0),
            lobby_type=data.get('lobby_type', 0),
            hero_id=data.get('hero_id', 0),
            start_time=data.get('start_time', 0),
            kills=data.get('kills', 0),
            deaths=data.get('deaths', 0),
            assists=data.get('assists', 0)
        )
    
    def to_dict(self) -> dict:
        """Convert the DotaMatch instance to a dictionary (for JSON serialization)"""
        return {
            'match_id': self.match_id,
            'player_slot': self.player_slot,
            'radiant_win': self.radiant_win,
            'duration': self.duration,
            'game_mode': self.game_mode,
            'lobby_type': self.lobby_type,
            'hero_id': self.hero_id,
            'start_time': self.start_time,
            'kills': self.kills,
            'deaths': self.deaths,
            'assists': self.assists
        }
    
    def __str__(self) -> str:
        """String representation of the match"""
        result = "Won" if self.player_won else "Lost"
        return (f"Match {self.match_id}: {result} as {self.hero_name} "
                f"with KDA {self.kills}/{self.deaths}/{self.assists} - "
                f"{self.start_time_utc.strftime('%m/%d/%Y %H:%M')}")
    
    def __repr__(self) -> str:
        """Detailed representation of the match"""
        return (f"DotaMatch(match_id={self.match_id}, hero_id={self.hero_id}, "
                f"player_won={self.player_won}, kda={self.kills}/{self.deaths}/{self.assists})")
