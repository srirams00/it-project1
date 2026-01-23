import os
from flask import Flask, render_template, request, redirect, session, url_for
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# 1. LOAD ENVIRONMENT VARIABLES
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'fallback_secret_key')

# 2. CONFIGURE FILE UPLOADS
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 3. DATABASE CONNECTION
def get_db_connection():
    # DIRECT CONNECTION (Bypassing .env issues for reliability)
    conn = mysql.connector.connect(
        host="localhost",
        user="it_admin",
        password="ComplexPassword123!",
        database="it_department_db"
    )
    return conn

# --- HELPER FUNCTION TO SAVE LOGS ---
def log_action(action_message):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO activity_logs (action) VALUES (%s)", (action_message,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Logging Error: {e}")

# --- ROUTE TO VIEW LOGS ---
@app.route('/logs')
def view_logs():
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # Fetch logs, newest first
    cursor.execute("SELECT * FROM activity_logs ORDER BY id DESC")
    logs = cursor.fetchall()
    conn.close()
    
    return render_template('logs.html', logs=logs)

# --- PUBLIC ROUTES ---

@app.route('/')
def home():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get recent events
        cursor.execute("SELECT * FROM events ORDER BY event_date DESC LIMIT 3")
        recent_events = cursor.fetchall()
        
        # Get recent photos from gallery
        cursor.execute("SELECT * FROM gallery ORDER BY upload_date DESC LIMIT 6")
        recent_photos = cursor.fetchall()

        conn.close()
        return render_template('index.html', recent_events=recent_events, recent_photos=recent_photos)
    except Error as e:
        print(f"Error: {e}")
        return render_template('index.html', recent_events=[], recent_photos=[])

@app.route('/events')
def events():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM events ORDER BY event_date DESC")
        events = cursor.fetchall()
        conn.close()
        return render_template('events.html', events=events)
    except Error as e:
        print(f"Error: {e}")
        return render_template('events.html', events=[])

@app.route('/event/<int:event_id>')
def event_detail(event_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM events WHERE id = %s", (event_id,))
        event = cursor.fetchone()
        conn.close()
        if event:
            return render_template('event_detail.html', event=event)
        else:
            return "Event not found", 404
    except Error as e:
        print(f"Error: {e}")
        return "Database error", 500

@app.route('/gallery')
def gallery():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM gallery ORDER BY upload_date DESC")
        photos = cursor.fetchall()
        conn.close()
        return render_template('gallery.html', photos=photos)
    except Error as e:
        print(f"Error: {e}")
        return render_template('gallery.html', photos=[])

@app.route('/materials')
def materials():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # THIS LINE IS CRITICAL: It actually fetches the data
    cursor.execute("SELECT * FROM materials ORDER BY target_year, semester, title")
    items = cursor.fetchall()
    conn.close()

    # Organize data for the tabs
    materials_data = {}
    
    # Ensure all years exist (so tabs appear even if empty)
    for y in ['1st Year', '2nd Year', '3rd Year']:
        materials_data[y] = {}

    for item in items:
        year = item['target_year'] # e.g. "1st Year"
        sem = f"Sem {item['semester']}" # e.g. "Sem 1"
        
        if year not in materials_data:
            materials_data[year] = {}
        if sem not in materials_data[year]:
            materials_data[year][sem] = []
            
        materials_data[year][sem].append(item)
        
    return render_template('materials.html', materials=materials_data)


# --- ADMIN ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                session['admin'] = user['username']
                log_action("Admin Logged In successfully") # LOGGED
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error='Invalid credentials')
        except Error as e:
            print(f"Error: {e}")
            return render_template('login.html', error='Database error')
    
    return render_template('login.html')

# --- UPDATE DASHBOARD ROUTE ---
@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Fetch Events
    cursor.execute("SELECT * FROM events ORDER BY id DESC")
    events = cursor.fetchall()

    # 2. Fetch Gallery Photos
    cursor.execute("SELECT * FROM gallery ORDER BY id DESC")
    photos = cursor.fetchall()

    # 3. Fetch Materials (NEW ADDITION)
    cursor.execute("SELECT * FROM materials ORDER BY id DESC")
    materials = cursor.fetchall()
    
    conn.close()

    return render_template('dashboard.html', events=events, photos=photos, materials=materials)

# --- NEW MATERIAL ROUTES ---

@app.route('/delete_material/<int:id>', methods=['POST'])
def delete_material(id):
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM materials WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    
    log_action(f"Deleted Material ID: {id}") # LOGGED
    return redirect(url_for('dashboard'))

@app.route('/edit_material/<int:id>', methods=['GET', 'POST'])
def edit_material(id):
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # Get data from form
        title = request.form['title']
        subject = request.form['subject']
        target_year = request.form['target_year']
        semester = request.form['semester']
        file_link = request.form['file_link']
        
        # Update Database
        cursor.execute("""
            UPDATE materials 
            SET title=%s, subject=%s, target_year=%s, semester=%s, file_link=%s 
            WHERE id=%s
        """, (title, subject, target_year, semester, file_link, id))
        
        conn.commit()
        conn.close()
        
        log_action(f"Edited Material ID: {id} - {title}") # LOGGED
        return redirect(url_for('dashboard'))
    
    # GET Request: Show the form with current data
    cursor.execute("SELECT * FROM materials WHERE id = %s", (id,))
    material = cursor.fetchone()
    conn.close()
    
    return render_template('edit_material.html', material=material)

