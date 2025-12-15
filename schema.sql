-- FRC Scouting System Database Schema
-- SQLite database for storing scouting data

-- Match scouting data table
CREATE TABLE IF NOT EXISTS scouting_data (
    -- Primary key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Timestamp from the form submission
    timestamp TEXT NOT NULL,
    
    -- Match Information
    match_number INTEGER NOT NULL,
    team_number INTEGER NOT NULL,
    alliance TEXT NOT NULL CHECK(alliance IN ('Red', 'Blue')),
    scouter_name TEXT NOT NULL,
    
    -- Autonomous Period
    auto_balls_scored_upper INTEGER DEFAULT 0,
    auto_balls_scored_lower INTEGER DEFAULT 0,
    auto_taxi INTEGER DEFAULT 0 CHECK(auto_taxi IN (0, 1)),
    
    -- Teleoperated Period
    teleop_balls_scored_upper INTEGER DEFAULT 0,
    teleop_balls_scored_lower INTEGER DEFAULT 0,
    teleop_balls_missed INTEGER DEFAULT 0,
    
    -- Endgame
    climb_level TEXT CHECK(climb_level IN ('None', 'Low', 'Mid', 'High', 'Traversal', '')),
    climb_time INTEGER DEFAULT 0,
    
    -- Performance Assessment
    defense_rating TEXT CHECK(defense_rating IN ('None', 'Poor', 'Average', 'Good', 'Excellent', '')),
    driver_skill TEXT CHECK(driver_skill IN ('Poor', 'Average', 'Good', 'Excellent', '')),
    penalties INTEGER DEFAULT 0,
    broke_down INTEGER DEFAULT 0 CHECK(broke_down IN (0, 1)),
    
    -- Notes
    notes TEXT,
    
    -- Metadata
    scanned_at TEXT NOT NULL,
    
    -- Unique constraint to prevent duplicate entries for same match/team/alliance
    UNIQUE(match_number, team_number, alliance)
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_match_number ON scouting_data(match_number);
CREATE INDEX IF NOT EXISTS idx_team_number ON scouting_data(team_number);
CREATE INDEX IF NOT EXISTS idx_alliance ON scouting_data(alliance);
CREATE INDEX IF NOT EXISTS idx_scanned_at ON scouting_data(scanned_at);

-- View for easy data analysis
CREATE VIEW IF NOT EXISTS scouting_summary AS
SELECT 
    match_number,
    team_number,
    alliance,
    scouter_name,
    -- Auto performance
    (auto_balls_scored_upper + auto_balls_scored_lower) as auto_total_balls,
    auto_taxi,
    -- Teleop performance
    (teleop_balls_scored_upper + teleop_balls_scored_lower) as teleop_total_balls,
    teleop_balls_missed,
    -- Accuracy
    CASE 
        WHEN (teleop_balls_scored_upper + teleop_balls_scored_lower + teleop_balls_missed) > 0 
        THEN ROUND(
            100.0 * (teleop_balls_scored_upper + teleop_balls_scored_lower) / 
            (teleop_balls_scored_upper + teleop_balls_scored_lower + teleop_balls_missed), 
            2
        )
        ELSE 0 
    END as shooting_accuracy,
    -- Endgame
    climb_level,
    climb_time,
    -- Overall
    defense_rating,
    driver_skill,
    penalties,
    broke_down,
    timestamp
FROM scouting_data;

-- Pit scouting data table
CREATE TABLE IF NOT EXISTS pit_data (
    -- Primary key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Team Information
    team_number INTEGER NOT NULL UNIQUE,
    robot_weight REAL NOT NULL,
    drivetrain_type TEXT NOT NULL CHECK(drivetrain_type IN ('Swerve', 'Tank', 'Mecanum')),
    intake_type TEXT NOT NULL CHECK(intake_type IN ('Over-bumper', 'Through-bumper')),
    programming_language TEXT NOT NULL CHECK(programming_language IN ('Java', 'C++', 'Python', 'LabVIEW')),
    
    -- Robot Photo (BLOB for binary data)
    robot_thumbnail BLOB,
    
    -- Metadata
    scanned_at TEXT NOT NULL
);

-- Index for faster team lookup
CREATE INDEX IF NOT EXISTS idx_pit_team_number ON pit_data(team_number);
