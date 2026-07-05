import os
import pandas as pd
import random
from datetime import date
import database

# Try importing generative AI, catch error if import fails during setup
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# ==========================================
# 1. BRUTAL RULE-BASED CRITIQUE ENGINE
# ==========================================
def get_rule_based_critique(user_id, log_date_str=None):
    """
    Analyzes user logs and habits to generate a customized, brutal, rule-based response.
    Used when Gemini API Key is missing or invalid.
    """
    if log_date_str is None:
        log_date_str = str(date.today())

    user = database.get_user_by_id(user_id)
    if not user:
        return "User not found. Stop trying to break my code and register."

    target_sleep = user['target_sleep']
    target_screen_time = user['target_screen_time']

    log = database.get_daily_log(user_id, log_date_str)
    habits = database.get_daily_habits_status(user_id, log_date_str)

    if not log:
        return (
            "🔥 **NO DATA LOGGED FOR TODAY**\n\n"
            "You haven't logged anything for today yet. Are you hiding from your own metrics? "
            "Go to the **Daily Log** page and enter your stats. Delaying is just a soft version of quitting. "
            "I'm waiting."
        )

    sleep = log['sleep_hours']
    screen = log['screen_time_hours']
    mood = log['mood_score']
    productivity = log['productivity_score']
    score = log['discipline_score']
    notes = log['notes']

    critique = []

    # 1. Score-based overall assessment
    if score >= 90:
        critique.append(
            f"### Discipline Score: {score}/100 (S-Tier)\n"
            "Outstanding work. You operated like a machine today. You met your goals, hit your habits, and did what needed to be done. "
            "Do not let this success make you soft. The moment you start feeling comfortable is the moment you begin to slide. "
            "Sleep well, wake up, and do it again."
        )
    elif score >= 75:
        critique.append(
            f"### Discipline Score: {score}/100 (A-Tier)\n"
            "Solid day. You did the majority of what you planned. But let's look at the gaps. "
            "You are doing enough to stay above average, but 'decent' is the enemy of greatness. "
            "Identify the single habit or metric that dragged you down today and crush it tomorrow."
        )
    elif score >= 50:
        critique.append(
            f"### Discipline Score: {score}/100 (C-Tier - Mediocre)\n"
            "A mediocre, middle-of-the-road performance. You did some good things, but you compromised on others. "
            "You have one foot in discipline and one foot in comfort. That is a dangerous place to stand. "
            "Tomorrow, choose a side: either commit to the forge or accept average."
        )
    else:
        critique.append(
            f"### Discipline Score: {score}/100 (FAIL)\n"
            "A complete disaster. You let your excuses win today. You are actively self-sabotaging. "
            "Look at your stats: they show someone who chose comfort, scrolling, or laziness over their goals. "
            "Stop looking for motivation. Clean up your environment, look yourself in the mirror, and show up tomorrow."
        )

    # 2. Specific metrics breakdown
    critique.append("\n**METRIC BREAKDOWN:**")

    # Sleep
    sleep_diff = sleep - target_sleep
    if abs(sleep_diff) <= 1.0:
        critique.append(f"🟢 **Sleep ({sleep} hrs):** Right in the zone. You gave your body the recovery it actually needed. Good.")
    elif sleep_diff < -1.0:
        critique.append(
            f"🔴 **Sleep ({sleep} hrs vs Target {target_sleep} hrs):** Sleep deprivation is a debt that always collects. "
            "You are trading cognitive function and focus for extra waking hours of low-quality activity. Go to bed earlier."
        )
    else:
        critique.append(
            f"🟡 **Sleep ({sleep} hrs vs Target {target_sleep} hrs):** You over-slept. Spending excessive time in bed is just "
            "procrastination under a warm blanket. Wake up on your first alarm."
        )

    # Screen Time
    if screen <= target_screen_time:
        critique.append(f"🟢 **Screen Time ({screen} hrs):** Below your {target_screen_time}h limit. You protected your attention from the dopamine loops. Keep this shield up.")
    else:
        overage = screen - target_screen_time
        critique.append(
            f"🔴 **Screen Time ({screen} hrs vs Limit {target_screen_time} hrs):** You went {overage:.1f} hours over your limit. "
            "You literally paid tech billionaires with the currency of your lifetime attention. What did you get in return? "
            "Junk dopamine. Install a screen blocker or throw your phone in another room."
        )

    # Habits
    good_habits = [h for h in habits if h['habit_type'] == 'good']
    bad_habits = [h for h in habits if h['habit_type'] == 'bad']

    if good_habits:
        completed_good = [h['habit_name'] for h in good_habits if h['completed'] == 1]
        missed_good = [h['habit_name'] for h in good_habits if h['completed'] == 0]
        
        if missed_good:
            critique.append(f"❌ **Missed Good Habits:** {', '.join(missed_good)}. You couldn't spare a few minutes to build your character. Weak.")
        else:
            critique.append("✅ **Good Habits:** 100% completed. Excellent execution on your positive routines.")

    if bad_habits:
        triggered_bad = [h['habit_name'] for h in bad_habits if h['completed'] == 1]
        
        if triggered_bad:
            critique.append(f"⚠️ **Failed Bad Habits:** You gave in to: {', '.join(triggered_bad)}. Your impulses are still in the driver's seat. Reclaim control.")
        else:
            critique.append("🛡️ **Bad Habits:** 100% avoided. You successfully resisted temptation today. Respect.")

    # 3. Closing remark
    closing_remarks = [
        "No excuses. Tomorrow is a clean slate. Attack it.",
        "Your future self is watching. Don't disappoint them again.",
        "Discipline is doing what needs to be done, especially when you don't feel like it.",
        "Consistency is the only bridge between goals and accomplishments. Walk it.",
        "You know what you need to do. Stop talking and start executing."
    ]
    critique.append(f"\n*Coach Ares: \"{random.choice(closing_remarks)}\"*")

    return "\n\n".join(critique)

