from typing import List
from pydantic import BaseModel, ConfigDict


class Player(BaseModel):
    account_id: int = 0
    player_slot: int
    hero_id: int
    kills: int
    deaths: int
    assists: int

    model_config = ConfigDict(extra="ignore")


class Match(BaseModel):
    players: List[Player]
    radiant_win: bool
    duration: int
    pre_game_duration: int
    start_time: int
    match_id: int
    match_seq_num: int
    tower_status_radiant: int
    tower_status_dire: int
    barracks_status_radiant: int
    barracks_status_dire: int
    cluster: int
    first_blood_time: int
    lobby_type: int
    human_players: int
    leagueid: int
    game_mode: int
    flags: int
    engine: int
    radiant_score: int
    dire_score: int

    model_config = ConfigDict(extra="ignore")


class MatchHistoryResult(BaseModel):
    status: int
    matches: List[Match]

    model_config = ConfigDict(extra="ignore")


class MatchHistoryResponse(BaseModel):
    result: MatchHistoryResult

    model_config = ConfigDict(extra="ignore")
