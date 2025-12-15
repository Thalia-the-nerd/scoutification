#!/usr/bin/env python3
"""
Test script for the Pit Scouting Scanner
Tests pit data functionality without requiring webcam
"""

import json
import sys
import os
import sqlite3
import base64
from datetime import datetime

# Mock cv2 and pyzbar since we don't need them for database tests
sys.modules['cv2'] = type(sys)('cv2')
sys.modules['numpy'] = type(sys)('numpy')
sys.modules['pyzbar'] = type(sys)('pyzbar')
sys.modules['pyzbar.pyzbar'] = type(sys)('pyzbar')

# Add current directory to path to import scanner
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scanner import ScoutingScanner


def create_test_image_base64():
    """Create a simple test image as base64"""
    # Create a simple 10x10 grayscale image (100 bytes)
    # Each pixel is represented by a single byte (grayscale)
    # This simulates a very small grayscale image
    test_image_data = bytes([i % 256 for i in range(100)])
    return base64.b64encode(test_image_data).decode('utf-8')


def test_pit_database_initialization():
    """Test that pit data table is created"""
    print("Testing pit database initialization...")
    scanner = ScoutingScanner('test_pit_data.db')
    
    # Check that pit_data table exists
    scanner.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pit_data'")
    result = scanner.cursor.fetchone()
    assert result is not None, "Table 'pit_data' not found"
    print("✓ Pit data table initialized successfully")
    
    scanner.conn.close()
    return True


def test_pit_data_validation():
    """Test pit data validation"""
    print("\nTesting pit data validation...")
    scanner = ScoutingScanner('test_pit_data.db')
    
    # Test valid pit data
    valid_pit_data = {
        't': 1234,
        'w': 120.5,
        'd': 'Swerve',
        'i': 'Over-bumper',
        'p': 'Java',
        'img': create_test_image_base64()
    }
    
    is_valid, message = scanner.validate_pit_data(valid_pit_data)
    assert is_valid, f"Valid pit data failed validation: {message}"
    print("✓ Valid pit data passes validation")
    
    # Test invalid pit data (missing required field)
    invalid_pit_data = {
        't': 1234,
        'w': 120.5,
        # Missing drivetrain, intake, and programming
    }
    
    is_valid, message = scanner.validate_pit_data(invalid_pit_data)
    assert not is_valid, "Invalid pit data should fail validation"
    print("✓ Invalid pit data correctly rejected")
    
    # Test invalid drivetrain type
    invalid_drivetrain = {
        't': 1234,
        'w': 120.5,
        'd': 'InvalidType',
        'i': 'Over-bumper',
        'p': 'Java'
    }
    
    is_valid, message = scanner.validate_pit_data(invalid_drivetrain)
    assert not is_valid, "Invalid drivetrain type should fail validation"
    print("✓ Invalid drivetrain type correctly rejected")
    
    scanner.conn.close()
    return True


def test_pit_data_save_and_retrieve():
    """Test saving and retrieving pit data"""
    print("\nTesting pit data save and retrieve...")
    scanner = ScoutingScanner('test_pit_data.db')
    
    # Create test pit data
    test_image_base64 = create_test_image_base64()
    test_pit_data = {
        't': 9876,
        'w': 115.8,
        'd': 'Tank',
        'i': 'Through-bumper',
        'p': 'Python',
        'img': test_image_base64
    }
    
    # Save data
    success, message = scanner.save_pit_data_to_database(test_pit_data)
    assert success, f"Failed to save pit data: {message}"
    print("✓ Pit data saved successfully")
    
    # Retrieve data
    scanner.cursor.execute('''
        SELECT team_number, robot_weight, drivetrain_type, intake_type, 
               programming_language, robot_thumbnail
        FROM pit_data
        WHERE team_number = 9876
    ''')
    result = scanner.cursor.fetchone()
    assert result is not None, "Pit data not found in database"
    assert result[0] == 9876, "Team number mismatch"
    assert abs(result[1] - 115.8) < 0.01, "Robot weight mismatch"
    assert result[2] == 'Tank', "Drivetrain type mismatch"
    assert result[3] == 'Through-bumper', "Intake type mismatch"
    assert result[4] == 'Python', "Programming language mismatch"
    assert result[5] is not None, "Robot thumbnail is missing"
    print("✓ Pit data retrieved and verified successfully")
    
    scanner.conn.close()
    return True