# ==========================================
# 2. GEMINI COACH INTEGRATION
# ==========================================
def chat_with_coach(api_key, user_id, user_message, chat_history=[]):
    """
    Sends the user message, context (daily metrics, habit rates, recent history), 
    and custom system prompt to Gemini, returning the coach response.
    """
    # Fallback if no API key is configured or import failed
    if not api_key or not GENAI_AVAILABLE:
        # If the user asks a general question, return a simulated brutal response or the rule-based critique
        if "analyze" in user_message.lower() or "today" in user_message.lower() or "log" in user_message.lower():
            return get_rule_based_critique(user_id)
        
        # General response mapping for other queries
        responses = [
            "I'm running in offline mode. If you want a real conversational analysis, put your Gemini API key in the Profile/Settings page. In the meantime, look at your Dashboard. Your numbers don't lie.",
            "You're chatting, but are you doing? Stop trying to negotiate with me in offline mode. Go log your habits and keep your screen time below limit.",
            "Excuses. If you want my full AI intelligence, configure your Gemini API key in settings. Otherwise, read this: sleep on time, avoid trash foods, put down your phone, and stop crying.",
            "I don't care about your stories. I care about your metrics. If you want a detailed conversation, configure Gemini. If not, go do 20 pushups and start working."
        ]
        return random.choice(responses)

    try:
        # Configure Gemini Client
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-pro")

        # Gather user context for the model
        user = database.get_user_by_id(user_id)
        habits = database.get_user_habits(user_id)
        logs_df = database.get_user_logs_df(user_id, days=7)

        # Build detailed prompt instructions
        system_instruction = (
            "You are 'Ares', a brutal, zero-excuses, tough-love discipline coach for a productivity tracker app called SelfSync.\n"
            "Your personality is direct, raw, and highly motivating. You do not tolerate rationalizations, victim mentalities, or laziness.\n"
            "Your goal is to look at the user's data and call them out on their failures (screen time overages, missed habits, poor sleep) "
            "while acknowledging high performance with firm, professional respect. Never be overly soft, flowery, or standard corporate polite.\n\n"
            f"USER SETTINGS:\n"
            f"- Username: {user['username']}\n"
            f"- Current Discipline Streak: {user['current_streak']} Days\n"
            f"- Sleep Goal: {user['target_sleep']} hours\n"
            f"- Screen Time Limit: {user['target_screen_time']} hours\n\n"
        )

        if not logs_df.empty:
            system_instruction += "RECENT HISTORY (Last 7 Days):\n"
            for _, row in logs_df.iterrows():
                dt_str = row['log_date'].strftime('%Y-%m-%d')
                system_instruction += (
                    f"- {dt_str}: Sleep: {row['sleep_hours']}h (Goal: {user['target_sleep']}h), "
                    f"Screen Time: {row['screen_time_hours']}h (Limit: {user['target_screen_time']}h), "
                    f"Mood: {row['mood_score']}/10, Productivity: {row['productivity_score']}/10, "
                    f"Discipline Score: {row['discipline_score']}/100, Notes: '{row['notes']}'\n"
                )
        else:
            system_instruction += "RECENT HISTORY: No daily logs recorded yet. The user is a slacker who hasn't even filled out their log.\n"

        system_instruction += (
            "\nUSER HABITS DEFINED:\n"
            + "\n".join([f"- {h['habit_name']} ({h['habit_type']} habit)" for h in habits])
            + "\n\nINSTRUCTIONS FOR RESPONSE:\n"
            "1. Respond directly to the user's latest query, but ALWAYS tie it back to their metrics and habits.\n"
            "2. Keep your answer highly engaging, punchy, and under 3 short paragraphs.\n"
            "3. If they are failing their goals, show them the cold reality. If they are winning, tell them to maintain it and raise the stakes.\n"
            "4. NEVER say things like 'I understand' or 'It's okay to have bad days'. It is not okay. Remind them of the cost of compromise.\n"
        )

        # Build message conversation context
        prompt = system_instruction + "\nCONVERSATION HISTORY:\n"
        for sender, msg in chat_history[-6:]:  # Keep last 6 messages
            prompt += f"{sender}: {msg}\n"
        
        prompt += f"USER: {user_message}\nCOACH ARES:"

        # Generate response
        response = model.generate_content(prompt)
        return response.text

    except Exception:
        return get_rule_based_critique(user_id)
