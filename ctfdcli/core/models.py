"""Data models for CTFd entities."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, HttpUrl


class Challenge(BaseModel):
    """CTFd Challenge model."""
    id: int
    name: str
    description: str
    category: str
    value: int
    tags: List[str] = []
    state: str = "visible"
    max_attempts: Optional[int] = None
    type: str = "standard"
    solves: int = 0
    files: List[str] = []
    hints: List[Dict[str, Any]] = []
    solved_by_me: bool = False
    attempts: int = 0  # Current number of attempts made
    connection_info: Optional[str] = None  # Connection details from CTFd API


class Submission(BaseModel):
    """CTFd Submission model."""
    id: int
    challenge_id: int
    user_id: int
    team_id: Optional[int] = None
    ip: str
    provided: str
    type: str = "correct"
    date: datetime


class User(BaseModel):
    """CTFd User model."""
    id: int
    name: str
    email: Optional[str] = None
    score: int = 0
    place: int = 0
    website: Optional[str] = None
    affiliation: Optional[str] = None
    country: Optional[str] = None


class Team(BaseModel):
    """CTFd Team model."""
    id: int
    name: str
    email: Optional[str] = None
    score: int = 0
    place: int = 0
    website: Optional[str] = None
    affiliation: Optional[str] = None
    country: Optional[str] = None
    members: List[User] = []


class CTFProfile(BaseModel):
    """CTF Profile configuration."""
    name: str
    url: HttpUrl
    token: str
    user_mode: bool = True  # True for user mode, False for team mode
    default: bool = False


class ScoreboardEntry(BaseModel):
    """Scoreboard entry model."""
    pos: int
    account_id: int
    account_name: str
    score: int
    account_type: str = "user"  # "user" or "team"


class CTFInfo(BaseModel):
    """CTF Information model."""
    name: str
    description: Optional[str] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    freeze: Optional[datetime] = None
    mode: str = "users"  # "users" or "teams"
    registration: bool = True
    theme: Optional[str] = None
    theme_header: Optional[str] = None
    user_mode: Optional[str] = None
    team_mode: Optional[str] = None
    max_team_size: Optional[int] = None
    verification_required: bool = False
    workshop_mode: bool = False
    paused: bool = False
    rules: Optional[str] = None
    contact_info: Optional[str] = None