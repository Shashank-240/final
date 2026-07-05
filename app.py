import streamlit as st
from datetime import date, datetime, timedelta
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import database
import visuals
import ai_logic

# ==========================================
# 1. PAGE CONFIGURATION & UI SETUP
# ==========================================
st.set_page_config(
    page_title="SelfSync | DisciplineOS",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. SESSION STATE INITIALIZATION
# ==========================================
def init_session_state():
    """Initializes global state variables if they don't exist."""
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'Landing'
    if 'is_authenticated' not in st.session_state:
        st.session_state.is_authenticated = False
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'has_completed_onboarding' not in st.session_state:
        st.session_state.has_completed_onboarding = False
    if 'gemini_api_key' not in st.session_state:
        st.session_state.gemini_api_key = ""
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = [
            ("COACH", "I am Ares, your brutal discipline coach. Log your daily stats and let's see how much you compromised today.")
        ]
    if 'success_message' not in st.session_state:
        st.session_state.success_message = None

init_session_state()

# ==========================================
# 3. ROUTING CALLBACKS
# ==========================================
def navigate_to(page):
    """Callback function to change pages and trigger a rerun."""
    st.session_state.current_page = page

def login_user(user_id, completed_onboarding, username):
    """Callback to handle authentication state."""
    st.session_state.is_authenticated = True
    st.session_state.user_id = user_id
    st.session_state.username = username
    st.session_state.has_completed_onboarding = bool(completed_onboarding)
    
    if st.session_state.has_completed_onboarding:
        st.session_state.current_page = 'Dashboard'
    else:
        st.session_state.current_page = 'Onboarding'

def logout_user():
    """Clears authentication state and redirects to Landing."""
    st.session_state.is_authenticated = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.chat_history = [
        ("COACH", "I am Ares, your brutal discipline coach. Log your daily stats and let's see how much you compromised today.")
    ]
    st.session_state.current_page = 'Landing'

# ==========================================
# 4. PAGE RENDERERS
# ==========================================

def render_landing():
    st.markdown("""
    <div style='display: flex; flex-direction: column; align-items: center; justify-content: center; padding-top: 10vh; padding-bottom: 5vh;'>
        <h1 style='font-family: "Courier New", monospace; font-size: 5.5rem; font-weight: 900; margin-bottom: 0px; letter-spacing: -2px; text-shadow: 0 0 30px rgba(167, 139, 250, 0.4); background: linear-gradient(135deg, #a78bfa 0%, #8b5cf6 50%, #14b8a6 100%); color: transparent; -webkit-background-clip: text; background-clip: text;'>
            S E L F / S Y N C
        </h1>
        <p style='font-size: 1.3rem; color: #9ca3af; font-weight: 600; letter-spacing: 4px; margin-top: 15px; margin-bottom: 40px; text-transform: uppercase;'>
            // DISCIPLINE O.S //
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class="glass-card" style="text-align: center; margin-bottom: 30px;">
            <h3 style="margin-top: 0; color: #a78bfa;">🔥 Stop Negotiating With Yourself</h3>
            <p style="color: #d1d5db; line-height: 1.6; font-size: 0.95rem;">
                SelfSync is not another friendly habit tracker. It is a mirror for your discipline. 
                Log your sleep, screen time, and habits daily. Ares, your AI coach, will analyze your 
                data and give you a brutal reality check. Compete on the leaderboard and compound your habits.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.button("Enter the Forge (Login / Sign Up)", on_click=navigate_to, args=('Auth',), type="primary")

def render_auth():
    st.markdown("<h2 style='text-align: center; margin-bottom: 30px; font-weight: 800; color: #a78bfa;'>Identify Yourself</h2>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.form("auth_form"):
            st.markdown("<p style='color: #9ca3af; font-size: 0.9rem;'>Enter your username and password. If the username doesn't exist, we will forge a new account for you.</p>", unsafe_allow_html=True)
            username_input = st.text_input("Username", placeholder="e.g. Spartan01", max_chars=20)
            password_input = st.text_input("Password", type="password")
            
            submit_auth = st.form_submit_button("Enter the Forge", type="primary")
            
            if submit_auth:
                username = username_input.strip()
                password = password_input.strip()
                if not username or not password:
                    st.error("Username and password cannot be empty.")
                else:
                    user = database.get_user_by_username(username)
                    if user:
                        verified_user = database.verify_user(username, password)
                        if verified_user:
                            login_user(verified_user['id'], verified_user['onboarding_completed'], verified_user['username'])
                            st.rerun()
                        else:
                            st.error("Incorrect password.")
                    else:
                        new_id = database.create_user(username, password)
                        if new_id:
                            database.setup_default_habits(new_id)
                            login_user(new_id, completed_onboarding=False, username=username)
                            st.rerun()
                        else:
                            st.error("Failed to create profile. Try another username.")
        
        st.button("Cancel & Go Back", on_click=navigate_to, args=('Landing',))

def render_onboarding():
    user_id = st.session_state.user_id
    st.markdown(f"<h2 style='font-weight: 800; color: #a78bfa; margin-bottom: 5px;'>Onboarding | Set Your Baselines</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #9ca3af; margin-bottom: 35px;'>Configure your goals and select the habits you commit to tracking daily.</p>", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### ⚙️ Target Benchmarks")
        target_sleep = st.slider("Target Sleep Hours", min_value=4.0, max_value=12.0, value=8.0, step=0.5, help="How many hours of sleep your body needs to operate optimally.")
        target_screen = st.slider("Screen Time Limit (Hours)", min_value=1.0, max_value=12.0, value=4.0, step=0.5, help="Maximum allowed screen usage (phone + entertainment) before you lose points.")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 🛡️ Starting Habits (Check to Select)")
        st.markdown("<p style='color: #9ca3af; font-size: 0.85rem;'>You can add, edit, or delete habits later in your settings.</p>", unsafe_allow_html=True)
        
        default_habits = [
            ("Exercise / Workout", "good", True),
            ("Read a Book / Study", "good", True),
            ("Meditation / Mindfulness", "good", False),
            ("Drink 3L Water", "good", True),
            ("Learn a New Skill / Code", "good", False),
            ("Journaling / Reflection", "good", False),
            ("Doomscrolling on Social Media", "bad", True),
            ("Junk Food / Sugar Intake", "bad", True),
            ("Procrastination / Delays", "bad", True),
            ("Binge-watching TV/YouTube", "bad", False),
            ("Sleeping < 6 Hours", "bad", False)
        ]
        
        selected_habits = []
        for name, htype, default_val in default_habits:
            label = f"✨ [Good] {name}" if htype == 'good' else f"🛑 [Bad] {name}"
            chk = st.checkbox(label, value=default_val)
            if chk:
                selected_habits.append((name, htype))

    with col2:

        if st.button("Initialize Discipline Engine", type="primary", use_container_width=True):
            if not selected_habits:
                st.error("You must select at least one habit to track.")
            else:
                # 1. Update targets
                database.update_user_targets(user_id, target_sleep, target_screen)
                
                # 2. Clear old habits and write selected ones
                conn = database.get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM habits WHERE user_id = ?", (user_id,))
                for name, htype in selected_habits:
                    cursor.execute("INSERT INTO habits (user_id, habit_name, habit_type) VALUES (?, ?, ?)", (user_id, name, htype))
                conn.commit()
                conn.close()
                
                # 3. Mark onboarding complete
                database.complete_onboarding(user_id)
                st.session_state.has_completed_onboarding = True
                
                # 4. Redirect
                navigate_to('Dashboard')
                st.rerun()

def render_dashboard():
    user_id = st.session_state.user_id
    user = database.get_user_by_id(user_id)
    if not user:
        logout_user()
        st.rerun()

    # Main Header
    st.markdown(f"<h2 style='font-weight: 800; margin-bottom: 5px;'>Command Center</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: #9ca3af; margin-bottom: 25px;'>Disciplining focus for username: <span style='color: #a78bfa; font-weight: 600;'>{user['username']}</span></p>", unsafe_allow_html=True)

    today_str = str(date.today())
    today_log = database.get_daily_log(user_id, today_str)

    # 1. METRICS GRID
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    
    # Calculate screen and sleep values today
    sleep_val = f"{today_log['sleep_hours']}h / {user['target_sleep']}h" if today_log else "No Data"
    screen_val = f"{today_log['screen_time_hours']}h / {user['target_screen_time']}h" if today_log else "No Data"
    score_val = f"{user['discipline_score']}/100"
    streak_val = f"{user['current_streak']} Days"

    with m_col1:
        visuals.render_glass_metric("Discipline Score", score_val, "⚡")
    with m_col2:
        visuals.render_glass_metric("Active Streak", streak_val, "🔥")
    with m_col3:
        visuals.render_glass_metric("Sleep / Target", sleep_val, "🌙")
    with m_col4:
        # Invert colors for screen time card (so higher is red/bad)
        visuals.render_glass_metric("Screen / Limit", screen_val, "📱", invert_colors=True)

    # 2. MAIN LAYOUT
    col_chart, col_habits = st.columns([1.6, 1])

    with col_chart:
        st.markdown("### 📈 7-Day Performance")
        df_logs = database.get_user_logs_df(user_id, days=7)
        
        if df_logs.empty:
            visuals.render_empty_state("No Analytics Logs", "You need to log at least one day to display performance charts.", "📊")
        else:
            # Generate Plotly Chart
            fig = px.area(
                df_logs, 
                x='log_date', 
                y='discipline_score',
                labels={'discipline_score': 'Score', 'log_date': 'Date'},
                color_discrete_sequence=['#8b5cf6']
            )
            fig.update_traces(
                line_color='#8b5cf6', 
                line_width=3, 
                fillcolor='rgba(139, 92, 246, 0.1)'
            )
            fig.add_trace(
                go.Scatter(
                    x=df_logs['log_date'], 
                    y=df_logs['discipline_score'], 
                    mode='markers', 
                    marker=dict(size=8, color='#a78bfa', line=dict(width=2, color='#ffffff')),
                    name='Daily Score'
                )
            )
            # Apply styling
            fig = visuals.style_glass_fig(fig)
            fig.update_layout(yaxis=dict(range=[0, 105], showticklabels=True))
            st.plotly_chart(fig, use_container_width=True)

    with col_habits:
        st.markdown("### 🎯 Today's Habit Status")
        today_habits = database.get_daily_habits_status(user_id, today_str)

        if not today_habits:
            visuals.render_empty_state("No Habits Defined", "Create habits in settings to start tracking.", "🛡️")
        else:
            if not today_log:
                st.markdown("<p style='color: #9ca3af; font-size: 0.9rem;'>No daily activity logged for today yet. Displaying default habit states.</p>", unsafe_allow_html=True)
            
            for h in today_habits:
                status_color = "#10b981" if ((h['habit_type'] == 'good' and h['completed']) or (h['habit_type'] == 'bad' and not h['completed'])) else "#ef4444"
                status_text = "COMPLETED" if (h['habit_type'] == 'good' and h['completed']) else (
                    "AVOIDED" if (h['habit_type'] == 'bad' and not h['completed']) else (
                        "FAILED" if h['habit_type'] == 'good' else "TRIGGERED"
                    )
                )
                status_icon = "✅" if status_text == "COMPLETED" else ("🛡️" if status_text == "AVOIDED" else "❌")
                
                label_color = "#34d399" if h['habit_type'] == 'good' else "#f87171"
                type_prefix = "[Good]" if h['habit_type'] == 'good' else "[Bad]"
                
                st.markdown(f"""
                <div class="habit-row">
                    <div>
                        <span style="color: {label_color}; font-size: 0.8rem; font-weight: 700; margin-right: 8px;">{type_prefix}</span>
                        <span style="color: #ffffff; font-weight: 500;">{h['habit_name']}</span>
                    </div>
                    <span style="color: {status_color}; font-weight: 700; font-size: 0.85rem;">
                        {status_icon} {status_text}
                    </span>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.button("Update Log / Check-in", on_click=navigate_to, args=('Journal',))

def render_journal():
    user_id = st.session_state.user_id
    user = database.get_user_by_id(user_id)
    
    st.markdown("<h2 style='font-weight: 800;'>Daily Log Journal</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #9ca3af;'>Keep your statistics honest. Retroactive logging is fully supported.</p>", unsafe_allow_html=True)

    # Date Selector
    selected_date = st.date_input("Select Date to Log", value=date.today())
    selected_date_str = str(selected_date)

    # Fetch existing data for that day if it exists
    existing_log = database.get_daily_log(user_id, selected_date_str)
    
    # Pre-populate variables
    pre_sleep = existing_log['sleep_hours'] if existing_log else user['target_sleep']
    pre_screen = existing_log['screen_time_hours'] if existing_log else user['target_screen_time']
    pre_mood = existing_log['mood_score'] if existing_log else 6
    pre_prod = existing_log['productivity_score'] if existing_log else 6
    pre_notes = existing_log['notes'] if existing_log else ""

    col_form, col_info = st.columns([1.2, 1])

    with col_form:
        st.markdown(f"### Log Stats for: `{selected_date_str}`")
        
        # We wrap input elements in a streamlit container to keep them organized
        sleep_hrs = st.slider("Sleep Duration (Hours)", min_value=0.0, max_value=24.0, value=float(pre_sleep), step=0.5, key=f"sleep_{selected_date_str}")
        screen_hrs = st.slider("Screen Time Usage (Hours)", min_value=0.0, max_value=24.0, value=float(pre_screen), step=0.5, key=f"screen_{selected_date_str}")
        
        col_sliders = st.columns(2)
        with col_sliders[0]:
            mood_val = st.slider("Mood (1 - 10)", min_value=1, max_value=10, value=int(pre_mood), key=f"mood_{selected_date_str}")
        with col_sliders[1]:
            prod_val = st.slider("Productivity (1 - 10)", min_value=1, max_value=10, value=int(pre_prod), key=f"prod_{selected_date_str}")
            
        notes_val = st.text_area("Observations / Notes", value=pre_notes, placeholder="Describe obstacles, highlights, or why you slipped up today...", max_chars=500, key=f"notes_{selected_date_str}")

    with col_info:
        st.markdown("### 🎯 Habit Verification")
        st.markdown("<p style='color: #9ca3af; font-size: 0.85rem;'>Check off completed good habits. Check bad habits ONLY if you gave in (unchecked means avoided!).</p>", unsafe_allow_html=True)
        
        daily_habits = database.get_daily_habits_status(user_id, selected_date_str)
        
        habit_checkbox_states = {}
        
        good_list = [h for h in daily_habits if h['habit_type'] == 'good']
        bad_list = [h for h in daily_habits if h['habit_type'] == 'bad']

        if not daily_habits:
            st.info("No habits defined. Go to Profile & Settings to add habits.")
        else:
            if good_list:
                st.markdown("<strong style='color: #10b981;'>✨ Positive Habits Completed</strong>", unsafe_allow_html=True)
                for h in good_list:
                    habit_checkbox_states[h['habit_id']] = st.checkbox(
                        h['habit_name'], 
                        value=bool(h['completed']), 
                        key=f"good_{h['habit_id']}_{selected_date_str}"
                    )
            
            if bad_list:
                st.markdown("<br><strong style='color: #ef4444;'>🛑 Bad Habits Triggered (Check if Done)</strong>", unsafe_allow_html=True)
                for h in bad_list:
                    habit_checkbox_states[h['habit_id']] = st.checkbox(
                        h['habit_name'], 
                        value=bool(h['completed']), 
                        key=f"bad_{h['habit_id']}_{selected_date_str}",
                        help="Check this ONLY if you did this bad habit today."
                    )

        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("Forge Daily Entry (Submit)", type="primary", use_container_width=True):
            # 1. Upsert daily log
            database.upsert_daily_log(
                user_id=user_id,
                log_date=selected_date_str,
                sleep=sleep_hrs,
                screen_time=screen_hrs,
                mood=mood_val,
                productivity=prod_val,
                notes=notes_val
            )
            
            # 2. Upsert daily habits
            for habit_id, completed in habit_checkbox_states.items():
                database.upsert_daily_habit(
                    log_date=selected_date_str,
                    user_id=user_id,
                    habit_id=habit_id,
                    completed=completed
                )
            
            # Re-fetch log to get calculated score
            fresh_log = database.get_daily_log(user_id, selected_date_str)
            fresh_score = fresh_log['discipline_score'] if fresh_log else 0
            
            st.session_state.success_message = f"🔥 Daily log for {selected_date_str} successfully forged! Today's Discipline Score: {fresh_score}/100."
            
            # If notes were provided, auto-trigger the AI Coach and redirect there for analysis
            if notes_val.strip():
                import ai_logic
                api_key = st.session_state.gemini_api_key or os.getenv("GEMINI_API_KEY")
                
                # Append user prompt to chat history
                user_msg = f"[System Log]: I scored {fresh_score}/100 today. My notes: '{notes_val}'"
                st.session_state.chat_history.append(("USER", user_msg))
                
                # Get brutal AI analysis
                ai_feedback = ai_logic.chat_with_coach(
                    api_key=api_key,
                    user_id=user_id,
                    user_message=f"I just submitted my daily log. My score is {fresh_score}/100. My personal notes are: '{notes_val}'. Give me a brutal, 2-sentence reality check about these specific notes.",
                    chat_history=st.session_state.chat_history[:-1]
                )
                
                st.session_state.chat_history.append(("COACH", ai_feedback))
                st.session_state.current_page = 'AICoach'
            else:
                # Redirect to Analytics if no notes to analyze
                st.session_state.current_page = 'Analytics'
                
            st.rerun()

def render_ai_coach():
    user_id = st.session_state.user_id
    user = database.get_user_by_id(user_id)

    st.markdown("<h2 style='font-weight: 800;'>AI Coach | Ares</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #9ca3af; margin-bottom: 20px;'>Ares analyzes your habits and sleep, providing brutal feedback. No excuses allowed.</p>", unsafe_allow_html=True)

    # Key setup warning
    api_key = st.session_state.gemini_api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.warning("⚠️ Running in offline Mode. Configure your Gemini API Key in Settings for deep conversations, or type 'critique' to run the rule-based critique engine.")

    # Scrollable chat logs container
    chat_container = st.container()
    
    # Display Chat messages
    with chat_container:
        for role, message in st.session_state.chat_history:
            if role == "USER":
                with st.chat_message("user"):
                    st.markdown(message)
            else:
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(message)

    # Input textbox
    user_input = st.chat_input("Explain your slip-ups, ask for guidance, or type 'critique' for today's review...")

    if user_input:
        # Append User Input
        st.session_state.chat_history.append(("USER", user_input))
        
        # Display instantly
        with chat_container:
            with st.chat_message("user"):
                st.markdown(user_input)

        # Generate Response
        with chat_container:
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("Ares is writing your reality check..."):
                    response_text = ai_logic.chat_with_coach(
                        api_key=api_key,
                        user_id=user_id,
                        user_message=user_input,
                        chat_history=st.session_state.chat_history[:-1]
                    )
                    st.markdown(response_text)
        
        # Append response
        st.session_state.chat_history.append(("COACH", response_text))
        st.rerun()

    # Clear chat utility
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Clear Chat Conversation", use_container_width=False):
        st.session_state.chat_history = [
            ("COACH", "I am Ares, your brutal discipline coach. Log your daily stats and let's see how much you compromised today.")
        ]
        st.rerun()

def render_analytics():
    user_id = st.session_state.user_id
    user = database.get_user_by_id(user_id)
    df_logs = database.get_user_logs_df(user_id, days=30)

    col_title, col_btn = st.columns([3.5, 1])
    with col_title:
        st.markdown("<h2 style='font-weight: 800; margin: 0;'>Deep Analytics Engine</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color: #9ca3af; margin-bottom: 25px; margin-top: 5px;'>Long-term statistical correlations between sleep, screen usage, and mental productivity.</p>", unsafe_allow_html=True)
    with col_btn:
        st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
        st.markdown("<div class='back-home-wrapper'>", unsafe_allow_html=True)
        st.button("↩️ Back to Home", on_click=navigate_to, args=('Dashboard',), key="back_to_home_analytics")
        st.markdown("</div>", unsafe_allow_html=True)

    if df_logs.empty:
        visuals.render_empty_state("Insufficient Historical Logs", "Log at least 3 days of habits to see correlations and predictive graphs.", "📈")
        return

    # 1. BURNOUT PREDICTION ALGORITHM
    if len(df_logs) >= 3:
        # Sort chronologically for moving averages
        df_sorted = df_logs.sort_values(by='log_date')
        
        # Calculate trailing 3-log averages
        df_sorted['sleep_roll'] = df_sorted['sleep_hours'].rolling(window=min(3, len(df_sorted))).mean()
        df_sorted['screen_roll'] = df_sorted['screen_time_hours'].rolling(window=min(3, len(df_sorted))).mean()
        df_sorted['prod_roll'] = df_sorted['productivity_score'].rolling(window=min(3, len(df_sorted))).mean()
        
        last_row = df_sorted.iloc[-1]
        
        # Burnout threshold logic: Screen time increasing, Sleep decreasing, Productivity falling
        is_high_screen = last_row['screen_time_hours'] > user['target_screen_time'] + 1.5
        is_low_sleep = last_row['sleep_hours'] < user['target_sleep'] - 1.5
        is_falling_prod = last_row['productivity_score'] < 5
        
        if is_high_screen and is_low_sleep:
            st.error("""
            ### 🚨 BURNOUT WARNING: High Risk
            Your screen time averages are elevated while your sleep levels are failing. 
            Productivity and energy levels are forecast to drop sharply. Reclaim control of your environment immediately.
            """)
        elif is_high_screen or is_low_sleep:
            st.warning("""
            ### ⚠️ BURNOUT WARNING: Moderate Risk
            Either screen time limit violations or sleep debts are beginning to accumulate. 
            Maintain your boundaries to avoid slipping into chronic brain fog.
            """)
        else:
            st.success("""
            ### 🟢 System Status: Harmonized
            Your habits are in a healthy equilibrium. Your targets are respected and your screen time is controlled. Maintain this status.
            """)
            
    # 2. CHARTS SECTIONS
    col_trends, col_scatter = st.columns(2)
    
    with col_trends:
        st.markdown("### 📊 Metrics Variance (30 Days)")
        fig_trend = px.line(
            df_logs,
            x='log_date',
            y=['sleep_hours', 'screen_time_hours', 'productivity_score'],
            labels={'value': 'Level', 'variable': 'Metric', 'log_date': 'Date'},
            color_discrete_map={
                'sleep_hours': '#10b981',
                'screen_time_hours': '#ef4444',
                'productivity_score': '#8b5cf6'
            }
        )
        fig_trend = visuals.style_glass_fig(fig_trend)
        st.plotly_chart(fig_trend, use_container_width=True)

    with col_scatter:
        st.markdown("### 📱 Screen Time vs Productivity Impact")
        fig_scatter = px.scatter(
            df_logs,
            x='screen_time_hours',
            y='productivity_score',
            size='mood_score',
            color_discrete_sequence=['#a78bfa'],
            labels={'screen_time_hours': 'Screen Time (Hours)', 'productivity_score': 'Productivity (1-10)'}
        )
        fig_scatter = visuals.style_glass_fig(fig_scatter)
        st.plotly_chart(fig_scatter, use_container_width=True)

    # 3. FUTURE YOU CALCULATOR
    st.markdown("### 🔮 The \"Future You\" Compound Projections")
    rolling_score = user['discipline_score']
    
    col_comp1, col_comp2 = st.columns([1, 1.5])
    with col_comp1:
        st.markdown(f"""
        <div class="glass-card" style="text-align: center;">
            <p class="metric-label">Compound Discipline Score</p>
            <p class="metric-value">{rolling_score}</p>
            <p style="color: #9ca3af; font-size: 0.85rem; margin-top: 5px;">Based on your rolling 7-day logs</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col_comp2:
        if rolling_score >= 80:
            st.markdown(f"""
            <div class="glass-card" style="border-left: 5px solid #10b981;">
                <h4 style="color: #10b981; margin-top:0;">⚡ THE UNSTOPPABLE MACHINE</h4>
                <p style="color: #d1d5db; line-height: 1.5; font-size: 0.9rem;">
                    At a score of <strong>{rolling_score}</strong>, you are consistently choosing delayed gratification. 
                    In 12 months, your habits will compound exponentially. You'll complete over 300 workouts, save 1000+ hours 
                    of screen distraction, and operate in a state of high cognitive alignment. Future You is elite.
                </p>
            </div>
            """, unsafe_allow_html=True)
        elif rolling_score >= 50:
            st.markdown(f"""
            <div class="glass-card" style="border-left: 5px solid #f59e0b;">
                <h4 style="color: #f59e0b; margin-top:0;">🟡 THE STAGNANT MEDIOCRE</h4>
                <p style="color: #d1d5db; line-height: 1.5; font-size: 0.9rem;">
                    At a score of <strong>{rolling_score}</strong>, you are drifting. You work hard on Tuesday but slip up on Thursday. 
                    In 12 months, Future You will look exactly the same as today. You will make minor career or personal changes, 
                    but the underlying habits will keep you stuck in average loops. Push for consistency.
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="glass-card" style="border-left: 5px solid #ef4444;">
                <h4 style="color: #ef4444; margin-top:0;">🚨 COMPROMISE SPIRAL</h4>
                <p style="color: #d1d5db; line-height: 1.5; font-size: 0.9rem;">
                    At a score of <strong>{rolling_score}</strong>, you are in self-sabotage mode. High screen times are hijacking 
                    your dopamine system, and sleep deficits are killing your energy. In 12 months, Future You will have less 
                    ambition, higher fatigue, and major regrets. Turn this around today. Change is mandatory.
                </p>
            </div>
            """, unsafe_allow_html=True)

def render_leaderboard():
    st.markdown("<h2 style='font-weight: 800;'>Discipline Leaderboard</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #9ca3af; margin-bottom: 25px;'>Compare discipline scores and active streaks with other users on this system.</p>", unsafe_allow_html=True)

    leaderboard_data = database.get_leaderboard()

    if not leaderboard_data:
        visuals.render_empty_state("Leaderboard Empty", "No users have completed onboarding yet.", "🏆")
        return

    # Build Beautiful Glass table
    table_rows = ""
    for idx, row in enumerate(leaderboard_data):
        rank = idx + 1
        username = row['username']
        score = row['discipline_score']
        streak = row['current_streak']
        
        # Highlight current user
        is_curr = username == st.session_state.username
        row_style = "background: rgba(139, 92, 246, 0.1); border: 1px solid rgba(139, 92, 246, 0.3);" if is_curr else ""
        username_label = f"✨ {username} (You)" if is_curr else username
        
        badge = "🥇" if rank == 1 else ("🥈" if rank == 2 else ("🥉" if rank == 3 else f"#{rank}"))

        table_rows += f"""
        <tr style="{row_style}">
            <td style="padding: 14px; border-bottom: 1px solid rgba(255,255,255,0.06); font-weight: 700;">{badge}</td>
            <td style="padding: 14px; border-bottom: 1px solid rgba(255,255,255,0.06);">{username_label}</td>
            <td style="padding: 14px; border-bottom: 1px solid rgba(255,255,255,0.06); font-weight: 700; color: #a78bfa;">⚡ {score}/100</td>
            <td style="padding: 14px; border-bottom: 1px solid rgba(255,255,255,0.06);">🔥 {streak} Days</td>
        </tr>
        """

    html = f"""
    <div style="background: rgba(18, 18, 26, 0.55); border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.06); padding: 10px; backdrop-filter: blur(12px);">
        <table style="width: 100%; border-collapse: collapse; text-align: left; color: white;">
            <thead>
                <tr style="color: #9ca3af; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1.2px;">
                    <th style="padding: 14px; border-bottom: 1px solid rgba(255,255,255,0.1);">Rank</th>
                    <th style="padding: 14px; border-bottom: 1px solid rgba(255,255,255,0.1);">Username</th>
                    <th style="padding: 14px; border-bottom: 1px solid rgba(255,255,255,0.1);">Discipline Score</th>
                    <th style="padding: 14px; border-bottom: 1px solid rgba(255,255,255,0.1);">Active Streak</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_profile():
    user_id = st.session_state.user_id
    user = database.get_user_by_id(user_id)
    if not user:
        logout_user()
        st.rerun()

    st.markdown("<h2 style='font-weight: 800;'>Settings & Profile</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #9ca3af; margin-bottom: 25px;'>Fine-tune your targets, manage habits, and update credentials.</p>", unsafe_allow_html=True)

    tab_targets, tab_habits, tab_api, tab_reset = st.tabs(["⚙️ Target Settings", "🛡️ Habit Inventory", "🤖 API Integration", "🚨 Danger Zone"])

    with tab_targets:
        st.markdown("### Update Daily Benchmarks")
        with st.form("targets_form"):
            t_sleep = st.slider("Target Sleep Hours", min_value=4.0, max_value=12.0, value=float(user['target_sleep']), step=0.5)
            t_screen = st.slider("Screen Time Limit (Hours)", min_value=1.0, max_value=12.0, value=float(user['target_screen_time']), step=0.5)
            submit_targets = st.form_submit_button("Save Baselines", type="primary")
            
            if submit_targets:
                database.update_user_targets(user_id, t_sleep, t_screen)
                st.session_state.success_message = "Benchmarks successfully updated."
                st.rerun()

    with tab_habits:
        st.markdown("### Active Habits Checklist")
        habits = database.get_user_habits(user_id)
        
        if not habits:
            st.info("No habits defined yet.")
        else:
            for h in habits:
                label_color = "#34d399" if h['habit_type'] == 'good' else "#f87171"
                type_name = "Good Habit" if h['habit_type'] == 'good' else "Bad Habit"
                
                col_name, col_btn = st.columns([4, 1])
                with col_name:
                    st.markdown(f"""
                    <div style="padding: 10px; background: rgba(255,255,255,0.02); border-radius: 8px; margin-bottom: 5px;">
                        <span style="color: {label_color}; font-weight:700; margin-right: 10px;">[{type_name}]</span>
                        <span>{h['habit_name']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                with col_btn:
                    # Provide deletion button
                    if st.button("Delete", key=f"del_{h['id']}"):
                        database.delete_habit(user_id, h['id'])
                        st.session_state.success_message = f"Deleted habit '{h['habit_name']}'"
                        st.rerun()

        st.markdown("<br>### Add New Habit")
        with st.form("new_habit_form"):
            new_name = st.text_input("Habit Name", placeholder="e.g. Code for 2 hours, Avoid snacking")
            new_type = st.selectbox("Habit Type", ["good", "bad"], format_func=lambda x: "✨ Good / Positive Habit" if x == 'good' else "🛑 Bad / Negate Habit")
            submit_new_habit = st.form_submit_button("Add Habit", type="primary")
            
            if submit_new_habit:
                if not new_name.strip():
                    st.error("Habit name cannot be blank.")
                else:
                    database.add_habit(user_id, new_name, new_type)
                    st.session_state.success_message = f"Successfully added '{new_name}' to inventory."
                    st.rerun()

    with tab_api:
        st.markdown("### Google Gemini Integration")
        st.markdown("<p style='color: #9ca3af; font-size: 0.9rem;'>Provide a Gemini API Key to enable deep, context-aware AI coaching conversations. If not provided, SelfSync falls back to the local rules-based Ares Critique Engine.</p>", unsafe_allow_html=True)
        
        # Display key status
        current_configured = "Configured (Masked)" if st.session_state.gemini_api_key else "Not Configured"
        st.markdown(f"**Current Status:** `{current_configured}`")

        input_api_key = st.text_input("Gemini API Key", value=st.session_state.gemini_api_key, type="password", placeholder="AIzaSy...")
        
        if st.button("Save API Configuration", type="primary"):
            st.session_state.gemini_api_key = input_api_key.strip()
            st.session_state.success_message = "API Key successfully registered in local Session State."
            st.rerun()

    with tab_reset:
        st.markdown("### Reset Data Profile")
        st.markdown("<p style='color: #ef4444;'>Warning: This will delete all your logged entries, historical database records, and habits. This action is irreversible.</p>", unsafe_allow_html=True)
        
        confirm = st.checkbox("I confirm that I want to wipe all records for this account.")
        if st.button("Wipe Profile Data", type="primary"):
            if confirm:
                conn = database.get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM daily_habits WHERE user_id = ?", (user_id,))
                cursor.execute("DELETE FROM daily_logs WHERE user_id = ?", (user_id,))
                cursor.execute("DELETE FROM habits WHERE user_id = ?", (user_id,))
                cursor.execute("UPDATE users SET discipline_score = 0, current_streak = 0 WHERE id = ?", (user_id,))
                conn.commit()
                conn.close()
                st.session_state.success_message = "Your database record has been cleared."
                navigate_to('Dashboard')
                st.rerun()
            else:
                st.error("Please check the confirmation checkbox first.")

# ==========================================
# 5. SIDEBAR NAVIGATION
# ==========================================
def render_sidebar():
    """Renders the custom navigation menu if the user is logged in."""
    if st.session_state.is_authenticated:
        with st.sidebar:
            st.markdown("<h2 style='font-weight: 800; color: #a78bfa;'>SelfSync OS</h2>", unsafe_allow_html=True)
            
            # Fetch user info for custom sidebar header
            user = database.get_user_by_id(st.session_state.user_id)
            if user:
                st.markdown(f"👤 **Spartan:** `{user['username']}`")
                st.markdown(f"⚡ **Discipline:** `{user['discipline_score']}/100`")
                st.markdown(f"🔥 **Streak:** `{user['current_streak']} Days`")
                st.markdown("---")

            pages = {
                'Dashboard': ("📊 Dashboard", 'Dashboard'),
                'Journal': ("📝 Daily Log", 'Journal'),
                'AICoach': ("🤖 AI Coach", 'AICoach'),
                'Analytics': ("📈 Deep Analytics", 'Analytics'),
                'Leaderboard': ("🏆 Leaderboard", 'Leaderboard'),
                'Profile': ("⚙️ Settings", 'Profile')
            }
            
            for key, (label, page) in pages.items():
                is_active = st.session_state.current_page == page
                btn_label = f"✨ {label}" if is_active else label
                st.button(btn_label, on_click=navigate_to, args=(page,), use_container_width=True, key=f"nav_{page}")
            
            st.markdown("---")
            st.button("Logout", on_click=logout_user, type="primary", use_container_width=True)

# ==========================================
# 6. MAIN ROUTER LOGIC
# ==========================================
def main():
    # Force schema check on every rerun to bypass cloud cache issues
    database.init_db()
    
    # Inject Custom UI overrides
    visuals.inject_global_css()

    # Display global success notification if present
    if st.session_state.success_message:
        st.success(st.session_state.success_message)
        # Clear it immediately so it doesn't show again on subsequent reruns
        st.session_state.success_message = None

    # Render sidebar
    render_sidebar()

    # Enforce Authentication Routing
    if not st.session_state.is_authenticated:
        allowed_public_pages = ['Landing', 'Auth']
        if st.session_state.current_page not in allowed_public_pages:
            st.session_state.current_page = 'Landing'

    page = st.session_state.current_page
    
    if page == 'Landing':
        render_landing()
    elif page == 'Auth':
        render_auth()
    elif page == 'Onboarding':
        render_onboarding()
    elif page == 'Dashboard':
        render_dashboard()
    elif page == 'Journal':
        render_journal()
    elif page == 'AICoach':
        render_ai_coach()
    elif page == 'Analytics':
        render_analytics()
    elif page == 'Leaderboard':
        render_leaderboard()
    elif page == 'Profile':
        render_profile()
    else:
        render_landing()

if __name__ == "__main__":
    main()
