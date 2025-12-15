#!/usr/bin/env python3
"""
FRC Scouting System - QR Code Scanner Backend
Scans QR codes from webcam and saves data to SQLite database
"""

import cv2
import json
import numpy as np
import sqlite3
import sys
from datetime import datetime
from pyzbar import pyzbar


class ScoutingScanner:
    def __init__(self, db_path='scouting_data.db'):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.init_database()
        
        # Expected schema keys from config.js
        self.expected_keys = {
            'timestamp', 'match_number', 'team_number', 'alliance', 'scouter_name',
            'auto_balls_scored_upper', 'auto_balls_scored_lower', 'auto_taxi',
            'teleop_balls_scored_upper', 'teleop_balls_scored_lower', 'teleop_balls_missed',
            'climb_level', 'climb_time', 'defense_rating', 'driver_skill',
            'penalties', 'broke_down', 'notes'
        }
        
    def init_database(self):
        """Initialize SQLite database with schema"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # Create table if it doesn't exist
        self.cursor.execute('''
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
        self.conn.commit()
        print(f"✓ Database initialized: {self.db_path}")
        
    def validate_data(self, data):
        """Validate that the scanned data has the expected structure"""
        if not isinstance(data, dict):
            return False, "Data is not a dictionary"
        
        # Check for required fields
        required_fields = {'match_number', 'team_number', 'alliance', 'scouter_name'}
        missing_fields = required_fields - set(data.keys())
        if missing_fields:
            return False, f"Missing required fields: {missing_fields}"
        
        # Validate data types
        try:
            int(data.get('match_number', 0))
            int(data.get('team_number', 0))
            if data.get('alliance') not in ['Red', 'Blue']:
                return False, f"Invalid alliance: {data.get('alliance')}"
        except (ValueError, TypeError) as e:
            return False, f"Invalid data types: {e}"
        
        return True, "Valid"
    
    def save_to_database(self, data):
        """Save or update scouting data in the database"""
        scanned_at = datetime.now().isoformat()
        
        # Prepare data with defaults
        record = {
            'timestamp': data.get('timestamp', scanned_at),
            'match_number': int(data.get('match_number', 0)),
            'team_number': int(data.get('team_number', 0)),
            'alliance': data.get('alliance', ''),
            'scouter_name': data.get('scouter_name', ''),
            'auto_balls_scored_upper': int(data.get('auto_balls_scored_upper', 0)),
            'auto_balls_scored_lower': int(data.get('auto_balls_scored_lower', 0)),
            'auto_taxi': 1 if data.get('auto_taxi') else 0,
            'teleop_balls_scored_upper': int(data.get('teleop_balls_scored_upper', 0)),
            'teleop_balls_scored_lower': int(data.get('teleop_balls_scored_lower', 0)),
            'teleop_balls_missed': int(data.get('teleop_balls_missed', 0)),
            'climb_level': data.get('climb_level', ''),
            'climb_time': int(data.get('climb_time') or 0),
            'defense_rating': data.get('defense_rating', ''),
            'driver_skill': data.get('driver_skill', ''),
            'penalties': int(data.get('penalties', 0)),
            'broke_down': 1 if data.get('broke_down') else 0,
            'notes': data.get('notes', ''),
            'scanned_at': scanned_at
        }
        
        try:
            # Use INSERT OR REPLACE to handle duplicates
            self.cursor.execute('''
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
            self.conn.commit()
            return True, "Data saved successfully"
        except sqlite3.Error as e:
            return False, f"Database error: {e}"
    
    def process_qr_code(self, qr_data):
        """Process a decoded QR code"""
        try:
            # Parse JSON data
            data = json.loads(qr_data)
            
            # Validate data
            is_valid, message = self.validate_data(data)
            if not is_valid:
                print(f"✗ Validation failed: {message}")
                return False
            
            # Save to database
            success, message = self.save_to_database(data)
            if success:
                print(f"✓ Saved: Match {data['match_number']}, Team {data['team_number']}, {data['alliance']}")
                return True
            else:
                print(f"✗ Save failed: {message}")
                return False
                
        except json.JSONDecodeError as e:
            print(f"✗ Invalid JSON: {e}")
            return False
        except Exception as e:
            print(f"✗ Error processing QR code: {e}")
            return False
    
    def draw_qr_feedback(self, frame, decoded_objects):
        """Draw visual feedback on the frame"""
        for obj in decoded_objects:
            # Get the bounding box points
            points = obj.polygon
            if len(points) > 4:
                # If it's not a simple rectangle, use the convex hull
                hull = cv2.convexHull(
                    np.array([point for point in points], dtype=np.float32)
                )
                points = hull
            
            # Convert points to integer tuples
            n = len(points)
            for i in range(n):
                pt1 = tuple(map(int, points[i]))
                pt2 = tuple(map(int, points[(i + 1) % n]))
                cv2.line(frame, pt1, pt2, (0, 255, 0), 3)
            
            # Draw the data on the frame
            x, y, w, h = obj.rect
            # Ensure text is visible by avoiding negative coordinates
            text_y = max(y - 10, 15)
            cv2.putText(
                frame,
                "QR Code Detected",
                (x, text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )
        
        return frame
    
    def run(self):
        """Main loop to capture and process QR codes from webcam"""
        print("\n" + "="*60)
        print("FRC Scouting System - QR Code Scanner")
        print("="*60)
        print("Starting webcam...")
        
        # Open webcam
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("✗ Error: Could not open webcam")
            return
        
        print("✓ Webcam started")
        print("\nInstructions:")
        print("  - Point camera at QR code to scan")
        print("  - Press 'q' to quit")
        print("  - Press 's' to show statistics")
        print("\nWaiting for QR codes...\n")
        
        last_qr_data = None
        frame_count = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("✗ Error: Failed to capture frame")
                    break
                
                frame_count += 1
                
                # Decode QR codes in the frame (only check every 5 frames for performance)
                if frame_count % 5 == 0:
                    decoded_objects = pyzbar.decode(frame)
                    
                    if decoded_objects:
                        # Draw feedback on frame
                        frame = self.draw_qr_feedback(frame, decoded_objects)
                        
                        for obj in decoded_objects:
                            qr_data = obj.data.decode('utf-8')
                            
                            # Only process if it's a new QR code
                            if qr_data != last_qr_data:
                                last_qr_data = qr_data
                                self.process_qr_code(qr_data)
                
                # Display instructions on frame
                cv2.putText(
                    frame,
                    "Press 'q' to quit | 's' for stats",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2
                )
                
                # Show the frame
                cv2.imshow('FRC Scouting Scanner', frame)
                
                # Handle key presses
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\nShutting down...")
                    break
                elif key == ord('s'):
                    self.show_statistics()
                    
        except KeyboardInterrupt:
            print("\n\nShutting down...")
        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.conn.close()
            print("✓ Scanner stopped")
    
    def show_statistics(self):
        """Display database statistics"""
        print("\n" + "="*60)
        print("DATABASE STATISTICS")
        print("="*60)
        
        # Total records
        self.cursor.execute('SELECT COUNT(*) FROM scouting_data')
        total = self.cursor.fetchone()[0]
        print(f"Total Records: {total}")
        
        # Records by alliance
        self.cursor.execute('''
            SELECT alliance, COUNT(*) 
            FROM scouting_data 
            GROUP BY alliance
        ''')
        print("\nBy Alliance:")
        for alliance, count in self.cursor.fetchall():
            print(f"  {alliance}: {count}")
        
        # Recent entries
        self.cursor.execute('''
            SELECT match_number, team_number, alliance, scouter_name
            FROM scouting_data
            ORDER BY scanned_at DESC
            LIMIT 5
        ''')
        print("\nRecent Entries:")
        for match, team, alliance, scouter in self.cursor.fetchall():
            print(f"  Match {match} | Team {team} | {alliance} | by {scouter}")
        
        print("="*60 + "\n")


def main():
    """Main entry point"""
    try:
        scanner = ScoutingScanner()
        scanner.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