def test_pit_qr_code_processing():
    """Test processing pit QR code data"""
    print("\nTesting pit QR code processing...")
    scanner = ScoutingScanner('test_pit_data.db')
    
    # Simulate pit QR code data (JSON string with abbreviated keys)
    test_image_base64 = create_test_image_base64()
    pit_qr_data = json.dumps({
        't': 5555,
        'w': 122.3,
        'd': 'Mecanum',
        'i': 'Over-bumper',
        'p': 'C++',
        'img': test_image_base64
    })
    
    # Process QR code
    success = scanner.process_qr_code(pit_qr_data)
    assert success, "Failed to process pit QR code"
    print("✓ Pit QR code data processed successfully")
    
    # Verify it was saved to pit_data table
    scanner.cursor.execute('''
        SELECT team_number, drivetrain_type, programming_language
        FROM pit_data
        WHERE team_number = 5555
    ''')
    result = scanner.cursor.fetchone()
    assert result is not None, "Pit QR data not found in database"
    assert result[0] == 5555, "Team number mismatch"
    assert result[1] == 'Mecanum', "Drivetrain mismatch"
    assert result[2] == 'C++', "Programming language mismatch"
    print("✓ Pit QR code data saved to pit_data table")
    
    scanner.conn.close()
    return True


def test_pit_data_without_image():
    """Test pit data without image"""
    print("\nTesting pit data without image...")
    scanner = ScoutingScanner('test_pit_data.db')
    
    # Pit data without image
    pit_data_no_image = {
        't': 7777,
        'w': 118.0,
        'd': 'Swerve',
        'i': 'Through-bumper',
        'p': 'LabVIEW'
    }
    
    # Save data
    success, message = scanner.save_pit_data_to_database(pit_data_no_image)
    assert success, f"Failed to save pit data without image: {message}"
    print("✓ Pit data without image saved successfully")
    
    # Retrieve and verify
    scanner.cursor.execute('''
        SELECT team_number, robot_thumbnail
        FROM pit_data
        WHERE team_number = 7777
    ''')
    result = scanner.cursor.fetchone()
    assert result is not None, "Pit data not found"
    assert result[0] == 7777, "Team number mismatch"
    assert result[1] is None, "Robot thumbnail should be None"
    print("✓ Pit data without image verified")
    
    scanner.conn.close()
    return True


def test_mixed_data_processing():
    """Test that scanner can handle both match and pit data"""
    print("\nTesting mixed match and pit data processing...")
    scanner = ScoutingScanner('test_pit_data.db')
    
    # Process a match QR code
    match_qr_data = json.dumps({
        'timestamp': '2025-12-15T04:30:00Z',
        'match_number': 10,
        'team_number': 1111,
        'alliance': 'Red',
        'scouter_name': 'Test Scout',
        'auto_balls_scored_upper': 2,
        'auto_balls_scored_lower': 1,
        'auto_taxi': True
    })
    
    success = scanner.process_qr_code(match_qr_data)
    assert success, "Failed to process match QR code"
    print("✓ Match QR code processed")
    
    # Process a pit QR code
    pit_qr_data = json.dumps({
        't': 2222,
        'w': 125.0,
        'd': 'Tank',
        'i': 'Over-bumper',
        'p': 'Java'
    })
    
    success = scanner.process_qr_code(pit_qr_data)
    assert success, "Failed to process pit QR code"
    print("✓ Pit QR code processed")
    
    # Verify both are in their respective tables
    scanner.cursor.execute('SELECT COUNT(*) FROM scouting_data WHERE team_number = 1111')
    match_count = scanner.cursor.fetchone()[0]
    assert match_count > 0, "Match data not found"
    
    scanner.cursor.execute('SELECT COUNT(*) FROM pit_data WHERE team_number = 2222')
    pit_count = scanner.cursor.fetchone()[0]
    assert pit_count > 0, "Pit data not found"
    
    print("✓ Both match and pit data stored correctly")
    
    scanner.conn.close()
    return True


def cleanup():
    """Remove test database"""
    try:
        os.remove('test_pit_data.db')
        print("\n✓ Test database cleaned up")
    except (OSError, FileNotFoundError):
        pass


def main():
    """Run all tests"""
    print("="*60)
    print("FRC Pit Scouting Scanner - Unit Tests")
    print("="*60)
    
    try:
        test_pit_database_initialization()
        test_pit_data_validation()
        test_pit_data_save_and_retrieve()
        test_pit_qr_code_processing()
        test_pit_data_without_image()
        test_mixed_data_processing()
        
        print("\n" + "="*60)
        print("ALL PIT SCOUTING TESTS PASSED! ✓")
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
