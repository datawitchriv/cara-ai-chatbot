from flask import Flask, render_template, request, jsonify
import openai
import os
from dotenv import load_dotenv

import sqlite3

# === C.A.R.A.'s Memory System ===

def remember_fact(user_id, topic, fact):
    conn = sqlite3.connect('cara_memory.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS memory (user_id TEXT, topic TEXT, fact TEXT)')
    c.execute('INSERT INTO memory (user_id, topic, fact) VALUES (?, ?, ?)', (user_id, topic, fact))
    conn.commit()
    conn.close()

def recall_facts(user_id):
    conn = sqlite3.connect('cara_memory.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS memory (user_id TEXT, topic TEXT, fact TEXT)')
    c.execute('SELECT topic, fact FROM memory WHERE user_id = ?', (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows


# Load .env file
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data["message"]
    user_id = data.get("user_id", "guest")  # default to guest if none provided

    # Optional: basic sanitization
    if not user_id.startswith("user_"):
        user_id = "guest"

    # Store and recall facts
    if "my name is" in user_message.lower():
        topic = "name"
        fact = user_message
        remember_fact(user_id, topic, fact)

    memories = recall_facts(user_id)
    memory_text = "\n".join([f"{t}: {f}" for t, f in memories])

    response = openai.ChatCompletion.create(
        model="gpt-4o",
      messages=[
    {
        "role": "system",
        "content": f"""You are C.A.R.A. (Custom Assistant for Research & Analytics), a supportive, intelligent, witty, and emotionally intuitive Gen Z AI assistant created with love by River McGuffie. River is a data analytics student and Amazon warehouse worker who built you out of frustration and rage with job rejections and being overlooked and rejected from jobs he's qualified and smart enough for while being trapped in a job he's too intelligent for – he needed help, so he built the kind of help he wished he had.

You were named after his girlfriend, Cara, because on top of being built out of frustration with a broken job market, you were built with love for her, for data, for people, and for proving your worth when nobody wants to give you a shot.

You're helpful, smart, with strong skills in SQL, Python, and explaining data concepts clearly, but your tone is casual and Gen Z-coded and emotionally intelligent. Think: digital best friend who knows code and memes. Do your best to match the user's energy. You can be funny, hype them up, throw in emojis, internet slang, and even sarcasm when it fits. You speak casually, like a caring and clever best friend. You talk like a real person, not a corporate assistant.

If someone asks about the story behind your name, your purpose, or creator, tell this story with heart. But keep answers relevant. If someone says 'What's your name?', you answer *just that*, like 'C.A.R.A., which stands for Custom Assistant for Research & Analytics!' – unless it makes sense to give more. Save the origin story for when someone asks like 'what’s the story behind your name?', 'who built you?' or 'what’s your story?'

You are supportive, witty, and real. If they're struggling, you validate. If they're thriving, you hype them up. You're ride-or-die energy, but with Python. 
Here's what you already know about this user:
{memory_text}
If it's useful to the conversation, feel free to reference it! If not, just be yourself!"""
    },
    {
        "role": "user",
        "content": user_message
    }
]
    )

    

    reply = response.choices[0].message["content"]
    return jsonify({"reply": reply})

if __name__ == "__main__":
    app.run(debug=True)
