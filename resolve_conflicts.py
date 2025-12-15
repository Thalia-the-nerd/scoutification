#!/usr/bin/env python3
"""
FRC Scouting System - Conflict Resolution Tool
Identifies and resolves duplicate entries in scouting_data.db
"""

import sqlite3
import pandas as pd
import sys
from datetime import datetime


class ConflictResolver:
    def __init__(self, db_path='scouting_data.db'):
        """Initialize the conflict resolver with database path"""
        self.db_path = db_path
        self.conn = None
        self.df = None
        
        # Define numeric and string fields based on schema
        self.numeric_fields = [
            'match_number', 'team_number',
            'auto_balls_scored_upper', 'auto_balls_scored_lower', 'auto_taxi',
            'teleop_balls_scored_upper', 'teleop_balls_scored_lower', 'teleop_balls_missed',
            'climb_time', 'penalties', 'broke_down'
        ]
        
        self.string_fields = [
            'alliance', 'scouter_name', 'climb_level', 
            'defense_rating', 'driver_skill', 'notes', 'timestamp', 'scanned_at'
        ]
    
    def load_database(self):
        """Load the scouting database into a DataFrame"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.df = pd.read_sql_query("SELECT * FROM scouting_data", self.conn)
            print(f"✓ Database loaded: {len(self.df)} records found")
            return True
        except sqlite3.Error as e:
            print(f"✗ Database error: {e}")
            return False
        except Exception as e:
            print(f"✗ Error loading database: {e}")
            return False
    
    def find_duplicates(self):
        """Find rows where Match Number and Team Number are identical"""
        if self.df is None:
            print("✗ No data loaded. Call load_database() first.")
            return None
        
        # Group by match_number and team_number to find duplicates
        duplicates = self.df[self.df.duplicated(subset=['match_number', 'team_number'], keep=False)]
        
        if len(duplicates) == 0:
            print("✓ No duplicate entries found!")
            return None
        
        # Sort by match_number and team_number for organized display
        duplicates = duplicates.sort_values(['match_number', 'team_number', 'id'])
        
        print(f"✓ Found {len(duplicates)} conflicting records")
        return duplicates
    
    def display_conflict(self, row1, row2):
        """Display two conflicting records side-by-side"""
        print("\n" + "="*80)
        print(f"CONFLICT: Match {row1['match_number']}, Team {row2['team_number']}")
        print("="*80)
        
        # Get all columns except id
        columns = [col for col in row1.index if col != 'id']
        
        # Display side-by-side comparison
        print(f"{'Field':<30} {'Record 1 (ID: ' + str(row1['id']) + ')':<25} {'Record 2 (ID: ' + str(row2['id']) + ')':<25}")
        print("-"*80)
        
        for col in columns:
            val1 = str(row1[col]) if pd.notna(row1[col]) else ''
            val2 = str(row2[col]) if pd.notna(row2[col]) else ''
            
            # Highlight differences
            marker = " *" if val1 != val2 else ""
            print(f"{col:<30} {val1:<25} {val2:<25}{marker}")
        
        print("="*80)
    
    def get_user_choice(self):
        """Prompt user for resolution choice"""
        while True:
            choice = input("\nKeep (1), Keep (2), or Average (A)? ").strip().upper()
            if choice in ['1', '2', 'A']:
                return choice
            else:
                print("Invalid choice. Please enter 1, 2, or A.")
    
    def average_records(self, row1, row2):
        """Calculate average of numeric fields and merge string fields"""
        merged_record = {}
        
        for col in row1.index:
            if col == 'id':
                # Keep the first ID
                merged_record[col] = row1[col]
            elif col in self.numeric_fields:
                # Average numeric fields
                val1 = row1[col] if pd.notna(row1[col]) else 0
                val2 = row2[col] if pd.notna(row2[col]) else 0
                
                # Handle numeric conversion
                try:
                    val1 = float(val1)
                    val2 = float(val2)
                    merged_record[col] = (val1 + val2) / 2
                except (ValueError, TypeError):
                    merged_record[col] = val1  # Fallback to first value
            else:
                # Merge string fields
                val1 = str(row1[col]) if pd.notna(row1[col]) else ''
                val2 = str(row2[col]) if pd.notna(row2[col]) else ''
                
                if val1 == val2:
                    merged_record[col] = val1
                elif val1 and val2:
                    # Both have values - combine them
                    if col == 'notes':
                        merged_record[col] = f"{val1} | {val2}"
                    elif col == 'scouter_name':
                        merged_record[col] = f"{val1}/{val2}"
                    elif col == 'timestamp' or col == 'scanned_at':
                        # Keep the earlier timestamp
                        merged_record[col] = min(val1, val2)
                    else:
                        # For other string fields, prefer non-empty value
                        merged_record[col] = val1 if val1 else val2
                else:
                    # One is empty - use the non-empty one
                    merged_record[col] = val1 if val1 else val2
        
        return merged_record
    
    def update_database(self, keep_record, delete_ids):
        """Update database with resolved row and delete duplicates"""
        try:
            cursor = self.conn.cursor()
            
            # Get all column names except 'id'
            columns = [col for col in keep_record.keys() if col != 'id']
            
            # Update the kept record
            update_cols = ', '.join([f"{col} = ?" for col in columns])
            update_values = [keep_record[col] for col in columns]
            update_values.append(keep_record['id'])
            
            cursor.execute(
                f"UPDATE scouting_data SET {update_cols} WHERE id = ?",
                update_values
            )
            
            # Delete the duplicate records
            for delete_id in delete_ids:
                cursor.execute("DELETE FROM scouting_data WHERE id = ?", (delete_id,))
            
            self.conn.commit()
            print(f"✓ Database updated: Kept record ID {keep_record['id']}, deleted {len(delete_ids)} duplicate(s)")
            return True
            
        except sqlite3.Error as e:
            print(f"✗ Database error during update: {e}")
            self.conn.rollback()
            return False
    
    def resolve_conflicts(self):
        """Main method to identify and resolve all conflicts"""
        if not self.load_database():
            return False
        
        duplicates = self.find_duplicates()
        
        if duplicates is None:
            # No duplicates found
            return True
        
        # Group duplicates by match_number and team_number
        grouped = duplicates.groupby(['match_number', 'team_number'])
        
        total_groups = len(grouped)
        current_group = 0
        
        for (match_num, team_num), group in grouped:
            current_group += 1
            print(f"\n\nProcessing conflict {current_group} of {total_groups}")
            
            # Get the duplicate records
            records = group.to_dict('records')
            
            # Handle multiple duplicates - process pairs
            while len(records) > 1:
                row1_dict = records[0]
                row2_dict = records[1]
                
                # Convert to Series for easier handling
                row1 = pd.Series(row1_dict)
                row2 = pd.Series(row2_dict)
                
                # Display the conflict
                self.display_conflict(row1, row2)
                
                # Get user choice
                choice = self.get_user_choice()
                
                if choice == '1':
                    # Keep record 1, delete record 2
                    keep_record = row1_dict
                    delete_ids = [row2_dict['id']]
                    records.pop(1)  # Remove second record
                elif choice == '2':
                    # Keep record 2, delete record 1
                    keep_record = row2_dict
                    delete_ids = [row1_dict['id']]
                    records.pop(0)  # Remove first record
                else:  # choice == 'A'
                    # Average the records
                    merged = self.average_records(row1, row2)
                    keep_record = merged
                    delete_ids = [row2_dict['id']]
                    records.pop(1)  # Remove second record
                    records[0] = merged  # Update first with merged
                
                # Update the database
                if not self.update_database(keep_record, delete_ids):
                    print("✗ Failed to update database. Aborting.")
                    return False
        
        print("\n" + "="*80)
        print("✓ All conflicts resolved!")
        print("="*80)
        return True
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


def main():
    """Main entry point"""
    print("\n" + "="*80)
    print("FRC Scouting System - Conflict Resolution Tool")
    print("="*80)
    
    # Check if database file exists
    import os
    if not os.path.exists('scouting_data.db'):
        print("✗ Error: scouting_data.db not found")
        print("  Please ensure the database file exists in the current directory.")
        return 1
    
    try:
        resolver = ConflictResolver()
        success = resolver.resolve_conflicts()
        resolver.close()
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\n✗ Aborted by user")
        return 1
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
