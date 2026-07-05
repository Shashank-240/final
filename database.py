import sqlite3
from datetime import datetime, date, timedelta
import pandas as pd
import hashlib

DB_NAME = "selfsync.db"

def hash_password(password):
    """Returns a SHA-256 hash of the given password."""
    return hashlib.sha256(password.encode()).hexdigest()

# ==========================================
# 1. DATABASE CONNECTION & SCHEMA
# ==========================================
def get_connection():
    """Establishes a connection and enforces WAL mode for concurrency."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    """Creates the tables if they do not exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            onboarding_completed BOOLEAN DEFAULT 0,
            discipline_score INTEGER DEFAULT 0,
            current_streak INTEGER DEFAULT 0,
            target_sleep REAL DEFAULT 8.0,
            target_screen_time REAL DEFAULT 4.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Safe migration: add password_hash if it doesn't exist
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    except sqlite3.OperationalError:
        pass

    # Habits Table (Tracks both Good and Bad habits to monitor)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            habit_name TEXT NOT NULL,
            habit_type TEXT CHECK(habit_type IN ('good', 'bad')) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Daily Logs Table (The core of the Daily Activity Tracker)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            log_date DATE NOT NULL,
            sleep_hours REAL DEFAULT 0.0,
            screen_time_hours REAL DEFAULT 0.0,
            mood_score INTEGER CHECK(mood_score >= 1 AND mood_score <= 10),
            productivity_score INTEGER CHECK(productivity_score >= 1 AND productivity_score <= 10),
            notes TEXT,
            discipline_score INTEGER DEFAULT 0,
            UNIQUE(user_id, log_date),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Habit Tracking Table (Pivot table for daily habit completion)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_habits (
            log_date DATE NOT NULL,
            user_id INTEGER,
            habit_id INTEGER,
            completed BOOLEAN DEFAULT 0,
            PRIMARY KEY (log_date, user_id, habit_id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (habit_id) REFERENCES habits (id)
        )
    ''')

    conn.commit()
    conn.close()

# ==========================================
# 2. USER CRUD & ONBOARDING
# ==========================================
def get_user_by_username(username):
    """Retrieves user row by username or returns None."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username.strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id):
    """Retrieves user row by user_id or returns None."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_user(username, password):
    """Creates a new user and returns the new user_id."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        hashed_pw = hash_password(password)
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username.strip(), hashed_pw))
        user_id = cursor.lastrowid
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def verify_user(username, password):
    """Verifies a user's password and returns the user dict if successful."""
    user = get_user_by_username(username)
    if user:
        # Legacy user migration: If they don't have a password set yet, set it to what they just typed
        if 'password_hash' not in user.keys() or not user['password_hash']:
            hashed_pw = hash_password(password)
            conn = get_connection()
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed_pw, user['id']))
            conn.commit()
            conn.close()
            return user
            
        if user['password_hash'] == hash_password(password):
            return user
    return None

def update_user_targets(user_id, target_sleep, target_screen_time):
    """Updates user sleep and screen time goals."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET target_sleep = ?, target_screen_time = ? WHERE id = ?",
        (target_sleep, target_screen_time, user_id)
    )
    conn.commit()
    conn.close()

def complete_onboarding(user_id):
    """Marks user onboarding as completed."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET onboarding_completed = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

# ==========================================
# 3. HABIT MANAGEMENT
# ==========================================
def add_habit(user_id, habit_name, habit_type):
    """Adds a new habit to track for the user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO habits (user_id, habit_name, habit_type) VALUES (?, ?, ?)",
        (user_id, habit_name.strip(), habit_type)
    )
    conn.commit()
    conn.close()

def get_user_habits(user_id):
    """Returns a list of all habits for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM habits WHERE user_id = ? ORDER BY habit_type DESC, habit_name ASC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_habit(user_id, habit_id):
    """Deletes a habit and its tracking history for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM daily_habits WHERE user_id = ? AND habit_id = ?", (user_id, habit_id))
    cursor.execute("DELETE FROM habits WHERE user_id = ? AND id = ?", (user_id, habit_id))
    conn.commit()
    conn.close()

def setup_default_habits(user_id):
    """Sets up a core set of standard good and bad habits for a new user."""
    defaults = [
        ("Exercise / Workout", "good"),
        ("Read a Book / Study", "good"),
        ("Meditation / Mindfulness", "good"),
        ("Drink 3L Water", "good"),
        ("Learn a New Skill / Code", "good"),
        ("Journaling / Reflection", "good"),
        ("Cold Shower / Ice Bath", "good"),
        ("Stretch / Yoga", "good"),
        ("Doomscrolling on Social Media", "bad"),
        ("Junk Food / Sugar Intake", "bad"),
        ("Procrastination / Delays", "bad"),
        ("Binge-watching TV/YouTube", "bad"),
        ("Sleeping < 6 Hours", "bad"),
        ("Complaining / Victim Mentality", "bad"),
        ("Hitting the Snooze Button", "bad")
    ]
    conn = get_connection()
    cursor = conn.cursor()
    # Check if user already has habits to avoid duplicates
    cursor.execute("SELECT COUNT(*) FROM habits WHERE user_id = ?", (user_id,))
    if cursor.fetchone()[0] == 0:
        for name, htype in defaults:
            cursor.execute("INSERT INTO habits (user_id, habit_name, habit_type) VALUES (?, ?, ?)", (user_id, name, htype))
        conn.commit()
    conn.close()

# ==========================================
# 4. DAILY LOGS & HABIT TRACKING (UPSERT)
# ==========================================
def upsert_daily_log(user_id, log_date, sleep, screen_time, mood, productivity, notes=""):
    """
    Inserts a daily log or updates it if it exists.
    Also calculates the discipline score and updates the user's overall score/streak.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if a log already exists to keep its discipline_score initially or we'll recalculate
    query = '''
        INSERT INTO daily_logs (user_id, log_date, sleep_hours, screen_time_hours, mood_score, productivity_score, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, log_date) DO UPDATE SET
            sleep_hours=excluded.sleep_hours,
            screen_time_hours=excluded.screen_time_hours,
            mood_score=excluded.mood_score,
            productivity_score=excluded.productivity_score,
            notes=excluded.notes
    '''
    cursor.execute(query, (user_id, log_date, sleep, screen_time, mood, productivity, notes))
    conn.commit()
    conn.close()

    # Recalculate discipline score for this day, update overall user scores
    recalculate_discipline_and_streak(user_id, log_date)

def get_daily_log(user_id, log_date):
    """Retrieves a single day's log if it exists."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM daily_logs WHERE user_id = ? AND log_date = ?", (user_id, log_date))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def upsert_daily_habit(log_date, user_id, habit_id, completed):
    """Logs the completion state of a specific habit for a given day."""
    conn = get_connection()
    cursor = conn.cursor()
    query = '''
        INSERT INTO daily_habits (log_date, user_id, habit_id, completed)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(log_date, user_id, habit_id) DO UPDATE SET
            completed=excluded.completed
    '''
    cursor.execute(query, (log_date, user_id, habit_id, int(completed)))
    conn.commit()
    conn.close()

    # Recalculate discipline score for this day since habit completion changed
    recalculate_discipline_and_streak(user_id, log_date)

def get_daily_habits_status(user_id, log_date):
    """
    Returns all habits with their completed status for a given day.
    If no log exists yet, completed defaults to False.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Outer join habits with daily_habits for the specific date
    query = '''
        SELECT h.id as habit_id, h.habit_name, h.habit_type, COALESCE(dh.completed, 0) as completed
        FROM habits h
        LEFT JOIN daily_habits dh ON h.id = dh.habit_id AND dh.log_date = ?
        WHERE h.user_id = ?
        ORDER BY h.habit_type DESC, h.habit_name ASC
    '''
    cursor.execute(query, (log_date, user_id))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ==========================================
# 5. DISCIPLINE SCORE & STREAK CALCULATIONS
# ==========================================
def recalculate_discipline_and_streak(user_id, log_date):
    """
    Computes daily score, saves it, updates rolling average and user streak.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Fetch user targets
    cursor.execute("SELECT target_sleep, target_screen_time FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return
    target_sleep = user['target_sleep']
    target_screen_time = user['target_screen_time']

    # 2. Fetch daily log
    cursor.execute("SELECT sleep_hours, screen_time_hours FROM daily_logs WHERE user_id = ? AND log_date = ?", (user_id, log_date))
    log = cursor.fetchone()
    
    # If no log exists yet, we can't calculate score
    if not log:
        conn.close()
        return

    sleep_hours = log['sleep_hours']
    screen_time_hours = log['screen_time_hours']

    # Calculate components
    # A. Sleep Score (Max 20)
    sleep_diff = abs(sleep_hours - target_sleep)
    if sleep_diff <= 1.0:
        sleep_score = 20
    elif sleep_diff <= 2.0:
        sleep_score = 10
    else:
        sleep_score = 0

    # B. Screen Time Score (Max 20)
    if screen_time_hours <= target_screen_time:
        screen_score = 20
    elif screen_time_hours <= target_screen_time + 2.0:
        screen_score = 10
    else:
        screen_score = 0

    # C. Habits Scores (Max 60 total, 30 for Good, 30 for Bad)
    # Fetch all habits and their completed status for today
    cursor.execute('''
        SELECT h.habit_type, COALESCE(dh.completed, 0) as completed
        FROM habits h
        LEFT JOIN daily_habits dh ON h.id = dh.habit_id AND dh.log_date = ?
        WHERE h.user_id = ?
    ''', (log_date, user_id))
    habit_records = cursor.fetchall()

    good_habits = [r for r in habit_records if r['habit_type'] == 'good']
    bad_habits = [r for r in habit_records if r['habit_type'] == 'bad']

    # Good habits: percentage completed * 30
    if not good_habits:
        good_score = 30
    else:
        completed_good = sum(1 for h in good_habits if h['completed'])
        good_score = int((completed_good / len(good_habits)) * 30)

    # Bad habits: percentage NOT completed (i.e. avoided) * 30
    if not bad_habits:
        bad_score = 30
    else:
        avoided_bad = sum(1 for h in bad_habits if not h['completed'])
        bad_score = int((avoided_bad / len(bad_habits)) * 30)

    # Total Score
    total_discipline_score = sleep_score + screen_score + good_score + bad_score
    total_discipline_score = max(0, min(100, total_discipline_score))

    # Update daily log score
    cursor.execute(
        "UPDATE daily_logs SET discipline_score = ? WHERE user_id = ? AND log_date = ?",
        (total_discipline_score, user_id, log_date)
    )

    # 3. Calculate 7-day rolling average for overall user score
    cursor.execute('''
        SELECT discipline_score FROM daily_logs 
        WHERE user_id = ? 
        ORDER BY log_date DESC 
        LIMIT 7
    ''', (user_id,))
    recent_logs = cursor.fetchall()
    if recent_logs:
        rolling_avg = int(sum(r['discipline_score'] for r in recent_logs) / len(recent_logs))
    else:
        rolling_avg = 0

    # 4. Calculate current streak
    # Get all distinct log dates for the user
    cursor.execute("SELECT DISTINCT log_date FROM daily_logs WHERE user_id = ? ORDER BY log_date DESC", (user_id,))
    log_dates_raw = cursor.fetchall()
    
    log_dates = set()
    for r in log_dates_raw:
        date_str = r['log_date']
        if date_str:
            try:
                date_part = str(date_str).split()[0]
                log_dates.add(datetime.strptime(date_part, "%Y-%m-%d").date())
            except Exception:
                pass

    today_dt = date.today()
    yesterday_dt = today_dt - timedelta(days=1)
    
    current_streak = 0
    if today_dt in log_dates or yesterday_dt in log_dates:
        # Loop backwards starting from the most recent logged date that is either today or yesterday
        current_check = today_dt if today_dt in log_dates else yesterday_dt
        while current_check in log_dates:
            current_streak += 1
            current_check -= timedelta(days=1)

    # Update users table with rolling average and streak
    cursor.execute(
        "UPDATE users SET discipline_score = ?, current_streak = ? WHERE id = ?",
        (rolling_avg, current_streak, user_id)
    )
    
    conn.commit()
    conn.close()

# ==========================================
# 6. PANDAS & ANALYTICS INTEGRATION
# ==========================================
def get_user_logs_df(user_id, days=30):
    """
    Pulls the last X days of logs into a Pandas DataFrame.
    Feeds Plotly, analytics, and Gemini AI.
    """
    conn = get_connection()
    query = '''
        SELECT log_date, sleep_hours, screen_time_hours, mood_score, productivity_score, discipline_score, notes
        FROM daily_logs 
        WHERE user_id = ? 
        ORDER BY log_date DESC 
        LIMIT ?
    '''
    df = pd.read_sql_query(query, conn, params=(user_id, days))
    conn.close()
    
    if not df.empty:
        df['log_date'] = pd.to_datetime(df['log_date'])
        df = df.sort_values(by='log_date', ascending=True) # Oldest to newest for graphing
        
    return df

def get_leaderboard():
    """Returns top users by overall discipline_score and streak."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT username, discipline_score, current_streak 
        FROM users 
        WHERE onboarding_completed = 1 
        ORDER BY discipline_score DESC, current_streak DESC 
        LIMIT 10
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# Initialize on import
init_db()
