import sqlite3

def create_database():
    try:
        # 1. Connect to SQLite database (creates the file if it doesn't exist)
        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()
        print("Connected to SQLite database 'database.db'")

        # 2. Create Users Table
        # Note: SQLite uses 'INTEGER PRIMARY KEY AUTOINCREMENT' instead of 'INT AUTO_INCREMENT'
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        print("Table 'users' created successfully")

        # 3. Insert Static Admin User
        # SQLite uses 'INSERT OR IGNORE' instead of 'INSERT IGNORE'
        cursor.execute("""
            INSERT OR IGNORE INTO users (username, password) VALUES ('admin', 'admin123')
        """)
        print("Admin user checked/inserted")

        # 4. Create Events Table (Updated with new fields from app.py)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                event_date TEXT NOT NULL,
                event_manager TEXT,
                contact_number TEXT,
                image_file TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Table 'events' created successfully")

        # 5. Create Gallery Table (Replaces 'blogs' to match app.py)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gallery (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_file TEXT NOT NULL,
                caption TEXT,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Table 'gallery' created successfully")

        # 6. Create Materials Table (Updated with Year and Semester)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                subject TEXT NOT NULL,
                target_year TEXT NOT NULL,
                semester INTEGER NOT NULL,
                file_link TEXT NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Table 'materials' created successfully")

        # 7. Create Activity Logs Table (New requirement)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Table 'activity_logs' created successfully")

        # 8. Create Anonymous Feedback Table (Student Voice)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Table 'feedback' created successfully")

        connection.commit()

    except sqlite3.Error as e:
        print(f"Error: {e}")

    finally:
        if connection:
            connection.close()
            print("SQLite connection closed")

if __name__ == "__main__":
    create_database()