# --- ADD EVENT (Updated with Image & Contact Info) ---
@app.route('/add_event', methods=['POST'])
def add_event():
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    title = request.form['title']
    description = request.form['description']
    event_date = request.form['event_date']
    
    # New Fields
    event_manager = request.form.get('event_manager', 'Student Coordinator')
    contact_number = request.form.get('contact_number', '')

    # Handle Image Upload
    image_filename = None
    if 'event_image' in request.files:
        file = request.files['event_image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_filename = filename
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO events (title, description, event_date, event_manager, contact_number, image_file) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (title, description, event_date, event_manager, contact_number, image_filename))
        conn.commit()
        conn.close()
        
        log_action(f"Created new Event: {title}") # LOGGED
    except Error as e:
        print(f"Error: {e}")
    
    return redirect(url_for('dashboard'))

# --- EDIT EVENT (New Route) ---
@app.route('/edit_event/<int:event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    if 'admin' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # Get updated data
        title = request.form['title']
        date = request.form['event_date']
        desc = request.form['description']
        manager = request.form['event_manager']
        contact = request.form['contact_number']

        # Handle Image Update (Only if a new one is uploaded)
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Delete old image if exists
                cursor.execute("SELECT image_file FROM events WHERE id = %s", (event_id,))
                old_event = cursor.fetchone()
                if old_event and old_event['image_file']:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], old_event['image_file'])
                    if os.path.exists(old_path):
                        os.remove(old_path)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                # Update with new image
                cursor.execute("""
                    UPDATE events SET title=%s, event_date=%s, description=%s, event_manager=%s, contact_number=%s, image_file=%s
                    WHERE id=%s
                """, (title, date, desc, manager, contact, filename, event_id))
            else:
                # Update without changing image
                cursor.execute("""
                    UPDATE events SET title=%s, event_date=%s, description=%s, event_manager=%s, contact_number=%s
                    WHERE id=%s
                """, (title, date, desc, manager, contact, event_id))
        else:
             # No file input found at all
            cursor.execute("""
                UPDATE events SET title=%s, event_date=%s, description=%s, event_manager=%s, contact_number=%s
                WHERE id=%s
            """, (title, date, desc, manager, contact, event_id))

        conn.commit()
        conn.close()
        
        log_action(f"Edited Event ID: {event_id} - {title}") # LOGGED
        return redirect(url_for('dashboard'))

    # GET request: Show the form pre-filled
    cursor.execute("SELECT * FROM events WHERE id = %s", (event_id,))
    event = cursor.fetchone()
    conn.close()
    return render_template('edit_event.html', event=event)

# --- DELETE EVENT (New Route) ---
@app.route('/delete_event/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    if 'admin' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get image filename first
        cursor.execute("SELECT image_file FROM events WHERE id = %s", (event_id,))
        event = cursor.fetchone()

        if event and event['image_file']:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], event['image_file'])
            if os.path.exists(image_path):
                os.remove(image_path)

        # Delete from DB
        cursor.execute("DELETE FROM events WHERE id = %s", (event_id,))
        conn.commit()
        conn.close()
        
        log_action(f"Deleted Event ID: {event_id}") # LOGGED
    except Error as e:
        print(f"Error: {e}")

    return redirect(url_for('dashboard'))


@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    if 'admin' not in session:
        return redirect(url_for('login'))

    caption = request.form.get('caption', '')

    # Handle Image Upload
    image_filename = None
    if 'image_file' in request.files:
        file = request.files['image_file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_filename = filename

    if image_filename:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO gallery (image_file, caption) VALUES (%s, %s)",
                           (image_filename, caption))
            conn.commit()
            conn.close()
            
            log_action(f"Uploaded Photo to Gallery. Caption: {caption}") # LOGGED
        except Error as e:
            print(f"Error: {e}")

    return redirect(url_for('dashboard'))

# --- PHOTO MANAGEMENT ROUTES ---

@app.route('/delete_photo/<int:photo_id>', methods=['POST'])
def delete_photo(photo_id):
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Get filename to delete file from folder
    cursor.execute("SELECT image_file FROM gallery WHERE id = %s", (photo_id,))
    photo = cursor.fetchone()
    
    if photo:
        try:
            # Try to delete the file from your computer
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], photo['image_file'])
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file: {e}")

        # 2. Delete from Database
        cursor.execute("DELETE FROM gallery WHERE id = %s", (photo_id,))
        conn.commit()
        
        log_action(f"Deleted Gallery Photo ID: {photo_id}") # LOGGED
    
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/edit_photo/<int:photo_id>', methods=['GET', 'POST'])
def edit_photo(photo_id):
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # UPDATE CAPTION
        new_caption = request.form['caption']
        cursor.execute("UPDATE gallery SET caption = %s WHERE id = %s", (new_caption, photo_id))
        conn.commit()
        conn.close()
        
        log_action(f"Edited Photo Caption ID: {photo_id}") # LOGGED
        return redirect(url_for('dashboard'))
    
    # GET: Show the form
    cursor.execute("SELECT * FROM gallery WHERE id = %s", (photo_id,))
    photo = cursor.fetchone()
    conn.close()
    
    return render_template('edit_photo.html', photo=photo)

# --- ADD MATERIAL ---
@app.route('/add_material', methods=['POST'])
def add_material():
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    # Get data from the form
    title = request.form['title']
    subject = request.form['subject']
    target_year = request.form['target_year']
    semester = request.form['semester']
    file_link = request.form['file_link']
    
    # Save to Database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO materials (title, subject, target_year, semester, file_link) VALUES (%s, %s, %s, %s, %s)',
                   (title, subject, target_year, semester, file_link))
    conn.commit()
    conn.close()
    
    log_action(f"Uploaded Material: {title} ({target_year})") # LOGGED
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)