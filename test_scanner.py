#!/usr/bin/env python3
"""
Test script for the FRC Scouting Scanner
Tests database functionality without requiring webcam
"""

import json
import sys
import os
import sqlite3
from datetime import datetime

# Mock cv2 and pyzbar since we don't need them for database tests
sys.modules['cv2'] = type(sys)('cv2')
sys.modules['numpy'] = type(sys)('numpy')
sys.modules['pyzbar'] = type(sys)('pyzbar')
sys.modules['pyzbar.pyzbar'] = type(sys)('pyzbar')

# Add current directory to path to import scanner
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scanner import ScoutingScanner


def test_database_initialization():
    """Test that database initializes correctly"""
    print("Testing database initialization...")
    scanner = ScoutingScanner('test_scouting_data.db')
    
    # Check that tables exist
    scanner.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scouting_data'")
    result = scanner.cursor.fetchone()
    assert result is not None, "Table 'scouting_data' not found"
    print("✓ Database initialized successfully")
    
    scanner.conn.close()
    return True


def test_data_validation():
    """Test data validation"""
    print("\nTesting data validation...")
    scanner = ScoutingScanner('test_scouting_data.db')
    
    # Test valid data
    valid_data = {
        'match_number': 42,
        'team_number': 1234,
        'alliance': 'Blue',
        'scouter_name': 'Test Scout',
        'auto_balls_scored_upper': 1,
        'auto_balls_scored_lower': 0,
        'auto_taxi': False,
        'teleop_balls_scored_upper': 5,
        'teleop_balls_scored_lower': 3,
        'teleop_balls_missed': 2,
        'climb_level': 'High',
        'climb_time': 25,
        'defense_rating': 'Good',
        'driver_skill': 'Excellent',
        'penalties': 0,
        'broke_down': False,
        'notes': 'Great performance!'
    }
    
    is_valid, message = scanner.validate_data(valid_data)
    assert is_valid, f"Valid data failed validation: {message}"
    print("✓ Valid data passes validation")
    
    # Test invalid data (missing required field)
    invalid_data = {
        'match_number': 42,
        'team_number': 1234,
        # Missing alliance and scouter_name
    }
    
    is_valid, message = scanner.validate_data(invalid_data)
    assert not is_valid, "Invalid data should fail validation"
    print("✓ Invalid data correctly rejected")
    
    scanner.conn.close()
    return True


def test_data_save_and_retrieve():
    """Test saving and retrieving data"""
    print("\nTesting data save and retrieve...")
    scanner = ScoutingScanner('test_scouting_data.db')
    
    # Create test data
    test_data = {
        'timestamp': '2025-12-15T04:30:00Z',
        'match_number': 42,
        'team_number': 1234,
        'alliance': 'Blue',
        'scouter_name': 'Test Scout',
        'auto_balls_scored_upper': 1,
        'auto_balls_scored_lower': 0,
        'auto_taxi': False,
        'teleop_balls_scored_upper': 5,
        'teleop_balls_scored_lower': 3,
        'teleop_balls_missed': 2,
        'climb_level': 'High',
        'climb_time': 25,
        'defense_rating': 'Good',
        'driver_skill': 'Excellent',
        'penalties': 0,
        'broke_down': False,
        'notes': 'Great performance!'
    }
    
    # Save data
    success, message = scanner.save_to_database(test_data)
    assert success, f"Failed to save data: {message}"
    print("✓ Data saved successfully")
    
    # Retrieve data
    scanner.cursor.execute('''
        SELECT match_number, team_number, alliance, auto_balls_scored_upper, climb_level
        FROM scouting_data
        WHERE match_number = 42 AND team_number = 1234
    ''')
    result = scanner.cursor.fetchone()
    assert result is not None, "Data not found in database"
    assert result[0] == 42, "Match number mismatch"
    assert result[1] == 1234, "Team number mismatch"
    assert result[2] == 'Blue', "Alliance mismatch"
    assert result[3] == 1, "Auto balls upper mismatch"
    assert result[4] == 'High', "Climb level mismatch"
    print("✓ Data retrieved and verified successfully")
    
    scanner.conn.close()
    return True


def test_qr_code_processing():
    """Test processing QR code data"""
    print("\nTesting QR code processing...")
    scanner = ScoutingScanner('test_scouting_data.db')
    
    # Simulate QR code data (JSON string)
    qr_data = json.dumps({
        'timestamp': '2025-12-15T04:30:00Z',
        'match_number': 99,
        'team_number': 5678,
        'alliance': 'Red',
        'scouter_name': 'QR Test Scout',
        'auto_balls_scored_upper': 2,
        'auto_balls_scored_lower': 1,
        'auto_taxi': True,
        'teleop_balls_scored_upper': 8,
        'teleop_balls_scored_lower': 4,
        'teleop_balls_missed': 1,
        'climb_level': 'Traversal',
        'climb_time': 20,
        'defense_rating': 'Excellent',
        'driver_skill': 'Good',
        'penalties': 1,
        'broke_down': False,
        'notes': 'Excellent climbing ability'
    })
    
    # Process QR code
    success = scanner.process_qr_code(qr_data)
    assert success, "Failed to process QR code"
    print("✓ QR code data processed successfully")
    
    # Verify it was saved
    scanner.cursor.execute('''
        SELECT match_number, team_number, alliance
        FROM scouting_data
        WHERE match_number = 99 AND team_number = 5678
    ''')
    result = scanner.cursor.fetchone()
    assert result is not None, "QR data not found in database"
    print("✓ QR code data saved to database")
    
    scanner.conn.close()
    return True


def cleanup():
    """Remove test database"""
    try:
        os.remove('test_scouting_data.db')
        print("\n✓ Test database cleaned up")
    except:
        pass


def main():
    """Run all tests"""
    print("="*60)
    print("FRC Scouting Scanner - Unit Tests")
    print("="*60)
    
    try:
        test_database_initialization()
        test_data_validation()
        test_data_save_and_retrieve()
        test_qr_code_processing()
        
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
