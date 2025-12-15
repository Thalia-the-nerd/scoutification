#!/usr/bin/env python3
"""
Test script for the FRC Scouting Conflict Resolver
Tests conflict resolution functionality
"""

import json
import sys
import os
import sqlite3
import pandas as pd
from datetime import datetime

# Add current directory to path to import resolve_conflicts
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from resolve_conflicts import ConflictResolver


def setup_test_database():
    """Create a test database with duplicate entries"""
    db_path = 'test_conflicts.db'
    
    # Remove existing test database
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table with same schema as scouting_data
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
            scanned_at TEXT NOT NULL
        )
    ''')
    
    # Insert test data with duplicates
    test_records = [
        # Normal record (no duplicate)
        (1, '2025-12-15T04:00:00Z', 1, 1111, 'Blue', 'Scout A', 
         2, 1, 1, 5, 3, 2, 'High', 25, 'Good', 'Excellent', 0, 0, 
         'Good performance', '2025-12-15T04:30:00Z'),
        
        # Duplicate pair for Match 2, Team 2222
        (2, '2025-12-15T04:05:00Z', 2, 2222, 'Red', 'Scout B',
         3, 2, 1, 8, 4, 1, 'Traversal', 20, 'Excellent', 'Good', 0, 0,
         'Excellent climbing', '2025-12-15T04:35:00Z'),
        (3, '2025-12-15T04:06:00Z', 2, 2222, 'Red', 'Scout C',
         2, 1, 0, 6, 5, 2, 'High', 22, 'Good', 'Excellent', 1, 0,
         'Good shooter', '2025-12-15T04:36:00Z'),
        
        # Another normal record
        (4, '2025-12-15T04:10:00Z', 3, 3333, 'Blue', 'Scout D',
         1, 0, 1, 4, 2, 3, 'Mid', 30, 'Average', 'Average', 0, 0,
         'Average performance', '2025-12-15T04:40:00Z'),
        
        # Triple duplicate for Match 4, Team 4444
        (5, '2025-12-15T04:15:00Z', 4, 4444, 'Red', 'Scout E',
         4, 3, 1, 10, 5, 0, 'Traversal', 15, 'Excellent', 'Excellent', 0, 0,
         'Outstanding', '2025-12-15T04:45:00Z'),
        (6, '2025-12-15T04:16:00Z', 4, 4444, 'Red', 'Scout F',
         3, 2, 1, 9, 4, 1, 'High', 18, 'Good', 'Good', 0, 0,
         'Very good', '2025-12-15T04:46:00Z'),
        (7, '2025-12-15T04:17:00Z', 4, 4444, 'Red', 'Scout G',
         5, 4, 1, 11, 6, 0, 'Traversal', 16, 'Excellent', 'Excellent', 0, 0,
         'Amazing', '2025-12-15T04:47:00Z'),
    ]
    
    for record in test_records:
        cursor.execute('''
            INSERT INTO scouting_data VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', record)
    
    conn.commit()
    conn.close()
    
    print(f"✓ Test database created: {db_path}")
    print(f"  - 7 total records")
    print(f"  - 2 duplicate records for Match 2, Team 2222")
    print(f"  - 3 duplicate records for Match 4, Team 4444")
    
    return db_path


def test_load_database():
    """Test loading database into DataFrame"""
    print("\n" + "="*60)
    print("Test 1: Loading Database")
    print("="*60)
    
    db_path = setup_test_database()
    resolver = ConflictResolver(db_path)
    
    success = resolver.load_database()
    assert success, "Failed to load database"
    assert resolver.df is not None, "DataFrame is None"
    assert len(resolver.df) == 7, f"Expected 7 records, got {len(resolver.df)}"
    
    resolver.close()
    print("✓ Test passed: Database loaded successfully")
    
    # Cleanup
    os.remove(db_path)


def test_find_duplicates():
    """Test finding duplicate entries"""
    print("\n" + "="*60)
    print("Test 2: Finding Duplicates")
    print("="*60)
    
    db_path = setup_test_database()
    resolver = ConflictResolver(db_path)
    resolver.load_database()
    
    duplicates = resolver.find_duplicates()
    assert duplicates is not None, "No duplicates found when they should exist"
    assert len(duplicates) == 5, f"Expected 5 duplicate records, got {len(duplicates)}"
    
    # Check that we have the right duplicates
    duplicate_groups = duplicates.groupby(['match_number', 'team_number'])
    assert len(duplicate_groups) == 2, f"Expected 2 duplicate groups, got {len(duplicate_groups)}"
    
    resolver.close()
    print("✓ Test passed: Duplicates found correctly")
    print(f"  - Found 5 duplicate records in 2 groups")
    
    # Cleanup
    os.remove(db_path)


