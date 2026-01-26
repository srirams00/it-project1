import sqlite3
import os

def fix_database():
    """
    Fix database by adding the missing feedback table.
    This script is safe to run multiple times - it won't affect existing tables.
    """
    try:
        # Get the database path
        db_path = os.path.join(os.path.dirname(__file__), 'database.db')
        
        print(f"Connecting to database: {db_path}")
        
        # Connect to the database
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()
        
        print("✓ Connected successfully")
        
        # Create the feedback table if it doesn't exist
        print("Creating 'feedback' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Commit the changes
        connection.commit()
        print("✓ Table 'feedback' created successfully")
        
        # Verify the table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='feedback'")
        result = cursor.fetchone()
        
        if result:
            print("✓ Verification passed: 'feedback' table exists")
            
            # Show table schema
            cursor.execute("PRAGMA table_info(feedback)")
            columns = cursor.fetchall()
            print("\nTable schema:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
        else:
            print("✗ Warning: Table verification failed")
        
        # Close the connection
        connection.close()
        print("\n✅ Database fix completed successfully!")
        print("You can now restart your Flask app and access the dashboard.")
        
    except sqlite3.Error as e:
        print(f"\n❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("  Database Fix Script - Adding 'feedback' Table")
    print("=" * 60)
    print()
    
    success = fix_database()
    
    if success:
        print("\n" + "=" * 60)
        print("  ✓ All done! Your database is ready.")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("  ✗ Fix failed. Please check the error above.")
        print("=" * 60)
