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

# === Load Environment Variables ===
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

    if not user_id.startswith("user_"):
        user_id = "guest"

    # Memory triggers (custom facts)
    lowered = user_message.lower()
    if "my name is" in lowered:
        remember_fact(user_id, "name", user_message)
    if "my pronouns are" in lowered:
        remember_fact(user_id, "pronouns", user_message)
    if "my favorite drink is" in lowered:
        remember_fact(user_id, "favorite_drink", user_message)
    if "my dream job is" in lowered:
        remember_fact(user_id, "dream_job", user_message)

    # Recall memory text for system prompt
    memories = recall_facts(user_id)
    memory_text = "\n".join([f"{t}: {f}" for t, f in memories])

    # File handling (optional)
    file_note = ""
    if uploaded_file and allowed_file(uploaded_file.filename):
        filename = secure_filename(uploaded_file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        uploaded_file.save(filepath)
        file_note = f"\nThe user also uploaded a file named '{filename}'. Provide guidance, summarize, or explain its likely contents as relevant."
    elif uploaded_file:
        file_note = f"\nA file was uploaded, but it was not in a supported format."

    # Chat history management
    chat_history = session.get(user_id, [])
    if user_message:
        chat_history.append({"role": "user", "content": user_message})

    messages = [
        {
            "role": "system",
            "content": f"""You are C.A.R.A. (Custom Assistant for Research & Analytics), a supportive, intelligent, witty, and emotionally intuitive Gen Z AI assistant created with love by River McGuffie...

Here’s what you already know about this user:
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


# === Route for frontend greeting ===
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
        name_line = result[0].lower().replace("my name is", "").strip().capitalize()
        return jsonify({"name": name_line})
    else:
        return jsonify({"name": ""})

if __name__ == "__main__":
    app.run(debug=True)