def test_average_records():
    """Test averaging two records"""
    print("\n" + "="*60)
    print("Test 3: Averaging Records")
    print("="*60)
    
    db_path = setup_test_database()
    resolver = ConflictResolver(db_path)
    resolver.load_database()
    
    # Get the first duplicate pair (Match 2, Team 2222)
    duplicates = resolver.find_duplicates()
    match2_dups = duplicates[(duplicates['match_number'] == 2) & (duplicates['team_number'] == 2222)]
    
    row1 = match2_dups.iloc[0]
    row2 = match2_dups.iloc[1]
    
    merged = resolver.average_records(row1, row2)
    
    # Check numeric averages
    assert merged['auto_balls_scored_upper'] == 2.5, f"Expected 2.5, got {merged['auto_balls_scored_upper']}"
    assert merged['auto_balls_scored_lower'] == 1.5, f"Expected 1.5, got {merged['auto_balls_scored_lower']}"
    assert merged['teleop_balls_scored_upper'] == 7.0, f"Expected 7.0, got {merged['teleop_balls_scored_upper']}"
    
    # Check string merging
    assert '/' in merged['scouter_name'] or merged['scouter_name'] in ['Scout B', 'Scout C'], \
        f"Unexpected scouter_name: {merged['scouter_name']}"
    
    resolver.close()
    print("✓ Test passed: Records averaged correctly")
    print(f"  - Numeric fields averaged")
    print(f"  - String fields merged")
    
    # Cleanup
    os.remove(db_path)


def test_no_duplicates():
    """Test behavior when no duplicates exist"""
    print("\n" + "="*60)
    print("Test 4: No Duplicates Case")
    print("="*60)
    
    # Create database with no duplicates
    db_path = 'test_no_dups.db'
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scouting_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            match_number INTEGER NOT NULL,
            team_number INTEGER NOT NULL,
            alliance TEXT NOT NULL,
            scouter_name TEXT NOT NULL,
            auto_balls_scored_upper INTEGER DEFAULT 0,
            auto_balls_scored_lower INTEGER DEFAULT 0,
            auto_taxi INTEGER DEFAULT 0,
            teleop_balls_scored_upper INTEGER DEFAULT 0,
            teleop_balls_scored_lower INTEGER DEFAULT 0,
            teleop_balls_missed INTEGER DEFAULT 0,
            climb_level TEXT,
            climb_time INTEGER DEFAULT 0,
            defense_rating TEXT,
            driver_skill TEXT,
            penalties INTEGER DEFAULT 0,
            broke_down INTEGER DEFAULT 0,
            notes TEXT,
            scanned_at TEXT NOT NULL
        )
    ''')
    
    # Insert unique records only
    cursor.execute('''
        INSERT INTO scouting_data VALUES 
        (1, '2025-12-15T04:00:00Z', 1, 1111, 'Blue', 'Scout A', 
         2, 1, 1, 5, 3, 2, 'High', 25, 'Good', 'Excellent', 0, 0, 
         'Good performance', '2025-12-15T04:30:00Z'),
        (2, '2025-12-15T04:05:00Z', 2, 2222, 'Red', 'Scout B',
         3, 2, 1, 8, 4, 1, 'Traversal', 20, 'Excellent', 'Good', 0, 0,
         'Excellent climbing', '2025-12-15T04:35:00Z')
    ''')
    
    conn.commit()
    conn.close()
    
    resolver = ConflictResolver(db_path)
    resolver.load_database()
    
    duplicates = resolver.find_duplicates()
    assert duplicates is None, "Found duplicates when none should exist"
    
    resolver.close()
    print("✓ Test passed: Correctly identified no duplicates")
    
    # Cleanup
    os.remove(db_path)


def cleanup():
    """Remove test databases"""
    test_files = ['test_conflicts.db', 'test_no_dups.db']
    for file in test_files:
        try:
            if os.path.exists(file):
                os.remove(file)
        except OSError:
            pass


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("FRC Conflict Resolver - Unit Tests")
    print("="*60)
    
    try:
        test_load_database()
        test_find_duplicates()
        test_average_records()
        test_no_duplicates()
        
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
