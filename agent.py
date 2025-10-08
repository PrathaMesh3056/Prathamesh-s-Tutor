import os
import json
import requests
from dotenv import load_dotenv

# --- Firebase Imports ---
import firebase_admin
from firebase_admin import credentials, firestore

# --- Gemini Imports ---
import google.generativeai as genai

# --- 1. SETUP ---
print("--- SCRIPT START ---")
load_dotenv()

# --- Initialize APIs (Gemini, Telegram, Firebase) ---
# NOTE: This section contains robust initialization and error checking.
try:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')
    print("OK: Gemini configured.")

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip().strip('"')
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip().strip('"')
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        raise ValueError("Telegram secrets are missing.")
    print("OK: Telegram secrets loaded.")

    db = None
    FIREBASE_CREDS_JSON = os.getenv("FIREBASE_CREDS_JSON")
    if not FIREBASE_CREDS_JSON:
        raise ValueError("FIREBASE_CREDS_JSON secret not found!")
    
    creds_dict = json.loads(FIREBASE_CREDS_JSON)
    cred = credentials.Certificate(creds_dict)
    
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    print("OK: Firebase initialized.")
except Exception as e:
    print(f"FATAL ERROR during initialization: {e}")
    exit()

LESSONS_COLLECTION = 'lessons'

# --- 2. DATABASE FUNCTIONS ---

def find_next_lesson_from_db():
    print("-> Querying for next lesson...")
    try:
        query = db.collection(LESSONS_COLLECTION).where('status', '==', 'pending').order_by('day').limit(1)
        results = query.stream()
        for doc in results:
            print(f"  > Found: Day {doc.to_dict().get('day')}")
            return doc.to_dict()
        print("  > No pending lessons found.")
        return None
    except Exception as e:
        print(f"  > ERROR during Firestore query: {e}")
        return None

def update_lesson_status_in_db(lesson_data):
    day = lesson_data.get('day')
    doc_id = str(day)
    print(f"-> Attempting to update status for Day {day}...")
    try:
        updated_lesson = lesson_data.copy()
        updated_lesson['status'] = 'complete'
        doc_ref = db.collection(LESSONS_COLLECTION).document(doc_id)
        doc_ref.set(updated_lesson)
        print(f"  > Write command sent for Day {day}.")
        
        # Verification Step
        updated_doc = doc_ref.get()
        if updated_doc.exists and updated_doc.to_dict().get('status') == 'complete':
            print(f"  > VERIFICATION SUCCESS: Day {day} is now 'complete'.")
            return True
        else:
            print(f"  > VERIFICATION FAILED: Write was not successful.")
            return False
    except Exception as e:
        print(f"  > CRITICAL ERROR during update: {e}")
        return False

# --- 3. CORE LOGIC FUNCTIONS ---

def generate_simple_lesson_content(topic):
    """Generates a simple text-only lesson."""
    print(f"-> Generating simple lesson for: {topic}...")
    prompt = f"""
    Explain the following topic in a simple way for a beginner.
    Topic: "{topic}"
    Use very simple Markdown like *bold* or _italic_. Do not include any other complex formatting or code blocks.
    """
    try:
        response = model.generate_content(prompt)
        print("  > Lesson content generated.")
        return response.text
    except Exception as e:
        print(f"  > ERROR generating content: {e}")
        return None

def send_telegram_message(text_message):
    """Sends a text-only message to Telegram."""
    print("-> Sending message to Telegram...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text_message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("  > Message sent successfully!")
        return True
    except requests.exceptions.RequestException as e:
        # Print the detailed error from Telegram
        print(f"  > FAILED to send message: {e}")
        print(f"  > Telegram Response: {response.text}")
        return False

# --- 4. MAIN EXECUTION ---
if __name__ == "__main__":
    print("\n--- Main execution started ---")
    next_lesson = find_next_lesson_from_db()

    if next_lesson:
        topic = next_lesson.get('topic')
        
        # Generate simple text content only
        lesson_content = generate_simple_lesson_content(topic)
        
        if lesson_content:
            # Send the text and if successful, update the database
            if send_telegram_message(lesson_content):
                update_lesson_status_in_db(next_lesson)
    else:
        print("  > No pending lessons to process.")
        send_telegram_message("🎉 You've completed the entire curriculum! Congratulations! 🎉")
        
    print("--- SCRIPT END ---")

