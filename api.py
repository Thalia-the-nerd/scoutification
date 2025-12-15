#!/usr/bin/env python3
"""
FRC Scouting System - FastAPI Backend
RESTful API for receiving scouting data via HTTP POST
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from typing import Optional, Any
import sqlite3
import base64
from datetime import datetime
import os

app = FastAPI(title="FRC Scouting API", version="1.0.0")

# CORS middleware to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
def get_db_path():
    """Get database path from environment or default"""
    return os.getenv('DB_PATH', '/data/scouting_data.db')


class ScoutingData(BaseModel):
    """Model for match scouting data"""
    timestamp: Optional[str] = None
    match_number: int
    team_number: int
    alliance: str
    scouter_name: str
    auto_balls_scored_upper: Optional[int] = 0
    auto_balls_scored_lower: Optional[int] = 0
    auto_taxi: Optional[bool] = False
    teleop_balls_scored_upper: Optional[int] = 0
    teleop_balls_scored_lower: Optional[int] = 0
    teleop_balls_missed: Optional[int] = 0
    climb_level: Optional[str] = ""
    climb_time: Optional[int] = 0
    defense_rating: Optional[str] = ""
    driver_skill: Optional[str] = ""
    penalties: Optional[int] = 0
    broke_down: Optional[bool] = False
    notes: Optional[str] = ""

    @validator('alliance')
    def validate_alliance(cls, v):
        if v not in ['Red', 'Blue']:
            raise ValueError(f"Alliance must be 'Red' or 'Blue', got '{v}'")
        return v

    @validator('climb_level')
    def validate_climb_level(cls, v):
        valid_levels = ['None', 'Low', 'Mid', 'High', 'Traversal', '']
        if v not in valid_levels:
            raise ValueError(f"Invalid climb_level: {v}")
        return v

    @validator('defense_rating')
    def validate_defense_rating(cls, v):
        valid_ratings = ['None', 'Poor', 'Average', 'Good', 'Excellent', '']
        if v not in valid_ratings:
            raise ValueError(f"Invalid defense_rating: {v}")
        return v

    @validator('driver_skill')
    def validate_driver_skill(cls, v):
        valid_skills = ['Poor', 'Average', 'Good', 'Excellent', '']
        if v not in valid_skills:
            raise ValueError(f"Invalid driver_skill: {v}")
        return v


class PitData(BaseModel):
    """Model for pit scouting data with abbreviated keys"""
    t: int  # team_number
    w: float  # robot_weight
    d: str  # drivetrain_type
    i: str  # intake_type
    p: str  # programming_language
    img: Optional[str] = None  # robot_thumbnail (base64)

    @validator('d')
    def validate_drivetrain(cls, v):
        if v not in ['Swerve', 'Tank', 'Mecanum']:
            raise ValueError(f"Invalid drivetrain_type: {v}")
        return v

    @validator('i')
    def validate_intake(cls, v):
        if v not in ['Over-bumper', 'Through-bumper']:
            raise ValueError(f"Invalid intake_type: {v}")
        return v

    @validator('p')
    def validate_programming(cls, v):
        if v not in ['Java', 'C++', 'Python', 'LabVIEW']:
            raise ValueError(f"Invalid programming_language: {v}")
        return v


def init_database():
    """Initialize SQLite database with schema"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create match scouting table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scouting_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            match_number INTEGER NOT NULL,
            team_number INTEGER NOT NULL,
            alliance TEXT NOT NULL CHECK(alliance IN ('Red', 'Blue')),
            scouter_name TEXT NOT NULL,
            auto_balls_scored_upper INTEGER DEFAULT 0,
            auto_balls_scored_lower INTEGER DEFAULT 0,
            auto_taxi INTEGER DEFAULT 0 CHECK(auto_taxi IN (0, 1)),
            teleop_balls_scored_upper INTEGER DEFAULT 0,
            teleop_balls_scored_lower INTEGER DEFAULT 0,
            teleop_balls_missed INTEGER DEFAULT 0,
            climb_level TEXT CHECK(climb_level IN ('None', 'Low', 'Mid', 'High', 'Traversal', '')),
            climb_time INTEGER DEFAULT 0,
            defense_rating TEXT CHECK(defense_rating IN ('None', 'Poor', 'Average', 'Good', 'Excellent', '')),
            driver_skill TEXT CHECK(driver_skill IN ('Poor', 'Average', 'Good', 'Excellent', '')),
            penalties INTEGER DEFAULT 0,
            broke_down INTEGER DEFAULT 0 CHECK(broke_down IN (0, 1)),
            notes TEXT,
            scanned_at TEXT NOT NULL,
            UNIQUE(match_number, team_number, alliance)
        )
    ''')
    
    # Create pit scouting table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pit_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_number INTEGER NOT NULL UNIQUE,
            robot_weight REAL NOT NULL,
            drivetrain_type TEXT NOT NULL CHECK(drivetrain_type IN ('Swerve', 'Tank', 'Mecanum')),
            intake_type TEXT NOT NULL CHECK(intake_type IN ('Over-bumper', 'Through-bumper')),
            programming_language TEXT NOT NULL CHECK(programming_language IN ('Java', 'C++', 'Python', 'LabVIEW')),
            robot_thumbnail BLOB,
            scanned_at TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    db_path = get_db_path()
    # Ensure data directory exists (skip if path is in /tmp or current dir)
    db_dir = os.path.dirname(db_path)
    if db_dir and db_dir not in ['', '.', '/tmp']:
        try:
            os.makedirs(db_dir, exist_ok=True)
        except PermissionError:
            print(f"Warning: Cannot create directory {db_dir}, using database path as-is")
    init_database()
    print(f"✓ Database initialized: {db_path}")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "FRC Scouting API",
        "version": "1.0.0"
    }


@app.post("/api/submit")
async def submit_data(data: dict[str, Any]):
    """
    Submit scouting data to the database.
    Accepts both match scouting data and pit scouting data.
    """
    try:
        # Check if this is pit data (contains abbreviated keys)
        is_pit_data = 't' in data and 'w' in data and 'd' in data
        
        if is_pit_data:
            # Validate as pit data
            pit_data = PitData(**data)
            result = save_pit_data(pit_data)
            return {
                "status": "success",
                "message": f"Pit data saved for Team {pit_data.t}",
                "data": result
            }
        else:
            # Validate as match data
            match_data = ScoutingData(**data)
            result = save_match_data(match_data)
            return {
                "status": "success",
                "message": f"Match data saved: Match {match_data.match_number}, Team {match_data.team_number}",
                "data": result
            }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


def save_match_data(data: ScoutingData) -> dict:
    """Save match scouting data to database"""
    db_path = get_db_path()
    scanned_at = datetime.now().isoformat()
    
    # Prepare record
    record = {
        'timestamp': data.timestamp or scanned_at,
        'match_number': data.match_number,
        'team_number': data.team_number,
        'alliance': data.alliance,
        'scouter_name': data.scouter_name,
        'auto_balls_scored_upper': data.auto_balls_scored_upper,
        'auto_balls_scored_lower': data.auto_balls_scored_lower,
        'auto_taxi': 1 if data.auto_taxi else 0,
        'teleop_balls_scored_upper': data.teleop_balls_scored_upper,
        'teleop_balls_scored_lower': data.teleop_balls_scored_lower,
        'teleop_balls_missed': data.teleop_balls_missed,
        'climb_level': data.climb_level,
        'climb_time': data.climb_time or 0,
        'defense_rating': data.defense_rating,
        'driver_skill': data.driver_skill,
        'penalties': data.penalties,
        'broke_down': 1 if data.broke_down else 0,
        'notes': data.notes,
        'scanned_at': scanned_at
    }
    
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        
        # Use INSERT OR REPLACE to handle duplicates
        cursor.execute('''
            INSERT OR REPLACE INTO scouting_data (
                timestamp, match_number, team_number, alliance, scouter_name,
                auto_balls_scored_upper, auto_balls_scored_lower, auto_taxi,
                teleop_balls_scored_upper, teleop_balls_scored_lower, teleop_balls_missed,
                climb_level, climb_time, defense_rating, driver_skill,
                penalties, broke_down, notes, scanned_at
            ) VALUES (
                :timestamp, :match_number, :team_number, :alliance, :scouter_name,
                :auto_balls_scored_upper, :auto_balls_scored_lower, :auto_taxi,
                :teleop_balls_scored_upper, :teleop_balls_scored_lower, :teleop_balls_missed,
                :climb_level, :climb_time, :defense_rating, :driver_skill,
                :penalties, :broke_down, :notes, :scanned_at
            )
        ''', record)
        
        conn.commit()
        conn.close()
        
        return {
            "match_number": data.match_number,
            "team_number": data.team_number,
            "alliance": data.alliance
        }
    
    except sqlite3.Error as e:
        raise Exception(f"Database error: {e}")


def save_pit_data(data: PitData) -> dict:
    """Save pit scouting data to database"""
    scanned_at = datetime.now().isoformat()
    
    # Decode Base64 image if present
    thumbnail_blob = None
    if data.img:
        try:
            thumbnail_blob = base64.b64decode(data.img)
        except Exception as e:
            print(f"Warning: Failed to decode image: {e}")
    
    # Prepare record
    record = {
        'team_number': data.t,
        'robot_weight': data.w,
        'drivetrain_type': data.d,
        'intake_type': data.i,
        'programming_language': data.p,
        'robot_thumbnail': thumbnail_blob,
        'scanned_at': scanned_at
    }
    
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        
        # Use INSERT OR REPLACE to handle duplicates
        cursor.execute('''
            INSERT OR REPLACE INTO pit_data (
                team_number, robot_weight, drivetrain_type, intake_type,
                programming_language, robot_thumbnail, scanned_at
            ) VALUES (
                :team_number, :robot_weight, :drivetrain_type, :intake_type,
                :programming_language, :robot_thumbnail, :scanned_at
            )
        ''', record)
        
        conn.commit()
        conn.close()
        
        return {
            "team_number": data.t,
            "robot_weight": data.w,
            "drivetrain_type": data.d
        }
    
    except sqlite3.Error as e:
        raise Exception(f"Database error: {e}")


@app.get("/api/stats")
async def get_stats():
    """Get database statistics"""
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        
        # Get match data count
        cursor.execute('SELECT COUNT(*) FROM scouting_data')
        match_count = cursor.fetchone()[0]
        
        # Get pit data count
        cursor.execute('SELECT COUNT(*) FROM pit_data')
        pit_count = cursor.fetchone()[0]
        
        # Get unique teams
        cursor.execute('SELECT COUNT(DISTINCT team_number) FROM scouting_data')
        unique_teams = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "match_records": match_count,
            "pit_records": pit_count,
            "unique_teams": unique_teams
        }
    
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
