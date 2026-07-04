import streamlit as st
import sqlite3
import pandas as pd
import google.generativeai as genai
import os
import datetime
import hashlib

DB_FILE = 'selfsync_v2.db'

st.set_page_config(page_title="SelfSync", layout="wide")

def apply_custom_theme():
    custom_css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        
        /* Global Font */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }
        
        /* Gradient Headers */
        h1, h2, h3 {
            background: -webkit-linear-gradient(45deg, #FF6B6B, #4ECDC4);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        /* Glowing Metrics */
        div[data-testid="stMetricValue"] {
            color: #4ECDC4 !important;
            text-shadow: 0px 0px 10px rgba(78, 205, 196, 0.5);
            font-weight: 800;
        }
        
        /* Sleek Buttons */
        div.stButton > button, div.stFormSubmitButton > button {
            border-radius: 8px;
            background: linear-gradient(90deg, #FF6B6B 0%, #FF8E53 100%) !important;
            color: white !important;
            border: none;
            transition: all 0.3s ease;
        }
        div.stButton > button:hover, div.stFormSubmitButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(255, 107, 107, 0.4) !important;
            border: none !important;
        }
        
        /* Progress Bar */
        .stProgress > div > div > div > div {
            background-color: #4ECDC4;
        }
        
        /* Chat bubbles */
        div[data-testid="stChatMessage"] {
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 10px;
            margin-bottom: 10px;
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

apply_custom_theme()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@st.cache_resource
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        # Phase 3: Users Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                password_hash TEXT
            )
        ''')
        
        # Phase 3: Daily Logs Table with user_id
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_logs (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                log_date TEXT,
                screen_time REAL,
                productive_time REAL,
                mood TEXT,
                ai_insight TEXT,
                UNIQUE(user_id, log_date),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        # Phase 3: User Settings Table with user_id
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                id INTEGER PRIMARY KEY,
                user_id INTEGER UNIQUE,
                primary_goal TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        conn.commit()

init_db()

# --- HELPER FUNCTIONS ---
def get_user_goal(user_id):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT primary_goal FROM user_settings WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else "Stay balanced and productive."

def update_user_goal(user_id, new_goal):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO user_settings (user_id, primary_goal) VALUES (?, ?)', (user_id, new_goal))
        conn.commit()

def fetch_recent_logs(user_id, days=7):
    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query(f'''
            SELECT * FROM daily_logs 
            WHERE user_id = {user_id}
            ORDER BY log_date DESC 
            LIMIT {days}
        ''', conn)
    return df

def calculate_streak(user_id):
    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query(f'''
            SELECT log_date FROM daily_logs 
            WHERE user_id = {user_id}
            ORDER BY log_date DESC
        ''', conn)
    if df.empty:
        return 0
    dates = pd.to_datetime(df['log_date']).dt.date.tolist()
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    
    streak = 0
    if dates[0] == today or dates[0] == yesterday:
        current_date = dates[0]
        streak = 1
        for d in dates[1:]:
            if d == current_date - datetime.timedelta(days=1):
                streak += 1
                current_date = d
            else:
                break
    return streak

def setup_gemini():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-1.5-flash")

# --- AUTHENTICATION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_id'] = None
    st.session_state['username'] = None

# Application Navigation
st.sidebar.title("SelfSync")

if not st.session_state['logged_in']:
    page = st.sidebar.radio("Navigation", ["Login / Register"])
else:
    st.sidebar.write(f"Welcome, **{st.session_state['username']}**!")
    page = st.sidebar.radio("Navigation", ["Dashboard", "Daily Log", "AI Coach Chat", "Settings"])
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.session_state['user_id'] = None
        st.session_state['username'] = None
        st.rerun()

if page == "Login / Register":
    st.title("Welcome to SelfSync")
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("login_form"):
            login_user = st.text_input("Username")
            login_pass = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            
            if submitted:
                hashed = hash_password(login_pass)
                with sqlite3.connect(DB_FILE) as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT id FROM users WHERE username = ? AND password_hash = ?', (login_user, hashed))
                    result = cursor.fetchone()
                    if result:
                        st.session_state['logged_in'] = True
                        st.session_state['user_id'] = result[0]
                        st.session_state['username'] = login_user
                        st.success("Logged in successfully!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")
                        
    with tab2:
        with st.form("register_form"):
            reg_user = st.text_input("New Username")
            reg_pass = st.text_input("New Password", type="password")
            reg_submit = st.form_submit_button("Register")
            
            if reg_submit:
                if len(reg_user) < 3 or len(reg_pass) < 3:
                    st.error("Username and password must be at least 3 characters.")
                else:
                    hashed = hash_password(reg_pass)
                    with sqlite3.connect(DB_FILE) as conn:
                        cursor = conn.cursor()
                        try:
                            cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (reg_user, hashed))
                            conn.commit()
                            st.success("Registration successful! Please login.")
                        except sqlite3.IntegrityError:
                            st.error("Username already exists.")

elif page == "Daily Log" and st.session_state['logged_in']:
    st.title("Daily Log")
    user_id = st.session_state['user_id']
    
    with st.form("daily_log_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            screen_time = st.number_input("Total Screen Time (hours)", min_value=0.0, step=0.5)
        with col2:
            productive_time = st.number_input("Productive Time (hours)", min_value=0.0, step=0.5)
        with col3:
            mood = st.selectbox("Overall Mood", ["Energized", "Neutral", "Drained", "Burnt Out"])
            
        submitted = st.form_submit_button("Submit")
        
        if submitted:
            log_date = str(datetime.date.today())
            model = setup_gemini()
            
            if model:
                goal = get_user_goal(user_id)
                prompt = f"Act as a Discipline Coach. User's main goal is: {goal}. User logged {screen_time}hrs screen time, {productive_time}hrs work, Mood: {mood}. Give a 2-sentence reality check and one habit challenge."
                try:
                    response = model.generate_content(prompt)
                    ai_insight = response.text
                except Exception:
                    ai_insight = "Your AI Coach is currently offline, but your data was saved. Stay focused!"
            else:
                ai_insight = "Gemini API key not found. Data saved locally."
                
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO daily_logs 
                    (user_id, log_date, screen_time, productive_time, mood, ai_insight)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, log_date, screen_time, productive_time, mood, ai_insight))
                conn.commit()
                
            st.success("Daily log saved successfully!")

elif page == "Dashboard" and st.session_state['logged_in']:
    st.title("Executive Dashboard")
    user_id = st.session_state['user_id']
    
    df = fetch_recent_logs(user_id)
        
    if df.empty:
        st.warning("No data found. Please navigate to the 'Daily Log' page to log your day!")
        st.stop()
        
    def calculate_score(row):
        score = 50
        if row['productive_time'] >= row['screen_time']:
            score += 30
        else:
            score -= 20
        return max(0, min(100, score))
        
    df['discipline_score'] = df.apply(calculate_score, axis=1)
    
    def get_badges(row):
        badges = []
        if row['discipline_score'] >= 80:
            badges.append("Laser Focus 🎯")
        if row['productive_time'] > 5:
            badges.append("Deep Worker 🧠")
        if row['screen_time'] < 2:
            badges.append("Digital Minimalist 🌿")
        return ", ".join(badges) if badges else "No badges yet"
        
    df['badges'] = df.apply(get_badges, axis=1)
    streak = calculate_streak(user_id)
    
    # SECTION A: The Status View
    most_recent = df.iloc[0]
    today_str = str(datetime.date.today())
    
    col1, col2 = st.columns([3, 1])
    with col1:
        if most_recent['log_date'] == today_str:
            st.subheader(f"Today's Standing | 🔥 {streak} Day Streak!")
        else:
            st.subheader(f"Most Recent Log: {most_recent['log_date']} | 🔥 {streak} Day Streak!")
    
    with col2:
        if st.button("Generate Weekly AI Summary"):
            st.session_state['generate_summary'] = True

    if st.session_state.get('generate_summary', False):
        with st.spinner("Generating AI Summary..."):
            model = setup_gemini()
            if model:
                goal = get_user_goal(user_id)
                recent_data_str = df.to_string()
                prompt = f"Act as a Discipline Coach. User's main goal is: {goal}. Here is their data for the last {len(df)} days:\n{recent_data_str}\n\nProvide a comprehensive, encouraging weekly summary (max 3 paragraphs) identifying trends, calling out areas for improvement, and suggesting a focus for next week."
                try:
                    response = model.generate_content(prompt)
                    st.success("**Weekly AI Summary:**\n\n" + response.text)
                except Exception as e:
                    st.error("Could not generate summary at this time. Please check your API key or internet connection.")
            else:
                st.error("Please set the GEMINI_API_KEY environment variable to use this feature.")
            st.session_state['generate_summary'] = False
        
    score_val = int(most_recent['discipline_score'])
    st.metric("Discipline Score", score_val)
    st.progress(score_val)
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Screen Time", f"{most_recent['screen_time']} hrs")
    with col_b:
        st.metric("Productive Time", f"{most_recent['productive_time']} hrs")
        
    st.markdown("##### Screen vs Productive Time Allocation")
    balance_df = pd.DataFrame(
        {"Hours": [most_recent['screen_time'], most_recent['productive_time']]},
        index=["Screen Time", "Productive Time"]
    )
    st.bar_chart(balance_df)
    
    st.info(f"**AI Coach Insight:**\n\n{most_recent['ai_insight']}")
    
    st.markdown("##### Recent Badges")
    recent_badges = df['badges'].iloc[0]
    st.success(f"**Earned:** {recent_badges}")
    
    st.markdown("---")
    
    # SECTION B: 7-Day Trends
    st.subheader("Weekly Trends")
    trend_df = df.copy()
    trend_df['log_date'] = pd.to_datetime(trend_df['log_date'])
    trend_df = trend_df.sort_values(by='log_date', ascending=True)
    trend_df = trend_df.set_index('log_date')
    
    st.markdown("##### Discipline Score Over Time")
    st.line_chart(trend_df[['discipline_score']])

elif page == "AI Coach Chat" and st.session_state['logged_in']:
    st.title("AI Coach Chat")
    user_id = st.session_state['user_id']
    
    # Isolate chat history by user_id
    chat_key = f"messages_{user_id}"
    
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []
        st.session_state[chat_key].append({"role": "assistant", "content": f"Hello {st.session_state['username']}! I'm your SelfSync AI coach. How can I help you stay on track today?"})

    for message in st.session_state[chat_key]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask your coach anything..."):
        st.chat_message("user").markdown(prompt)
        st.session_state[chat_key].append({"role": "user", "content": prompt})

        model = setup_gemini()
        if model:
            goal = get_user_goal(user_id)
            df = fetch_recent_logs(user_id)
            data_context = df.to_string() if not df.empty else "No recent data logged."
            
            system_context = f"You are a supportive discipline coach for the SelfSync app. The user's primary goal is: {goal}. Their recent logs:\n{data_context}\n\nKeep your responses concise, actionable, and encouraging."
            history_text = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in st.session_state[chat_key][-5:]])
            full_prompt = f"{system_context}\n\nChat History:\n{history_text}\n\nCoach (you):"
            
            try:
                response = model.generate_content(full_prompt)
                ai_reply = response.text
            except Exception:
                ai_reply = "I'm having trouble connecting to the network right now. Keep up the good work!"
                
            with st.chat_message("assistant"):
                st.markdown(ai_reply)
            st.session_state[chat_key].append({"role": "assistant", "content": ai_reply})
        else:
            st.error("Please configure your GEMINI_API_KEY to use the chat.")

elif page == "Settings" and st.session_state['logged_in']:
    st.title("Settings")
    user_id = st.session_state['user_id']
    current_goal = get_user_goal(user_id)
    
    st.subheader("Personalized Wellness Goal")
    with st.form("settings_form"):
        new_goal = st.text_area("What is your primary goal?", value=current_goal, height=100)
        submitted = st.form_submit_button("Save Goal")
        
        if submitted:
            update_user_goal(user_id, new_goal)
            st.success("Your goal has been updated!")
