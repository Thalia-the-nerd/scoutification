#!/usr/bin/env python3
"""
FRC Scouting System - FastAPI Backend
2026 Game: REBUILT
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from typing import Optional, Any
import sqlite3
import base64
from datetime import datetime
import os

app = FastAPI(title="FRC Scouting API – REBUILT 2026", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://scout.thaliathenerd.dev",
        "https://scoutsubmit.thaliathenerd.dev",
        # Allow localhost for local dev
        "http://localhost",
        "http://localhost:80",
        "http://127.0.0.1",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db_path():
    return os.getenv('DB_PATH', '/data/scouting_data.db')


# ─────────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────────

class ScoutingData(BaseModel):
    """2026 REBUILT match scouting data"""
    timestamp: Optional[str] = None

    # Match info
    match_number:  int
    team_number:   int
    alliance:      str
    scouter_name:  str

    # Pre-match
    pre_loaded_fuel: Optional[int] = 0

    # Autonomous
    auto_fuel_active_hub: Optional[int] = 0
    auto_tower_level1:    Optional[bool] = False

    # Teleoperated
    teleop_fuel_active_hub:   Optional[int] = 0
    teleop_fuel_inactive_hub: Optional[int] = 0
    fuel_collection_source:   Optional[str] = ""

    # Advanced Performance
    preferred_traversal:     Optional[str] = "Neither"
    shooter_cadence:         Optional[str] = "N/A"
    shooter_accuracy:        Optional[str] = "N/A"
    defensive_phase_summary: Optional[str] = "No Defense Played"

    # End game
    max_tower_level: Optional[str] = "None"
    minor_fouls:     Optional[int] = 0
    major_fouls:     Optional[int] = 0

    # Alliance ranking points (observed)
    energized_rp:    Optional[bool] = False
    supercharged_rp: Optional[bool] = False
    traversal_rp:    Optional[bool] = False

    general_notes: Optional[str] = ""

    robot_photo_match: Optional[str] = None

    @validator('alliance')
    def validate_alliance(cls, v):
        if v not in ('Red', 'Blue'):
            raise ValueError(f"Alliance must be 'Red' or 'Blue', got '{v}'")
        return v

    @validator('pre_loaded_fuel')
    def validate_pre_loaded_fuel(cls, v):
        if v is not None and not (0 <= v <= 8):
            raise ValueError("pre_loaded_fuel must be 0–8")
        return v

    @validator('fuel_collection_source')
    def validate_collection_source(cls, v):
        if v not in ('Depot', 'Neutral Zone', 'Outpost', ''):
            raise ValueError(f"Invalid fuel_collection_source: {v}")
        return v

    @validator('max_tower_level')
    def validate_tower_level(cls, v):
        if v not in ('None', 'Level 1', 'Level 2', 'Level 3', ''):
            raise ValueError(f"Invalid max_tower_level: {v}")
        return v or 'None'


class PreScoutingData(BaseModel):
    """Pre-scouting (pit) data from the new tabbed UI"""
    timestamp: Optional[str] = None
    pre_team_number:  int
    pre_scouter_name: str
    
    drive_system:  Optional[str] = ""
    has_turret:    Optional[str] = ""
    can_traverse_trench: Optional[str] = ""
    preferred_traversal: Optional[str] = ""
    fuel_capacity: Optional[int] = 0
    turret_fuel_shot_at_once: Optional[int] = 0

    expected_auto_fuel: Optional[int] = 0
    expected_auto_tower_level1: Optional[int] = 0
    expected_teleop_active: Optional[int] = 0
    expected_teleop_inactive: Optional[int] = 0
    expected_max_tower: Optional[str] = "None"
    expected_minor_fouls: Optional[int] = 0
    expected_major_fouls: Optional[int] = 0
    expected_energized_rp: Optional[int] = 0
    expected_supercharged_rp: Optional[int] = 0
    expected_traversal_rp: Optional[int] = 0
    expected_shooter_accuracy: Optional[str] = "N/A"
    
    robot_photo_pre: Optional[str] = None

    @validator('drive_system')
    def validate_drivetrain(cls, v):
        if v not in ('Swerve', 'Tank', 'Mecanum', ''):
            raise ValueError(f"Invalid drive_system: {v}")
        return v


# ─────────────────────────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────────────────────────

def init_database():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)

    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    if os.path.exists(schema_path):
        with open(schema_path, 'r') as f:
            try:
                conn.executescript(f.read())
            except sqlite3.Error as e:
                print(f"Schema execution warning: {e}")
    else:
        print("Warning: schema.sql not found! Database may not initialize properly.")

    conn.commit()
    conn.close()


@app.on_event("startup")
async def startup_event():
    db_path = get_db_path()
    db_dir = os.path.dirname(db_path)
    if db_dir and db_dir not in ('', '.', '/tmp'):
        try:
            os.makedirs(db_dir, exist_ok=True)
        except PermissionError:
            print(f"Warning: cannot create {db_dir}")
    init_database()
    print(f"✓ Database ready: {db_path}")


# ─────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "ok", "service": "FRC Scouting API – REBUILT 2026", "version": "2.0.0"}


@app.post("/api/submit")
async def submit_data(data: dict[str, Any]):
    try:
        print(f"DEBUG: Received submission data: {data}")
        is_pre_scout = 'pre_team_number' in data and data['pre_team_number']
        if is_pre_scout:
            print(f"DEBUG: Processing as Pre-Scouting (Pit) data")
            pit = PreScoutingData(**data)
            result = save_pre_scouting_data(pit)
            return {"status": "success", "message": f"Pre-scouting data saved for Team {pit.pre_team_number}", "data": result}
        else:
            print(f"DEBUG: Processing as Match Scouting data")
            match = ScoutingData(**data)
            result = save_match_data(match)
            return {"status": "success", "message": f"Match {match.match_number}, Team {match.team_number} saved", "data": result}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {e}")


def save_match_data(data: ScoutingData) -> dict:
    scanned_at = datetime.now().isoformat()
    match_photo_blob = None
    if data.robot_photo_match:
        try:
            # format could be "data:image/jpeg;base64,/9j/4..."
            if ',' in data.robot_photo_match:
                match_photo_blob = base64.b64decode(data.robot_photo_match.split(',')[1])
            else:
                match_photo_blob = base64.b64decode(data.robot_photo_match)
        except Exception as e:
            print(f"Warning: failed to decode match photo: {e}")

    rec = {
        'timestamp':    data.timestamp or scanned_at,
        'scanned_at':   scanned_at,
        'match_number': data.match_number,
        'team_number':  data.team_number,
        'alliance':     data.alliance,
        'scouter_name': data.scouter_name.strip().lower(),

        'pre_loaded_fuel': data.pre_loaded_fuel or 0,

        'auto_fuel_active_hub': data.auto_fuel_active_hub or 0,
        'auto_tower_level1':    1 if data.auto_tower_level1 else 0,

        'teleop_fuel_active_hub':   data.teleop_fuel_active_hub or 0,
        'teleop_fuel_inactive_hub': data.teleop_fuel_inactive_hub or 0,
        'fuel_collection_source':   data.fuel_collection_source or '',

        'preferred_traversal':     data.preferred_traversal or 'Neither',
        'shooter_cadence':         data.shooter_cadence or 'N/A',
        'shooter_accuracy':        data.shooter_accuracy or 'N/A',
        'defensive_phase_summary': data.defensive_phase_summary or 'No Defense Played',

        'max_tower_level': data.max_tower_level or 'None',
        'minor_fouls':     data.minor_fouls or 0,
        'major_fouls':     data.major_fouls or 0,

        'energized_rp':    1 if data.energized_rp    else 0,
        'supercharged_rp': 1 if data.supercharged_rp else 0,
        'traversal_rp':    1 if data.traversal_rp    else 0,
        
        'general_notes':   data.general_notes or '',
        'robot_photo':     match_photo_blob
    }

    try:
        conn = sqlite3.connect(get_db_path())
        conn.execute('''
            INSERT OR REPLACE INTO scouting_data (
                timestamp, scanned_at,
                match_number, team_number, alliance, scouter_name,
                pre_loaded_fuel,
                auto_fuel_active_hub, auto_tower_level1,
                teleop_fuel_active_hub, teleop_fuel_inactive_hub, fuel_collection_source,
                preferred_traversal, shooter_cadence, shooter_accuracy, defensive_phase_summary,
                max_tower_level, minor_fouls, major_fouls,
                energized_rp, supercharged_rp, traversal_rp, general_notes, robot_photo
            ) VALUES (
                :timestamp, :scanned_at,
                :match_number, :team_number, :alliance, :scouter_name,
                :pre_loaded_fuel,
                :auto_fuel_active_hub, :auto_tower_level1,
                :teleop_fuel_active_hub, :teleop_fuel_inactive_hub, :fuel_collection_source,
                :preferred_traversal, :shooter_cadence, :shooter_accuracy, :defensive_phase_summary,
                :max_tower_level, :minor_fouls, :major_fouls,
                :energized_rp, :supercharged_rp, :traversal_rp, :general_notes, :robot_photo
            )
        ''', rec)
        conn.commit()
        conn.close()
        return {"match_number": data.match_number, "team_number": data.team_number, "alliance": data.alliance}
    except sqlite3.Error as e:
        raise Exception(f"Database error: {e}")


def save_pre_scouting_data(data: PreScoutingData) -> dict:
    scanned_at = datetime.now().isoformat()
    pre_photo_blob = None
    if data.robot_photo_pre:
        try:
            if ',' in data.robot_photo_pre:
                pre_photo_blob = base64.b64decode(data.robot_photo_pre.split(',')[1])
            else:
                pre_photo_blob = base64.b64decode(data.robot_photo_pre)
        except Exception as e:
            print(f"Warning: failed to decode pre_scouting photo: {e}")

    try:
        conn = sqlite3.connect(get_db_path())
        conn.execute('''
            INSERT OR REPLACE INTO pre_scouting_data (
                timestamp, scanned_at,
                team_number, scouter_name,
                drive_system, has_turret, can_traverse_trench, preferred_traversal, fuel_capacity,
                turret_fuel_shot_at_once, expected_auto_fuel, expected_auto_tower_level1,
                expected_teleop_active, expected_teleop_inactive, expected_max_tower,
                expected_minor_fouls, expected_major_fouls, expected_energized_rp,
                expected_supercharged_rp, expected_traversal_rp, expected_shooter_accuracy,
                robot_photo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.timestamp or scanned_at, scanned_at,
            data.pre_team_number, data.pre_scouter_name.strip().lower(),
            data.drive_system, data.has_turret, data.can_traverse_trench, data.preferred_traversal, data.fuel_capacity,
            data.turret_fuel_shot_at_once, data.expected_auto_fuel, data.expected_auto_tower_level1,
            data.expected_teleop_active, data.expected_teleop_inactive, data.expected_max_tower,
            data.expected_minor_fouls, data.expected_major_fouls, data.expected_energized_rp,
            data.expected_supercharged_rp, data.expected_traversal_rp, data.expected_shooter_accuracy,
            pre_photo_blob
        ))
        conn.commit()
        conn.close()
        return {"team_number": data.pre_team_number}
    except sqlite3.Error as e:
        raise Exception(f"Database error: {e}")


@app.get("/api/stats")
async def get_stats():
    try:
        conn = sqlite3.connect(get_db_path())
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM scouting_data')
        match_count = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM pre_scouting_data')
        pit_count = cur.fetchone()[0]
        cur.execute('SELECT COUNT(DISTINCT team_number) FROM scouting_data')
        unique_teams = cur.fetchone()[0]
        conn.close()
        return {"match_records": match_count, "pit_records": pit_count, "unique_teams": unique_teams}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@app.get("/api/assignments")
async def get_assignments():
    try:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT scouter_name, match_number, team_number FROM scouter_assignments ORDER BY match_number, team_number')
        rows = cur.fetchall()
        assignments = [dict(row) for row in rows]
        
        cur.execute('SELECT name FROM scouters ORDER BY name')
        scouters = [row['name'] for row in cur.fetchall()]
        conn.close()
        return {"assignments": assignments, "scouters": scouters}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

class AssignmentData(BaseModel):
    scouter_name: str
    match_number: int
    team_number: int

@app.post("/api/assignments")
async def save_assignment(data: AssignmentData):
    try:
        conn = sqlite3.connect(get_db_path())
        
        # Ensure scouter exists
        conn.execute('INSERT OR IGNORE INTO scouters (name) VALUES (?)', (data.scouter_name,))
        
        conn.execute('''
            INSERT OR REPLACE INTO scouter_assignments (scouter_name, match_number, team_number)
            VALUES (?, ?, ?)
        ''', (data.scouter_name, data.match_number, data.team_number))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
