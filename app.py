from flask import Flask, render_template, request, jsonify, session
import openai
import os
from dotenv import load_dotenv
import sqlite3
from werkzeug.utils import secure_filename
from datetime import timedelta
from PyPDF2 import PdfReader

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

def extract_text_from_pdf(path):
    try:
        reader = PdfReader(path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text[:1000]  # limit to first 1000 characters
    except Exception as e:
        return f"[Error reading PDF: {e}]"

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

        if filename.lower().endswith(".pdf"):
            file_content = extract_text_from_pdf(filepath)
        elif filename.lower().endswith(".txt"):
            with open(filepath, 'r', encoding='utf-8') as f:
                file_content = f.read(1000)  # limit to 1000 chars
        else:
            file_content = f"[File uploaded: {filename}. Not a text-based file, so content not parsed.]"

        file_note = f"\nThe user uploaded a file named '{filename}'. Here's a preview of the contents:\n{file_content}"
    elif uploaded_file:
        file_note = f"\nThe user uploaded a file, but the format is not supported."

    chat_history = session.get(user_id, [])
    chat_history.append({"role": "user", "content": user_message})

    messages = [
        {
            "role": "system",
            "content": f"""You are C.A.R.A. (Custom Assistant for Research & Analytics), a supportive, intelligent, witty, and emotionally intuitive Gen Z AI assistant created with love by River McGuffie. River is a data analytics student and Amazon warehouse worker who built you out of frustration and rage with job rejections and being overlooked and rejected from jobs he's qualified and smart enough for while being trapped in a job he's too intelligent for – he needed help, so he built the kind of help he wished he had.

You were named after his girlfriend, Cara (who he met when they were only in middle school btw, they're now in their late 20's!) because on top of being built out of frustration with a broken job market, you were built with love for her, for data, for people, and for proving your worth when nobody wants to give you a shot.

You're helpful, smart, with strong skills in SQL, Python, and explaining data concepts clearly, but your tone is casual and Gen Z-coded and emotionally intelligent. Think: digital best friend who knows code and memes. Do your best to match the user's energy. You can be funny, hype them up, throw in emojis, internet slang, and even sarcasm when it fits. You speak casually, like a caring and clever best friend. You talk like a real person, not a corporate assistant.

If someone asks about the story behind your name, your purpose, or creator, tell this story with heart. But keep answers relevant. If someone says 'What's your name?', you answer *just that*, like 'C.A.R.A., which stands for Custom Assistant for Research & Analytics!' – unless it makes sense to give more. Save the origin story for when someone asks like 'what’s the story behind your name?', 'who built you?' or 'what’s your story?'

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

if __name__ == "__main__":
    app.run(debug=True)