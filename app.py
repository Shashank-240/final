import streamlit as st
import sqlite3
import pandas as pd
import google.generativeai as genai
import os
import datetime
import hashlib
import plotly.express as px

DB_FILE = 'selfsync_v2.db'
st.set_page_config(page_title="SelfSync | AI Digital Wellness", layout="wide", initial_sidebar_state="expanded")

def apply_custom_theme():
    """
    Hijacks Streamlit's native React DOM to enforce the Next.js/Tailwind v4 
    Glassmorphism and Dark Mode design system.
    """
    custom_css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        
        /* 1. Global Setup & Background */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: #f8fafc;
        }
        .stApp {
            background-color: #0c0c10;
            background-image: 
              radial-gradient(at 0% 0%, rgba(93, 67, 194, 0.15) 0px, transparent 50%),
              radial-gradient(at 100% 100%, rgba(20, 184, 166, 0.1) 0px, transparent 50%);
            background-attachment: fixed;
        }
        
        /* 2. Sidebar Glassmorphism */
        [data-testid="stSidebar"] {
            background-color: rgba(13, 13, 17, 0.65) !important;
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border-right: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        /* 3. Glass Cards (Metrics, Forms, and Chat) */
        [data-testid="stMetric"], form[data-testid="stForm"] {
            background: rgba(22, 22, 28, 0.35);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 1rem;
            padding: 1.5rem;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        [data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        /* Metric Typography Override */
        [data-testid="stMetricLabel"] {
            color: #94a3b8 !important;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-size: 0.75rem;
        }
        [data-testid="stMetricValue"] {
            color: #ffffff !important;
            font-weight: 800;
            font-size: 2.5rem;
        }
        
        /* 4. Premium Buttons */
        div.stButton > button, div.stFormSubmitButton > button {
            border-radius: 0.75rem;
            background: #5d43c2 !important; /* Primary Indigo */
            color: white !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            font-weight: 600;
            padding: 0.5rem 1.5rem;
            box-shadow: 0 4px 12px rgba(93, 67, 194, 0.3) !important;
            transition: all 0.2s ease;
        }
        div.stButton > button:hover, div.stFormSubmitButton > button:hover {
            background: #6d53d2 !important;
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(93, 67, 194, 0.4) !important;
        }
        
        /* 5. Progress Bar and Charts */
        .stProgress > div > div > div > div {
            background-color: #10b981; /* Emerald 500 */
            border-radius: 999px;
        }
        .stProgress > div > div {
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 999px;
        }
        
        /* 6. Insights & Alerts */
        .stAlert {
            background: rgba(93, 67, 194, 0.1) !important;
            border: 1px solid rgba(93, 67, 194, 0.2) !important;
            color: #e2e8f0 !important;
            border-radius: 1rem !important;
            backdrop-filter: blur(8px);
        }
        
        /* 7. Typography Accents */
        h1, h2, h3 {
            font-weight: 800;
            letter-spacing: -0.025em;
        }
        .text-glow-primary {
            background: -webkit-linear-gradient(45deg, #a78bfa, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        /* 8. Chat Interface Customization */
        div[data-testid="stChatMessage"] {
            background: rgba(22, 22, 28, 0.35);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 1rem;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        div[data-testid="stChatMessage"][data-baseweb="card"]:nth-child(even) {
            background: rgba(93, 67, 194, 0.15);
            border: 1px solid rgba(93, 67, 194, 0.2);
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
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                password_hash TEXT
            )
        ''')
        
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
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                id INTEGER PRIMARY KEY,
                user_id INTEGER UNIQUE,
                primary_goal TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        try:
            cursor.execute('ALTER TABLE user_settings ADD COLUMN habits TEXT')
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute('ALTER TABLE user_settings ADD COLUMN initial_score INTEGER')
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute('ALTER TABLE user_settings ADD COLUMN initial_feedback TEXT')
        except sqlite3.OperationalError:
            pass
            
        conn.commit()

init_db()

def premium_metric_card(title, value, subtitle="", icon="✨", color="#4ECDC4"):
    html = f"""
    <div style="background: rgba(22,22,28,0.4); border: 1px solid rgba(255,255,255,0.05); border-radius: 16px; padding: 20px; box-shadow: 0 4px 20px 0 rgba(0,0,0,0.2);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <span style="color: #94a3b8; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">{title}</span>
            <span style="background: {color}20; border: 1px solid {color}40; padding: 6px; border-radius: 8px; font-size: 16px;">{icon}</span>
        </div>
        <div style="color: white; font-size: 32px; font-weight: 800; margin-bottom: 4px;">{value}</div>
        <div style="color: {color}; font-size: 12px; font-weight: 600;">{subtitle}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def premium_trend_chart(df, x_col, y_col, title):
    fig = px.line(df, x=x_col, y=y_col, markers=True)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(showgrid=False, zeroline=False, title="", tickfont=dict(color="#94a3b8")),
        yaxis=dict(showgrid=False, zeroline=False, title="", tickfont=dict(color="#94a3b8")),
        title=dict(text=title, font=dict(color="white", size=16, family="Inter"))
    )
    fig.update_traces(line_color="#5d43c2", line_width=3, marker=dict(size=8, color="#4ECDC4"))
    st.plotly_chart(fig, use_container_width=True)

def premium_empty_state():
    html = """
    <div style="text-align: center; padding: 60px 20px; background: rgba(22,22,28,0.3); border-radius: 16px; border: 1px dashed rgba(255,255,255,0.1); margin: 20px 0;">
        <div style="font-size: 48px; margin-bottom: 16px; opacity: 0.9;">🔭</div>
        <h3 style="color: white; font-weight: 700; margin-bottom: 8px;">No Telemetry Found</h3>
        <p style="color: #94a3b8; font-size: 14px; max-width: 400px; margin: 0 auto;">Your dashboard is waiting for data. Head over to the Daily Log to record your first session.</p>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
    st.stop()

# --- HELPER FUNCTIONS ---
def get_user_onboarding(user_id):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT habits, initial_score, initial_feedback FROM user_settings WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        if result and result[1] is not None:
            return {"habits": result[0], "score": result[1], "feedback": result[2]}
        return None

def save_user_onboarding(user_id, habits, score, feedback):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_settings (user_id, habits, initial_score, initial_feedback) 
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET 
            habits = excluded.habits, 
            initial_score = excluded.initial_score,
            initial_feedback = excluded.initial_feedback
        ''', (user_id, habits, score, feedback))
        conn.commit()

def get_user_goal(user_id):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT primary_goal FROM user_settings WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else "Stay balanced and productive."

def update_user_goal(user_id, new_goal):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_settings (user_id, primary_goal) 
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET primary_goal = excluded.primary_goal
        ''', (user_id, new_goal))
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

# --- NAVIGATION ---
st.sidebar.markdown("<h2 class='text-glow-primary'>SelfSync AI</h2>", unsafe_allow_html=True)
st.sidebar.markdown("---")

if not st.session_state['logged_in']:
    page = st.sidebar.radio("Navigation", ["Login / Register"])
else:
    st.sidebar.write(f"Welcome, **{st.session_state['username']}**")
    
    onboarding_data = get_user_onboarding(st.session_state['user_id'])
    
    if not onboarding_data:
        page = "Onboarding"
        st.sidebar.warning("Please complete your baseline setup.")
    else:
        page = st.sidebar.radio("Navigation", ["Dashboard", "Daily Log", "AI Coach Chat", "Settings"])
        
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state['logged_in'] = False
        st.session_state['user_id'] = None
        st.session_state['username'] = None
        st.rerun()

# --- PAGES ---

if page == "Onboarding" and st.session_state['logged_in']:
    st.markdown("<h1 class='text-glow-primary'>System Calibration</h1>", unsafe_allow_html=True)
    st.write("Welcome to SelfSync! Before you enter the dashboard, we need to establish your baseline.")
    user_id = st.session_state['user_id']
    
    with st.form("onboarding_form"):
        st.markdown("### please list your habits and hobbies you have ?")
        habits = st.text_area("Be honest. The AI will use this to calculate your initial behavioural score.", height=150)
        submitted = st.form_submit_button("Calculate Initial Score")
        
        if submitted:
            if len(habits) < 5:
                st.error("Please provide more detail about your habits.")
            else:
                with st.spinner("AI is analyzing your behavioral baseline..."):
                    model = setup_gemini()
                    if model:
                        prompt = f"Analyze these habits and hobbies: '{habits}'. Calculate an initial behavioural discipline score from 0 to 100. Provide a 2-sentence reality check. IMPORTANT: Your response must be in this exact format:\nSCORE: [number]\nFEEDBACK: [text]"
                        try:
                            response = model.generate_content(prompt)
                            text = response.text
                            score = 50
                            feedback = text
                            for line in text.split('\n'):
                                if "SCORE:" in line.upper():
                                    try:
                                        score = int(''.join(filter(str.isdigit, line)))
                                    except:
                                        pass
                                elif "FEEDBACK:" in line.upper():
                                    feedback = line.split("FEEDBACK:")[1].strip()
                            
                            save_user_onboarding(user_id, habits, score, feedback)
                            st.success(f"Baseline established! Your initial score is {score}.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"AI generation failed. {e}")
                    else:
                        st.error("Gemini API Key missing. Cannot complete onboarding.")

if page == "Login / Register":
    st.markdown("<h1 class='text-glow-primary'>Welcome to SelfSync</h1>", unsafe_allow_html=True)
    st.write("Synchronize your digital habits with your real-life ambitions.")
    st.markdown("<br>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("login_form"):
            login_user = st.text_input("Username")
            login_pass = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Access Dashboard")
            
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
                        st.success("Authentication successful.")
                        st.rerun()
                    else:
                        st.error("Invalid credentials.")
                        
    with tab2:
        with st.form("register_form"):
            reg_user = st.text_input("New Username")
            reg_pass = st.text_input("New Password", type="password")
            reg_submit = st.form_submit_button("Create Account")
            
            if reg_submit:
                if len(reg_user) < 3 or len(reg_pass) < 3:
                    st.error("Credentials must be at least 3 characters.")
                else:
                    hashed = hash_password(reg_pass)
                    with sqlite3.connect(DB_FILE) as conn:
                        cursor = conn.cursor()
                        try:
                            cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (reg_user, hashed))
                            conn.commit()
                            st.success("Account provisioned! Please login.")
                        except sqlite3.IntegrityError:
                            st.error("Username already exists.")

elif page == "Daily Log" and st.session_state['logged_in']:
    st.markdown("<h1>Daily Data Ingestion</h1>", unsafe_allow_html=True)
    st.write("Log your device telemetry to generate your daily AI insights.")
    user_id = st.session_state['user_id']
    
    with st.form("daily_log_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            screen_time = st.number_input("Total Screen Time (hours)", min_value=0.0, step=0.5)
        with col2:
            productive_time = st.number_input("Productive Time (hours)", min_value=0.0, step=0.5)
        with col3:
            mood = st.selectbox("Overall Mood", ["Energized", "Neutral", "Drained", "Burnt Out"])
            
        submitted = st.form_submit_button("Sync Data")
        
        if submitted:
            log_date = str(datetime.date.today())
            model = setup_gemini()
            
            if model:
                goal = get_user_goal(user_id)
                prompt = f"Act as a strict but supportive Discipline Coach. User's main goal is: {goal}. User logged {screen_time}hrs screen time, {productive_time}hrs work, Mood: {mood}. Give a 2-sentence reality check and one habit challenge."
                try:
                    response = model.generate_content(prompt)
                    ai_insight = response.text
                except Exception:
                    ai_insight = "Your AI Coach is currently offline, but telemetry was saved."
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
                
            st.success("Daily telemetry synced successfully!")

elif page == "Dashboard" and st.session_state['logged_in']:
    st.markdown("<h1>Executive Dashboard</h1>", unsafe_allow_html=True)
    user_id = st.session_state['user_id']
    
    df = fetch_recent_logs(user_id)
        
    if df.empty:
        premium_empty_state()
        
    def calculate_score(row):
        score = 50
        if row['productive_time'] >= row['screen_time']:
            score += 30
        else:
            score -= 20
        return max(0, min(100, score))
        
    df['discipline_score'] = df.apply(calculate_score, axis=1)
    streak = calculate_streak(user_id)
    
    # SECTION A: The Status View
    most_recent = df.iloc[0]
    today_str = str(datetime.date.today())
    
    st.markdown("<br>", unsafe_allow_html=True)
    col_header, col_btn = st.columns([3, 1])
    with col_header:
        if most_recent['log_date'] == today_str:
            st.markdown(f"### Today's Standing | 🔥 {streak} Day Streak")
        else:
            st.markdown(f"### Most Recent Log: {most_recent['log_date']} | 🔥 {streak} Day Streak")
    
    with col_btn:
        if st.button("Generate Weekly AI Report", use_container_width=True):
            st.session_state['generate_summary'] = True
            
    if st.session_state.get('generate_summary', False):
        with st.spinner("Analyzing historical telemetry..."):
            model = setup_gemini()
            if model:
                goal = get_user_goal(user_id)
                recent_data_str = df.to_string()
                prompt = f"Act as a Discipline Coach. User's main goal is: {goal}. Here is their data for the last {len(df)} days:\n{recent_data_str}\n\nProvide a comprehensive, encouraging weekly summary (max 2 paragraphs) identifying trends and suggesting a focus for next week."
                try:
                    response = model.generate_content(prompt)
                    st.info(f"**AI Weekly Report:**\n\n{response.text}")
                except Exception as e:
                    st.error("Could not generate summary at this time.")
            else:
                st.error("Please set the GEMINI_API_KEY environment variable.")
            st.session_state['generate_summary'] = False
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    score_val = int(most_recent['discipline_score'])
    onboarding_data = get_user_onboarding(user_id)
    initial_score = onboarding_data['score'] if onboarding_data else 50
    
    with m1:
        premium_metric_card("Discipline Index", f"{score_val}", "Out of 100", "🎯", "#10b981")
    with m2:
        premium_metric_card("Baseline Score", f"{initial_score}", "Initial behaviour", "🏁", "#8b5cf6")
    with m3:
        premium_metric_card("Screen Time", f"{most_recent['screen_time']}h", "Total usage", "📱", "#f43f5e")
    with m4:
        premium_metric_card("Productive Work", f"{most_recent['productive_time']}h", "Deep focus", "💻", "#3b82f6")
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Charts and AI Row
    c_chart, c_ai = st.columns([1, 2])
    with c_chart:
        st.markdown("##### Time Allocation")
        balance_df = pd.DataFrame(
            {"Hours": [most_recent['screen_time'], most_recent['productive_time']]},
            index=["Screen", "Productive"]
        )
        st.bar_chart(balance_df, color="#4ECDC4")
        
    with c_ai:
        st.markdown("##### AI Coach Insight")
        st.info(most_recent['ai_insight'])
    
    st.markdown("---")
    
    # SECTION B: 7-Day Trends
    st.markdown("### Weekly Index Trends")
    trend_df = df.copy()
    trend_df['log_date'] = pd.to_datetime(trend_df['log_date'])
    trend_df = trend_df.sort_values(by='log_date', ascending=True)
    trend_df = trend_df.set_index('log_date')
    
    premium_trend_chart(trend_df.reset_index(), 'log_date', 'discipline_score', "Weekly Index Trends")

elif page == "AI Coach Chat" and st.session_state['logged_in']:
    st.markdown("<h1>Cognitive Coach Sync</h1>", unsafe_allow_html=True)
    user_id = st.session_state['user_id']
    
    chat_key = f"messages_{user_id}"
    
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []
        st.session_state[chat_key].append({"role": "assistant", "content": f"Hello {st.session_state['username']}. I am monitoring your telemetry. How can we optimize your focus today?"})
        
    for message in st.session_state[chat_key]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
    if prompt := st.chat_input("Ask about your digital habits..."):
        st.chat_message("user").markdown(prompt)
        st.session_state[chat_key].append({"role": "user", "content": prompt})
        model = setup_gemini()
        if model:
            goal = get_user_goal(user_id)
            df = fetch_recent_logs(user_id)
            data_context = df.to_string() if not df.empty else "No recent data logged."
            
            system_context = f"You are a highly analytical, premium AI coach for SelfSync. Goal: {goal}. Recent logs:\n{data_context}\n\nKeep responses concise, data-driven, and highly actionable."
            history_text = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in st.session_state[chat_key][-5:]])
            full_prompt = f"{system_context}\n\nChat History:\n{history_text}\n\nCoach (you):"
            
            try:
                response = model.generate_content(full_prompt)
                ai_reply = response.text
            except Exception:
                ai_reply = "Cognitive system offline. Check API keys."
                
            with st.chat_message("assistant"):
                st.markdown(ai_reply)
            st.session_state[chat_key].append({"role": "assistant", "content": ai_reply})
        else:
            st.error("Please configure your GEMINI_API_KEY.")

elif page == "Settings" and st.session_state['logged_in']:
    st.markdown("<h1>Profile & Parameters</h1>", unsafe_allow_html=True)
    user_id = st.session_state['user_id']
    current_goal = get_user_goal(user_id)
    
    st.write("Calibrate your digital boundaries and AI coach context.")
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.form("settings_form"):
        new_goal = st.text_area("Primary Wellness Objective", value=current_goal, height=100)
        submitted = st.form_submit_button("Save Parameters")
        
        if submitted:
            update_user_goal(user_id, new_goal)
            st.success("System parameters updated successfully.")
