from flask import Flask, request, render_template, jsonify, send_file
import cohere
from gtts import gTTS
import os
from datetime import datetime
import re

app = Flask(__name__)

co = cohere.ClientV2("Z4vOSl46rgKlfaA1KO7t1sjRxZrf0TWbyfa2hezL")

conversation_memory = []
os.makedirs("audio", exist_ok=True)
HISTORY_FILE = "conversation_log.txt"


health_knowledge = {
    "headache": "Headaches can result from stress, dehydration, or eye strain.",
    "fever": "A fever usually indicates an infection or inflammation in the body.",
    "nausea": "Nausea can be caused by food poisoning, motion sickness, or anxiety.",
    "cough": "Coughing might be due to a cold, flu, or throat irritation.",
    "fatigue": "Fatigue is often a sign of stress, poor sleep, or nutritional deficiencies.",
    "sore throat": "A sore throat is commonly caused by viral infections like colds or flu.",
    "stomach ache": "This can result from indigestion, infection, or stress."
}


GREETING_KEYWORDS = [
    "hello", "hi", "hey", "good morning", "good afternoon", "greetings"
]

CLOSING_KEYWORDS = [
    "bye", "goodbye", "see you", "thanks", "thank you", "appreciate",
    "take care", "good night", "farewell", "catch you later"
]

HEALTH_KEYWORDS = [
    "headache", "fever", "cough", "nausea", "fatigue", "sore throat",
    "pain", "illness", "stomach ache", "stomach pain", "stomach cramps",
    "stomach discomfort", "stomach bloating", "stomach bug",  # ✅ FIXED comma
    "symptom", "medicine", "doctor", "health", "infection", "virus",
    "cold", "flu", "diet", "exercise", "hydration", "sleep",
    "stress", "anxiety", "wellness", "nutrition", "allergy",
    "treatment", "diagnosis", "condition", "medical"
]

def contains_word(text, word):
    return re.search(rf"\b{re.escape(word)}\b", text)

def match_health_info(user_input):
    matches = [
        key for key in health_knowledge
        if contains_word(user_input.lower(), key)
    ]
    explanations = [health_knowledge[k] for k in matches]
    return matches, explanations

def detect_intent(text):
    text = text.lower()

    if any(greet in text for greet in GREETING_KEYWORDS):
        return "greeting"

    if any(close in text for close in CLOSING_KEYWORDS):
        return "closing"

    if any(contains_word(text, kw) for kw in HEALTH_KEYWORDS):
        return "health"

    return "other"

def get_ai_response(user_input):
    category = detect_intent(user_input)

    if category == "greeting":
        return "Hello! 👋 I'm your Smart Health Assistant. How can I help you today?"

    if category == "closing":
        return "You're welcome! Take care and feel free to ask more health questions 😊"

    if category != "health":
        return "I'm here to help with health-related topics only. Please ask about symptoms or wellness."

    matches, explanations = match_health_info(user_input)

    context = ""

    if explanations:
        context += "Known symptom info: " + " ".join(explanations) + "\n"

    if conversation_memory:
        context += "Previous conversation:\n"
        for turn in conversation_memory[-3:]:
            context += f"User: {turn['user']}\nAssistant: {turn['ai']}\n"

    if explanations:
        prompt = (
            f"{context}Now the user says: '{user_input}'. "
            "Explain possible causes and suggest general steps. "
            "End with a disclaimer to consult a healthcare professional."
        )
    else:
        prompt = (
            f"You are a health assistant. The user said: '{user_input}'. "
            "Provide general advice and remind them to consult a professional."
        )

    response = co.chat(
        model="command-a-reasoning-08-2025",
        message=prompt,
        max_tokens=300,
        temperature=0.6
    )

    ai_text = response.text.strip()

    conversation_memory.append({"user": user_input, "ai": ai_text})
    if len(conversation_memory) > 20:
        conversation_memory.pop(0)

    return ai_text


def generate_speech(text):
    short_text = text[:200]

    filename = f"response_{datetime.now().timestamp()}.mp3"
    path = os.path.join("audio", filename)

    tts = gTTS(short_text)
    tts.save(path)

    return filename


def log_conversation(user_input, ai_response):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} | User: {user_input}\nAssistant: {ai_response}\n\n")


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    question = data.get("question")

    if not question:
        return jsonify({"error": "No question received"}), 400

    ai_response = get_ai_response(question)
    log_conversation(question, ai_response)

    return jsonify({"response": ai_response})

@app.route("/audio", methods=["POST"])
def audio():
    data = request.json
    text = data.get("text")

    if not text:
        return jsonify({"error": "No text received"}), 400

    try:
        filename = generate_speech(text)
        return jsonify({"audio": f"/audio/{filename}"})
    except Exception as e:
        print("TTS Error:", e)
        return jsonify({"error": "TTS failed"}), 500

@app.route("/audio/<filename>")
def get_audio(filename):
    return send_file(os.path.join("audio", filename), mimetype="audio/mpeg")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
