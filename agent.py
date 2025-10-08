import os
import json
import requests
import re
import base64
from dotenv import load_dotenv

# --- Firebase Imports ---
import firebase_admin
from firebase_admin import credentials, firestore

# --- Gemini Imports ---
import google.generativeai as genai

# --- 1. SETUP: LOAD SECRETS and CONFIGURE APIS ---
print("--- SCRIPT START ---")
load_dotenv()

# Load and configure Google Gemini API
try:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in secrets!")
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash') # Corrected to a valid model name
    print("OK: Gemini API configured.")
except Exception as e:
    print(f"FATAL ERROR configuring Gemini: {e}")
    exit()

# Load and clean Telegram secrets
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip().strip('"')
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip().strip('"')
if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
    print("FATAL ERROR: Telegram secrets not found or empty!")
    exit()
else:
    print("OK: Telegram secrets loaded.")

# Load and initialize Firebase
db = None
try:
    FIREBASE_CREDS_JSON = os.getenv("FIREBASE_CREDS_JSON")
    if not FIREBASE_CREDS_JSON:
        raise ValueError("FIREBASE_CREDS_JSON secret not found!")
    
    creds_dict = json.loads(FIREBASE_CREDS_JSON)
    cred = credentials.Certificate(creds_dict)
    
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    print("OK: Firebase initialized and Firestore client created successfully.")
except Exception as e:
    print(f"FATAL ERROR initializing Firebase: {e}")
    exit()

LESSONS_COLLECTION = 'lessons'

# --- 2. DATABASE FUNCTIONS ---

def find_next_lesson_from_db():
    """Finds the first lesson with status 'pending' from Firestore, ordered by day."""
    print("-> Querying Firestore for the next pending lesson...")
    try:
        lessons_ref = db.collection(LESSONS_COLLECTION)
        query = lessons_ref.where('status', '==', 'pending').order_by('day').limit(1)
        results = query.stream()
        for lesson_doc in results:
            print(f"  > Found pending lesson: Day {lesson_doc.to_dict().get('day')}")
            return lesson_doc.to_dict()
        print("  > No pending lessons found.")
        return None
    except Exception as e:
        print(f"  > ERROR during Firestore query: {e}")
        return None

def update_lesson_status_in_db(lesson_data):
    """Overwrites the lesson document in Firestore with an updated status."""
    day = lesson_data.get('day')
    doc_id = str(day)
    print(f"-> Attempting to update status for Day {day} (Document ID: {doc_id})...")
    try:
        updated_lesson = lesson_data.copy()
        updated_lesson['status'] = 'complete'
        doc_ref = db.collection(LESSONS_COLLECTION).document(doc_id)
        doc_ref.set(updated_lesson)
        
        # --- VERIFICATION STEP ---
        print(f"  > Verifying update for Day {day}...")
        updated_doc = doc_ref.get()
        if updated_doc.exists and updated_doc.to_dict().get('status') == 'complete':
            print(f"  > VERIFICATION SUCCESS: Day {day} is now 'complete' in Firestore.")
            return True
        else:
            print(f"  > VERIFICATION FAILED: Status is still 'pending' after write operation.")
            return False
    except Exception as e:
        print(f"  > CRITICAL ERROR during Firestore update: {e}")
        return False

# --- 3. CORE LOGIC FUNCTIONS ---

def generate_lesson_content(topic):
    """Generates the educational content for a given topic."""
    print(f"-> Generating lesson for topic: {topic}...")
    # This prompt no longer asks for a Mermaid diagram.
    prompt = f"""
    You are an expert AI and Machine Learning tutor named 'Synapse'.
    Your goal is to explain complex topics in the simplest way possible for a Telegram message.

    Today's topic is: "{topic}"

    Please generate today's lesson by following this structure STRICTLY:

    1.  **Simple Analogy:** Start with a simple, real-world analogy.
    2.  **Clear Explanation:** Give a concise, easy-to-read explanation.
    3.  **Practical Example:** Provide a short, well-commented Python code snippet.
    4.  **Key Takeaway:** Summarize the most important point in one sentence.

    Use simple Markdown for formatting (*bold*, _italic_, `code`). Do not use any other complex formatting.
    """
    try:
        response = model.generate_content(prompt)
        print("  > Lesson content generated.")
        return response.text
    except Exception as e:
        print(f"  > ERROR generating content: {e}")
        return None

def send_telegram_message(text_message):
    """
    Sends a text message to Telegram as plain text to avoid formatting errors.
    """
    print("-> Sending message to Telegram as plain text...")
    text_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # Sending as plain text by not including the 'parse_mode' parameter.
    plain_text_payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text_message}
    try:
        response = requests.post(text_url, json=plain_text_payload, timeout=10)
        response.raise_for_status()
        print("  > Text message sent successfully as plain text!")
    except requests.exceptions.RequestException as final_e:
        print(f"  > FAILED to send as plain text: {final_e}")
        if response:
            print(f"  > Telegram Response: {response.text}")
        return False

    # The return True is critical for the main logic to proceed.
    return True

# --- 4. MAIN EXECUTION (CORRECTED) ---
if __name__ == "__main__":
    print("\n--- Main execution started ---")
    next_lesson = find_next_lesson_from_db()

    if next_lesson:
        topic = next_lesson.get('topic')
        # We now expect only the text content, no diagram info.
        lesson_content = generate_lesson_content(topic)
        
        if lesson_content:
            # The send function now only takes one argument.
            if send_telegram_message(lesson_content):
                update_lesson_status_in_db(next_lesson)
    else:
        print("-> No pending lessons to process.")
        # Only send the completion message if there are truly no pending lessons
        if find_next_lesson_from_db() is None:
             send_telegram_message("🎉 You've completed the entire curriculum! Congratulations! 🎉")
        
    print("--- SCRIPT END ---")

    

