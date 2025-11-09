from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from datetime import datetime, time
from flask_mysqldb import MySQL 
import MySQLdb.cursors
import json
import os
from dotenv import load_dotenv

# --- 1. INITIALIZE APP AND CONFIG ---
app = Flask(__name__)

# Load environment variables (like passwords and user names)
load_dotenv() 

# Set a SECRET_KEY for session management (CRITICAL for security)
app.secret_key = os.getenv('SECRET_KEY', 'a_default_secret_key_change_me')

# MySQL Configuration (***USING 'insomnia_cure' to match your SQL***)
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
# IMPORTANT: Replace 'your_mysql_password' with your ACTUAL MySQL password if not using a .env file
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '123456789') 
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'insomnia_cure') # Fixed to 'insomnia_cure'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor' # Use DictCursor by default

# Initialize MySQL
mysql = MySQL(app)

# --- 2. HELPER FUNCTIONS ---

# Function to calculate sleep duration in hours (handles sleep across midnight)
def calculate_sleep_duration(bedtime_str, wakeup_time_str):
    try:
        # Parse time strings into datetime.time objects
        bedtime = datetime.strptime(bedtime_str, '%H:%M').time()
        wakeup_time = datetime.strptime(wakeup_time_str, '%H:%M').time()
        
        # Combine with a dummy date (e.g., today) to calculate the difference
        dummy_date = datetime.now().date()
        
        dt_bedtime = datetime.combine(dummy_date, bedtime)
        dt_wakeup = datetime.combine(dummy_date, wakeup_time)
        
        # If wakeup is earlier than bedtime, assume sleep crossed midnight (add 24 hours)
        if dt_wakeup < dt_bedtime:
            dt_wakeup = datetime.combine(dummy_date.replace(day=dummy_date.day + 1), wakeup_time)
            
        duration = dt_wakeup - dt_bedtime
        
        # Convert total seconds to hours
        return duration.total_seconds() / 3600
        
    except ValueError as e:
        print(f"Time format error: {e}")
        return 0.0 # Return 0 if time format is incorrect

# --- 3. FLASK ROUTES ---

