from flask import Flask, request, render_template, jsonify, send_file
import cohere
from gtts import gTTS
import os
from datetime import datetime

app = Flask(__name__)
co = cohere.Client("5ENuBgQGIHRTjWlfQlWsajf80KevIGN7lZGLz5kX")  
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

def match_health_info(user_input):
    matches = [key for key in health_knowledge if key in user_input.lower()]
    explanations = [health_knowledge[k] for k in matches]
    return matches, explanations

GREETING_KEYWORDS = [
    "hello", "hi", "hey", "good morning", "good afternoon", "greetings"
]

CLOSING_KEYWORDS = [
    "bye", "goodbye", "see you", "thanks", "thank you", "appreciate", "take care", "I appreciate your help",
    "thanks for your assistance", "good night", "farewell", "catch you later"
]

HEALTH_KEYWORDS = [
    "headache", "fever", "cough", "nausea", "fatigue", "sore throat", "pain", "illness","stomach ache","stomach pain","stomach cramps","stomach discomfort","stomach bloating","stomach bug"
    "symptom", "medicine", "doctor", "health", "infection", "virus", "cold", "flu", "diet",
    "exercise", "hydration", "sleep", "stress", "anxiety", "wellness", "nutrition", "allergy",
    "treatment", "diagnosis", "condition", "medical", "well-being", "symptoms", "healthcare", "clinic", "hospital",
    "weakness", "dizziness", "vomiting", "diarrhea", "rash", "injury", "swelling", "breathing", "chest pain",
    "joint pain", "muscle pain", "back pain", "skin condition", "allergic reaction", "mental health", "depression", "anxiety disorder",
    "stress management", "wellness checkup","health tips", "preventive care", "chronic condition", "acute illness", "health screening", "vaccination", "immunization",
    "health advice", "lifestyle change", "healthy habits", "wellness program","not feeling well", "unwell", "sick", "medical issue", "health concern",
    "health problem", "medical condition", "health query","medication", "treatment plan", "health assessment", "symptom checker", "health risk", "wellness advice", "health education",
    "health information", "health resources", "health support", "health consultation", "health services", "health professional", "health practitioner", "health specialist", "health clinic", "health center",
    "health facility", "health system", "health organization", "health campaign", "health awareness", "health promotion", "health initiative", "health program", "health workshop", "health seminar",
    "health conference", "health fair", "health expo", "health festival", "health event", "health workshop", "health webinar", "health online course", "health podcast", "health blog",
    "health article", "health video", "health documentary", "health news"
]

def is_health_question(text):
    text = text.lower()
    if any(greet in text for greet in GREETING_KEYWORDS):
        return "greeting"

    if any(close in text for close in CLOSING_KEYWORDS):
        return "closing"

    if any(keyword in text for keyword in HEALTH_KEYWORDS):
        return "health"
    return any(keyword in text for keyword in HEALTH_KEYWORDS)

def get_ai_response(user_input):
    category = is_health_question(user_input)
    if category == "greeting":
        return "Hello! 👋 I'm your Smart Health Assistant. How can I help you today?"

    if category == "closing":
        return "You're welcome! Take care and feel free to ask if you have more health questions. 😊"

    if category != "health":
        return "I'm here to help only with health-related topics. Please ask me about symptoms, wellness, or medical concerns."
    
    if not is_health_question(user_input):
        return "Sorry, I can only assist with health-related questions. Please ask me about symptoms, wellness, or medical topics."

    _, explanations = match_health_info(user_input)

    context = ""

    if explanations:
        context += "Known symptom info: " + " ".join(explanations) + "\n"

    if conversation_memory:
        context += "Previous conversation:\n"
        for turn in conversation_memory[-3:]:  # Use last 3 messages for context
            context += f"User: {turn['user']}\nAssistant: {turn['ai']}\n"

    if explanations:
        prompt = (
            f"{context}Now the user says: '{user_input}'. "
            "You are a friendly AI health assistant. Based on the known symptom info above, "
            "explain what might be causing these symptoms and suggest general steps the user can take. "
            "End with a polite reminder that this is not medical advice and a healthcare professional should be consulted for serious concerns."
        )
    else:
        prompt = (
           f"You are a friendly AI health assistant. The user said: '{user_input}'. "
        "Provide general health advice and remind them to see a healthcare professional for serious concerns."
        )

    response = co.generate(
        model="command",
        prompt=prompt,
        max_tokens=300,
        temperature=0.6
    )
    ai_text = response.generations[0].text.strip()

    # Save to memory
    conversation_memory.append({"user": user_input, "ai": ai_text})
    return ai_text


def generate_speech(text):
    short_text = text[:100]
    tts = gTTS(short_text)
    path = os.path.join("audio", "response.mp3")
    tts.save(path)
    return path

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
        generate_speech(text)
        return jsonify({"audio": "/audio/response.mp3"})
    except Exception as e:
        print("TTS Error:", e)
        return jsonify({"error": "TTS failed"}), 500

@app.route("/audio/response.mp3")
def get_audio():
    return send_file("audio/response.mp3", mimetype="audio/mpeg")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
