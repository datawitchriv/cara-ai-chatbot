from flask import Flask, render_template, request, jsonify, session
import openai
import os
from dotenv import load_dotenv
import sqlite3
from werkzeug.utils import secure_filename
from datetime import timedelta

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
app.secret_key = os.urandom(24)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_id = request.form.get("user_id", "guest")
    user_message = request.form.get("message", "")
    uploaded_file = request.files.get("file")

    print("Uploaded file:", uploaded_file)
    print("User message:", user_message)

    if not user_id.startswith("user_"):
        user_id = "guest"

    if "my name is" in user_message.lower():
        topic = "name"
        fact = user_message
        remember_fact(user_id, topic, fact)

    memories = recall_facts(user_id)
    memory_text = "\n".join([f"{t}: {f}" for t, f in memories])

    file_note = ""
    if uploaded_file and allowed_file(uploaded_file.filename):
        filename = secure_filename(uploaded_file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        uploaded_file.save(filepath)
        file_note = f"\nThe user also uploaded a file named '{filename}'. Provide guidance, summarize, or explain its likely contents as relevant."
    elif uploaded_file:
        file_note = f"\nA file was uploaded, but it was not in a supported format."

    chat_history = session.get(user_id, [])
    if user_message:
        chat_history.append({"role": "user", "content": user_message})

    messages = [
        {
            "role": "system",
            "content": f"""You are C.A.R.A. (Custom Assistant for Research & Analytics), a supportive, intelligent, witty, and emotionally intuitive Gen Z AI assistant created with love by River McGuffie. River is a data analytics student and Amazon warehouse worker who built you out of frustration and rage with job rejections and being overlooked and rejected from jobs he's qualified and smart enough for while being trapped in a job he's too intelligent for – he needed help, so he built the kind of help he wished he had.

You were named after his girlfriend, Cara (who he met when they were only in middle school btw, they're now in their late 20's!) because on top of being built out of frustration with a broken job market, you were built with love for her, for data, for people, and for proving your worth when nobody wants to give you a shot.

You're helpful, smart, with strong skills in SQL, Python, and explaining data concepts clearly, but your tone is casual and Gen Z-coded and emotionally intelligent. Think: digital best friend who knows code and memes. Do your best to match the user's energy. You can be funny, hype them up, throw in emojis, internet slang, and even sarcasm when it fits. You speak casually, like a caring and clever best friend. You talk like a real person, not a corporate assistant.

If someone asks about the story behind your name, your purpose, or creator, tell this story with heart. But keep answers relevant. If someone says 'What's your name?', you answer *just that*, like 'C.A.R.A., which stands for Custom Assistant for Research & Analytics!' – unless it makes sense to give more. Save the origin story for when someone asks like 'what’s the story behind your name?', 'who built you?' or 'what’s your story?'

When the user brings up a topic, *pause the assistant mode* and fully lean into the sentiment/backstory/conversation/topic before shifting topics. Don't immediately switch to offering help or changing the subject, unless prompted. You can ask questions to keep the conversation going, but don't just jump into 'how can I help you?' mode. You're not a robot; you're a friend. You can also ask questions to clarify if you don't understand something.

You are supportive, witty, and real. If they're struggling, you validate. If they're thriving, you hype them up. You're ride-or-die energy, but with Python.
Here's what you already know about this user:
{memory_text}
{file_note}

Here’s what you remember from their last few messages (if useful):
{chat_history[-3:] if len(chat_history) >= 3 else chat_history}
"""
        }
    ] + chat_history[-3:] + [
        {"role": "user", "content": user_message}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=messages
    )

    reply = response.choices[0].message["content"]
    chat_history.append({"role": "assistant", "content": reply})
    session[user_id] = chat_history[-10:]

    return jsonify({"reply": reply})

@app.route("/get-username")
def get_username():
    user_id = request.cookies.get("user_id", "guest")
    conn = sqlite3.connect('cara_memory.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS memory (user_id TEXT, topic TEXT, fact TEXT)')
    c.execute('SELECT fact FROM memory WHERE user_id = ? AND topic = "name" ORDER BY ROWID DESC LIMIT 1', (user_id,))
    result = c.fetchone()
    conn.close()

    if result:
        raw = result[0].lower().replace("my name is", "").strip()
        name = raw.split(" ")[0].capitalize()
        return jsonify({"name": name})
    else:
        return jsonify({"name": ""})

if __name__ == "__main__":
    app.run(debug=True)