# Default route for the sleep tracker (assuming no user authentication is fully implemented yet)
@app.route('/', methods=['GET', 'POST'])
def index():
    # Placeholder: Assuming a single-user system for simplicity now, 
    # as the sleep_log table does not reference user_id in the original SQL.
    
    # Handle the form submission (POST request)
    if request.method == 'POST':
        try:
            # 1. Get form data
            sleep_date = request.form['sleep_date']
            bedtime = request.form['bedtime']
            wakeup_time = request.form['wakeup_time']
            
            # Use .get() with a default to avoid conversion errors if field is missing
            sleep_quality = int(request.form.get('sleep_quality', 5))
            stress_level = int(request.form.get('stress_level', 5))
            notes = request.form.get('notes', '')
            caffeine = 1 if 'caffeine_intake' in request.form else 0
            exercise = 1 if 'exercise' in request.form else 0
            
            # 2. Calculate duration
            sleep_duration = calculate_sleep_duration(bedtime, wakeup_time)

            # 3. Save to database (Assuming the original table name was `sleep_log` not `sleep_logs`)
            cursor = mysql.connection.cursor()
            cursor.execute("""
                INSERT INTO sleep_log (sleep_date, bedtime, wakeup_time, sleep_duration, sleep_quality, stress_level, caffeine_intake, exercise, notes) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (sleep_date, bedtime, wakeup_time, sleep_duration, sleep_quality, stress_level, caffeine, exercise, notes))
            mysql.connection.commit()
            cursor.close()
            
            return redirect(url_for('index'))
            
        except Exception as e:
            # Print the detailed error to the terminal
            print(f"FATAL DATABASE WRITE ERROR: {e}") 
            # This is often the primary reason for 'Internal Server Error'
            return render_template('500.html', error=str(e)), 500


    # Handle the page display (GET request)
    else:
        try:
            # 1. Fetch all sleep logs from the database
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            # Change 'sleep_log' to 'sleep_logs'
            cursor.execute(""" INSERT INTO sleep_logs (...) VALUES (...) """)
            # Order by date descending to show newest first
            cursor.execute("SELECT * FROM sleep_log ORDER BY sleep_date DESC, wakeup_time DESC")
            sleep_logs = cursor.fetchall()
            cursor.close()
            
            # Prepare today's date for the form default value
            today = datetime.now().strftime('%Y-%m-%d')
            
            # 2. Render the template
            return render_template('tracker.html', 
                                    sleep_logs=sleep_logs, 
                                    today=today)
        except Exception as e:
            print(f"FATAL DATABASE READ ERROR: {e}")
            return render_template('500.html', error="Could not connect to database or tables are missing."), 500


# JSON Data Endpoint for Chart.js (Required for the statistics chart)
@app.route('/sleep-data')
def sleep_data():
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        # Get the last 10 logs for a better chart view
        cursor.execute("SELECT sleep_date, sleep_duration, sleep_quality FROM sleep_logs ORDER BY sleep_date DESC, wakeup_time DESC LIMIT 10")
        logs = cursor.fetchall()
        cursor.close()
        
        # Reverse the list so the chart displays oldest to newest (left to right)
        logs.reverse() 

        # Extract data for the chart
        dates = [log['sleep_date'].strftime('%b %d') for log in logs]
        durations = [round(log['sleep_duration'], 1) for log in logs]
        qualities = [log['sleep_quality'] for log in logs] # Also include quality

        return jsonify({
            'dates': dates,
            'durations': durations,
            'qualities': qualities
        })
    except Exception as e:
        print(f"Error fetching chart data: {e}")
        return jsonify({'error': 'Could not load chart data'}), 500


# Route to handle editing an existing log
@app.route('/edit_log/<int:log_id>', methods=['GET', 'POST'])
def edit_log(log_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # GET: Display the edit form
    if request.method == 'GET':
        cursor.execute("SELECT * FROM sleep_log WHERE id = %s", (log_id,))
        log = cursor.fetchone()
        cursor.close()
        
        if log:
            return render_template('edit_tracker.html', log=log)
        else:
            return "Log not found.", 404
            
    # POST: Handle form submission to update the log
    if request.method == 'POST':
        try:
            sleep_date = request.form['sleep_date']
            bedtime = request.form['bedtime']
            wakeup_time = request.form['wakeup_time']
            sleep_quality = int(request.form.get('sleep_quality', 5))
            stress_level = int(request.form.get('stress_level', 5))
            notes = request.form.get('notes', '')
            caffeine = 1 if 'caffeine_intake' in request.form else 0
            exercise = 1 if 'exercise' in request.form else 0
            
            sleep_duration = calculate_sleep_duration(bedtime, wakeup_time)
            
            cursor.execute("""
                UPDATE sleep_log 
                SET sleep_date = %s, bedtime = %s, wakeup_time = %s, sleep_duration = %s, 
                    sleep_quality = %s, stress_level = %s, caffeine_intake = %s, exercise = %s, notes = %s
                WHERE id = %s
            """, (sleep_date, bedtime, wakeup_time, sleep_duration, 
                  sleep_quality, stress_level, caffeine, exercise, notes, log_id))
            mysql.connection.commit()
            cursor.close()
            
            return redirect(url_for('index'))
            
        except Exception as e:
            print(f"Error updating log: {e}")
            return "An error occurred while updating the sleep log.", 500


# Route to handle deleting a log
@app.route('/delete_log/<int:log_id>', methods=['POST'])
def delete_log(log_id):
    try:
        cursor = mysql.connection.cursor()
        # Use a DELETE query to remove the record
        cursor.execute("DELETE FROM sleep_log WHERE id = %s", (log_id,))
        mysql.connection.commit()
        cursor.close()
        
        # Redirect back to the main tracker page after deletion
        return redirect(url_for('index'))
        
    except Exception as e:
        print(f"Error deleting log: {e}")
        return "An error occurred while deleting the sleep log.", 500


# Basic error pages (Good practice to include these)
@app.errorhandler(404)
def page_not_found(e):
    # Log the error (optional)
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    # Log the error (optional)
    return render_template('500.html'), 500


# --- 4. RUN THE APP ---
if __name__ == '__main__':
    # When using a non-default host/port
    # app.run(debug=True, host='0.0.0.0', port=5000) 
    app.run(debug=True)