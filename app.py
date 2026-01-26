from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'super_secret_key_123'

# --- 1. SET ABSOLUTE PATHS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_registration_table():
    """Create event_registrations table if it doesn't exist"""
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS event_registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            dept_no TEXT NOT NULL,
            class_section TEXT NOT NULL,
            phone TEXT,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events (id)
        )
    ''')
    conn.commit()
    conn.close()

# Initialize registration table on startup
init_registration_table()

def log_activity(action):
    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO activity_logs (action) VALUES (?)', (action,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Log Error: {e}")

# --- ROUTES ---

@app.route('/')
def home():
    try:
        conn = get_db_connection()
        recent_events = conn.execute('SELECT * FROM events ORDER BY event_date DESC LIMIT 3').fetchall()
        recent_photos = conn.execute('SELECT * FROM gallery ORDER BY upload_date DESC LIMIT 6').fetchall()
        conn.close()
        return render_template('index.html', recent_events=recent_events, recent_photos=recent_photos)
    except Exception as e:
        print(f"Database Error: {e}")
        return render_template('index.html', recent_events=[], recent_photos=[])

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and user['password'] == password:
            session['admin'] = True
            log_activity(f"User logged in: {username}")
            return redirect(url_for('dashboard'))
        else:
            log_activity(f"Failed login attempt for: {username}")
            error = 'invalid'  # Pass error type to template
            
    return render_template('login.html', error=error)

# --- ONLY ONE LOGOUT FUNCTION HERE ---
@app.route('/logout')
def logout():
    if session.get('admin'):
        log_activity("User logged out")
    session.pop('admin', None)
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if not session.get('admin'): return redirect(url_for('login'))
    conn = get_db_connection()
    events = conn.execute('SELECT * FROM events ORDER BY event_date DESC').fetchall()
    photos = conn.execute('SELECT * FROM gallery ORDER BY upload_date DESC').fetchall()
    materials = conn.execute('SELECT * FROM materials ORDER BY upload_date DESC').fetchall()
    
    # Get registration counts for each event
    registrations = {}
    for event in events:
        count = conn.execute('SELECT COUNT(*) FROM event_registrations WHERE event_id = ?', (event['id'],)).fetchone()[0]
        registrations[event['id']] = count
    
    # Get anonymous feedback messages (newest first)
    feedback_messages = conn.execute('SELECT * FROM feedback ORDER BY timestamp DESC').fetchall()
    
    conn.close()
    return render_template('dashboard.html', events=events, photos=photos, materials=materials, registrations=registrations, feedback_messages=feedback_messages)

# --- ANONYMOUS FEEDBACK (Student Voice) ---
@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    message = request.form.get('message', '').strip()
    
    if not message:
        # Check if it's an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/x-www-form-urlencoded':
            return jsonify({'success': False, 'message': 'Please enter a message'}), 400
        flash('Please enter a message', 'error')
        return redirect(url_for('home'))
    
    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO feedback (message) VALUES (?)', (message,))
        conn.commit()
        conn.close()
        
        log_activity("New anonymous feedback submitted")
        
        # Return JSON for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return jsonify({'success': True, 'message': 'Thank you for your feedback!'}), 200
        
        # Regular redirect for non-AJAX requests
        flash('Thank you for your feedback! Your voice matters.', 'success')
        return redirect(url_for('home'))
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'An error occurred'}), 500
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('home'))

@app.route('/clear_inbox', methods=['POST'])
def clear_inbox():
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    try:
        conn = get_db_connection()
        count = conn.execute('SELECT COUNT(*) FROM feedback').fetchone()[0]
        conn.execute('DELETE FROM feedback')
        conn.commit()
        conn.close()
        
        log_activity(f"Cleared {count} feedback message(s) from inbox")
        flash(f'Successfully deleted {count} feedback message(s).', 'success')
    except Exception as e:
        flash('An error occurred while clearing the inbox.', 'error')
    
    return redirect(url_for('dashboard'))

# --- EVENTS ---
@app.route('/events')
def events():
    conn = get_db_connection()
    events = conn.execute('SELECT * FROM events ORDER BY event_date DESC').fetchall()
    conn.close()
    return render_template('events.html', events=events)

# --- EVENT REGISTRATION ---
@app.route('/register/<int:event_id>', methods=['GET', 'POST'])
def register_event(event_id):
    conn = get_db_connection()
    event = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    
    if not event:
        conn.close()
        flash('Event not found', 'error')
        return redirect(url_for('events'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        dept_no = request.form.get('dept_no', '').strip()
        class_section = request.form.get('class_section', '').strip()
        phone = request.form.get('phone', '').strip()
        
        if not name or not dept_no or not class_section:
            flash('Name, Dept No. and Class Section are required', 'error')
            return render_template('event_registration.html', event=event)
        
        # Check if already registered (by name and dept_no)
        existing = conn.execute(
            'SELECT * FROM event_registrations WHERE event_id = ? AND name = ? AND dept_no = ?',
            (event_id, name, dept_no)
        ).fetchone()
        
        if existing:
            conn.close()
            flash('You have already registered for this event!', 'warning')
            return render_template('event_registration.html', event=event, already_registered=True)
        
        # Insert registration
        conn.execute(
            'INSERT INTO event_registrations (event_id, name, dept_no, class_section, phone) VALUES (?, ?, ?, ?, ?)',
            (event_id, name, dept_no, class_section, phone)
        )
        conn.commit()
        conn.close()
        
        log_activity(f"New registration for event '{event['title']}' by {name}")
        flash('Registration successful! See you at the event.', 'success')
        return redirect(url_for('registration_success', event_id=event_id))
    
    conn.close()
    return render_template('event_registration.html', event=event)

@app.route('/registration-success/<int:event_id>')
def registration_success(event_id):
    conn = get_db_connection()
    event = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    conn.close()
    return render_template('registration_success.html', event=event)

@app.route('/event-registrations/<int:event_id>')
def view_event_registrations(event_id):
    if not session.get('admin'): return redirect(url_for('login'))
    conn = get_db_connection()
    event = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    registrations = conn.execute(
        'SELECT * FROM event_registrations WHERE event_id = ? ORDER BY registration_date DESC',
        (event_id,)
    ).fetchall()
    conn.close()
    return render_template('event_registrations.html', event=event, registrations=registrations)

@app.route('/add_event', methods=['POST'])
def add_event():
    if not session.get('admin'): return redirect(url_for('login'))
    image = request.files.get('image_file')
    filename = ""
    if image and image.filename != '':
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    conn = get_db_connection()
    conn.execute('INSERT INTO events (title, event_date, event_manager, contact_number, description, image_file) VALUES (?, ?, ?, ?, ?, ?)',
                 (request.form['title'], request.form['event_date'], request.form['event_manager'], 
                  request.form['contact_number'], request.form['description'], filename))
    conn.commit()
    conn.close()
    log_activity(f"Added event: {request.form['title']}")
    return redirect(url_for('dashboard'))

@app.route('/edit_event/<int:event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    if not session.get('admin'): return redirect(url_for('login'))
    conn = get_db_connection()
    
    if request.method == 'POST':
        conn.execute('UPDATE events SET title=?, event_date=?, event_manager=?, contact_number=?, description=? WHERE id=?',
                     (request.form['title'], request.form['event_date'], request.form['event_manager'], 
                      request.form['contact_number'], request.form['description'], event_id))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
        
    event = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    conn.close()
    return render_template('edit_event.html', event=event)

@app.route('/delete_event/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    if not session.get('admin'): return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute('DELETE FROM event_registrations WHERE event_id = ?', (event_id,))
    conn.execute('DELETE FROM events WHERE id = ?', (event_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

# --- GALLERY ---
@app.route('/gallery')
def gallery():
    conn = get_db_connection()
    photos = conn.execute('SELECT * FROM gallery ORDER BY upload_date DESC').fetchall()
    conn.close()
    return render_template('gallery.html', photos=photos)

@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    if not session.get('admin'): return redirect(url_for('login'))
    image = request.files.get('image_file')
    if image and image.filename != '':
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        conn = get_db_connection()
        conn.execute('INSERT INTO gallery (image_file, caption) VALUES (?, ?)', (filename, request.form['caption']))
        conn.commit()
        conn.close()
    return redirect(url_for('dashboard'))

@app.route('/edit_photo/<int:photo_id>', methods=['GET', 'POST'])
def edit_photo(photo_id):
    if not session.get('admin'): return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        conn.execute('UPDATE gallery SET caption=? WHERE id=?', (request.form['caption'], photo_id))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    photo = conn.execute('SELECT * FROM gallery WHERE id = ?', (photo_id,)).fetchone()
    conn.close()
    return render_template('edit_photo.html', photo=photo)

@app.route('/delete_photo/<int:photo_id>', methods=['POST'])
def delete_photo(photo_id):
    if not session.get('admin'): return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute('DELETE FROM gallery WHERE id = ?', (photo_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

# --- MATERIALS ---
@app.route('/materials')
def materials():
    conn = get_db_connection()
    materials = conn.execute('SELECT * FROM materials ORDER BY upload_date DESC').fetchall()
    conn.close()
    return render_template('materials.html', materials=materials)

@app.route('/add_material', methods=['POST'])
def add_material():
    if not session.get('admin'): return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute('INSERT INTO materials (title, subject, target_year, semester, file_link) VALUES (?, ?, ?, ?, ?)',
                 (request.form['title'], request.form['subject'], request.form['target_year'], 
                  request.form['semester'], request.form['file_link']))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/edit_material/<int:id>', methods=['GET', 'POST'])
def edit_material(id):
    if not session.get('admin'): return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        conn.execute('UPDATE materials SET title=?, subject=?, target_year=?, semester=?, file_link=? WHERE id=?',
                     (request.form['title'], request.form['subject'], request.form['target_year'], 
                      request.form['semester'], request.form['file_link'], id))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    material = conn.execute('SELECT * FROM materials WHERE id = ?', (id,)).fetchone()
    conn.close()
    return render_template('edit_material.html', material=material)

@app.route('/delete_material/<int:id>', methods=['POST'])
def delete_material(id):
    if not session.get('admin'): return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute('DELETE FROM materials WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

# --- LOGS ---
@app.route('/logs')
def view_logs():
    if not session.get('admin'): return redirect(url_for('login'))
    conn = get_db_connection()
    try:
        logs = conn.execute('SELECT * FROM activity_logs ORDER BY timestamp DESC').fetchall()
    except:
        logs = []
    conn.close()
    return render_template('logs.html', logs=logs)

if __name__ == '__main__':
    app.run(debug=True)