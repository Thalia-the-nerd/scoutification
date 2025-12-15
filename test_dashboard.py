#!/usr/bin/env python3
"""
Test script for the FRC Scouting Dashboard
Tests dashboard functionality without running Streamlit
"""

import sqlite3
import pandas as pd
import sys
import os

# Add current directory to path to import dashboard
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dashboard import ScoutingDashboard


def setup_test_database():
    """Create a test database with sample data"""
    db_path = 'test_dashboard.db'
    
    # Remove if exists
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table
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
    
    # Insert test data
    test_data = [
        ('2025-03-15T10:00:00Z', 1, 1234, 'Red', 'Scout A', 2, 1, 1, 5, 3, 1, 'High', 25, 'Good', 'Excellent', 0, 0, 'Great auto', '2025-03-15T10:30:00Z'),
        ('2025-03-15T10:15:00Z', 2, 1234, 'Blue', 'Scout B', 1, 2, 1, 6, 4, 2, 'Traversal', 20, 'Excellent', 'Good', 0, 0, 'Strong climb', '2025-03-15T10:45:00Z'),
        ('2025-03-15T10:30:00Z', 3, 1234, 'Red', 'Scout C', 2, 2, 1, 7, 5, 1, 'High', 22, 'Good', 'Excellent', 0, 0, 'Consistent', '2025-03-15T11:00:00Z'),
        ('2025-03-15T11:00:00Z', 1, 5678, 'Blue', 'Scout D', 1, 0, 0, 4, 2, 3, 'Mid', 30, 'Average', 'Average', 1, 0, 'Struggled', '2025-03-15T11:30:00Z'),
        ('2025-03-15T11:15:00Z', 2, 5678, 'Red', 'Scout E', 1, 1, 1, 5, 3, 2, 'High', 28, 'Good', 'Good', 0, 0, 'Good defense', '2025-03-15T11:45:00Z'),
        ('2025-03-15T11:30:00Z', 1, 9012, 'Red', 'Scout F', 3, 2, 1, 8, 6, 0, 'Traversal', 18, 'Excellent', 'Excellent', 0, 0, 'Top performer', '2025-03-15T12:00:00Z'),
        ('2025-03-15T11:45:00Z', 2, 9012, 'Blue', 'Scout G', 2, 3, 1, 9, 7, 1, 'Traversal', 19, 'Excellent', 'Excellent', 0, 0, 'Excellent all around', '2025-03-15T12:15:00Z'),
    ]
    
    cursor.executemany('''
        INSERT INTO scouting_data (
            timestamp, match_number, team_number, alliance, scouter_name,
            auto_balls_scored_upper, auto_balls_scored_lower, auto_taxi,
            teleop_balls_scored_upper, teleop_balls_scored_lower, teleop_balls_missed,
            climb_level, climb_time, defense_rating, driver_skill,
            penalties, broke_down, notes, scanned_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', test_data)
    
    conn.commit()
    conn.close()
    
    return db_path


def test_load_data():
    """Test loading aggregated data"""
    print("Testing load_data...")
    db_path = setup_test_database()
    dashboard = ScoutingDashboard(db_path)
    
    df = dashboard.load_data()
    
    assert not df.empty, "Data should not be empty"
    assert len(df) == 3, f"Expected 3 teams, got {len(df)}"
    assert 'team_number' in df.columns, "team_number column should exist"
    assert 'Avg_Auto' in df.columns, "Avg_Auto column should exist"
    assert 'Avg_Teleop' in df.columns, "Avg_Teleop column should exist"
    assert 'Climb_Success_Rate' in df.columns, "Climb_Success_Rate column should exist"
    
    print("✓ load_data works correctly")
    
    os.remove(db_path)
    return True


def test_load_raw_data():
    """Test loading raw data"""
    print("\nTesting load_raw_data...")
    db_path = setup_test_database()
    dashboard = ScoutingDashboard(db_path)
    
    df = dashboard.load_raw_data()
    
    assert not df.empty, "Raw data should not be empty"
    assert len(df) == 7, f"Expected 7 records, got {len(df)}"
    assert 'match_number' in df.columns, "match_number column should exist"
    assert 'team_number' in df.columns, "team_number column should exist"
    assert 'alliance' in df.columns, "alliance column should exist"
    
    print("✓ load_raw_data works correctly")
    
    os.remove(db_path)
    return True


def test_load_team_match_data():
    """Test loading team-specific match data"""
    print("\nTesting load_team_match_data...")
    db_path = setup_test_database()
    dashboard = ScoutingDashboard(db_path)
    
    # Test for team 1234
    df = dashboard.load_team_match_data(1234)
    
    assert not df.empty, "Team match data should not be empty"
    assert len(df) == 3, f"Expected 3 matches for team 1234, got {len(df)}"
    assert 'match_number' in df.columns, "match_number column should exist"
    assert 'auto_score' in df.columns, "auto_score column should exist"
    assert 'teleop_score' in df.columns, "teleop_score column should exist"
    assert 'climbed' in df.columns, "climbed column should exist"
    
    # Verify calculated columns - get first match data from our test set
    first_match = df.iloc[0]
    # From test data: auto_balls_scored_upper=2, auto_balls_scored_lower=1
    expected_auto_score = 3
    # From test data: teleop_balls_scored_upper=5, teleop_balls_scored_lower=3
    expected_teleop_score = 8
    
    assert first_match['auto_score'] == expected_auto_score, f"Auto score should be {expected_auto_score}"
    assert first_match['teleop_score'] == expected_teleop_score, f"Teleop score should be {expected_teleop_score}"
    assert first_match['climbed'] == 1, "Should have climbed"
    
    print("✓ load_team_match_data works correctly")
    
    os.remove(db_path)
    return True


def test_match_predictor_logic():
    """Test match predictor calculations"""
    print("\nTesting match predictor logic...")
    db_path = setup_test_database()
    dashboard = ScoutingDashboard(db_path)
    
    df = dashboard.load_data()
    
    # Simulate selecting teams
    red_alliance = [1234, 5678]
    blue_alliance = [9012]
    
    red_stats = df[df['team_number'].isin(red_alliance)]
    blue_stats = df[df['team_number'].isin(blue_alliance)]
    
    red_total = red_stats['Avg_Auto'].sum() + red_stats['Avg_Teleop'].sum()
    blue_total = blue_stats['Avg_Auto'].sum() + blue_stats['Avg_Teleop'].sum()
    
    assert red_total > 0, "Red total should be greater than 0"
    assert blue_total > 0, "Blue total should be greater than 0"
    
    # Calculate probabilities
    total_score = red_total + blue_total
    red_probability = (red_total / total_score) * 100
    blue_probability = (blue_total / total_score) * 100
    
    assert abs(red_probability + blue_probability - 100) < 0.01, "Probabilities should sum to 100%"
    
    print("✓ Match predictor logic works correctly")
    
    os.remove(db_path)
    return True


def cleanup():
    """Remove test database if it exists"""
    try:
        if os.path.exists('test_dashboard.db'):
            os.remove('test_dashboard.db')
        print("\n✓ Test database cleaned up")
    except (OSError, FileNotFoundError):
        pass


def main():
    """Run all tests"""
    print("="*60)
    print("FRC Scouting Dashboard - Unit Tests")
    print("="*60)
    
    try:
        test_load_data()
        test_load_raw_data()
        test_load_team_match_data()
        test_match_predictor_logic()
        
        print("\n" + "="*60)
        print("ALL TESTS PASSED! ✓")
        print("="*60)
        
        cleanup()
        return 0
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        cleanup()
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        cleanup()
        return 1


if __name__ == '__main__':
    sys.exit(main())
