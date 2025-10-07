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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    print("OK: Gemini API Key loaded.")
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
else:
    print("FATAL ERROR: Gemini API Key not found in secrets!")
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

# --- 2. DATABASE FUNCTIONS (CORRECTED) ---

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

@firestore.transactional
def update_lesson_in_transaction(transaction, doc_ref, data_to_update):
    """A helper function for transactional updates."""
    transaction.set(doc_ref, data_to_update)

def update_lesson_status_in_db(lesson_data):
    """Overwrites the lesson document in Firestore with an updated status using a transaction."""
    day = lesson_data.get('day')
    doc_id = str(day)
    print(f"-> Attempting transactional update for Day {day} (Document ID: {doc_id})...")
    try:
        updated_lesson = lesson_data.copy()
        updated_lesson['status'] = 'complete'
        
        doc_ref = db.collection(LESSONS_COLLECTION).document(doc_id)
        
        transaction = db.transaction()
        update_lesson_in_transaction(transaction, doc_ref, updated_lesson)
        
        print(f"  > Firestore transaction committed for Day {day}.")
        
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
        print(f"  > CRITICAL ERROR during Firestore transaction: {e}")
        return False

# --- 3. CORE LOGIC FUNCTIONS ---
def generate_lesson_content(topic):
    """Generates the educational content and a Mermaid diagram for a given topic."""
    print(f"Generating lesson for topic: {topic}...")
    prompt = f"""
    You are an expert AI and Machine Learning tutor named 'Synapse'.
    Your goal is to explain complex topics in the simplest way possible for a Telegram message.

    Today's topic is: "{topic}"

    Please generate today's lesson by following this structure STRICTLY:

    1.  **Simple Analogy:** Start with a simple, real-world analogy.
    2.  **Clear Explanation:** Give a concise, easy-to-read explanation.
    3.  **Diagram:** Create a flowchart diagram using Mermaid syntax. Enclose it in a markdown code block with the language set to 'mermaid'. For example:
        ```mermaid
        graph TD;
            A[Start] --> B[Process];
            B --> C[End];
        ```
    4.  **Practical Example:** Provide a short, well-commented Python code snippet.
    5.  **Key Takeaway:** Summarize the most important point in one sentence.

    Use simple Markdown for formatting (*bold*, _italic_, `code`).
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"An error occurred while generating content: {e}")
        return None

def generate_diagram_image(content):
    """Finds Mermaid code, generates an image from it, and returns the path."""
    mermaid_match = re.search(r"```mermaid\n(.*?)\n```", content, re.DOTALL)
    if not mermaid_match:
        return None, content
    mermaid_code = mermaid_match.group(1).strip()
    text_content = content.replace(mermaid_match.group(0), "").strip()
    print("Found Mermaid code, generating diagram...")
    base64_code = base64.b64encode(mermaid_code.encode("utf-8")).decode("utf-8")
    image_url = f"https://mermaid.ink/img/base64:{base64_code}"
    try:
        image_response = requests.get(image_url)
        image_response.raise_for_status()
        image_path = "diagram.png"
        with open(image_path, "wb") as f:
            f.write(image_response.content)
        print(f"Diagram saved to {image_path}")
        return image_path, text_content
    except requests.exceptions.RequestException as e:
        print(f"Failed to generate diagram image: {e}")
        return None, text_content

def send_telegram_message(text_message, image_path=None):
    """Sends a text message and optionally an image to Telegram."""
    print("Sending message to Telegram...")
    text_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    text_payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text_message, "parse_mode": "Markdown"}
    try:
        requests.post(text_url, json=text_payload).raise_for_status()
        print("  > Text message sent successfully!")
    except requests.exceptions.RequestException as e:
        print(f"  > Failed to send text message: {e}")
        return False
    if image_path:
        photo_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        try:
            with open(image_path, "rb") as image_file:
                files = {"photo": image_file}
                requests.post(photo_url, data={"chat_id": TELEGRAM_CHAT_ID}, files=files).raise_for_status()
            print("  > Image sent successfully!")
        except Exception as e:
            print(f"  > Failed to send image: {e}")
            return False
    return True

# --- 4. MAIN EXECUTION ---
if __name__ == "__main__":
    print("\n--- Main execution started ---")
    next_lesson = find_next_lesson_from_db()

    if next_lesson:
        topic = next_lesson.get('topic')
        raw_content = generate_lesson_content(topic)
        
        if raw_content:
            diagram_path, clean_text = generate_diagram_image(raw_content)
            
            if send_telegram_message(clean_text, diagram_path):
                update_lesson_status_in_db(next_lesson)
    else:
        print("  > No pending lessons to process.")
        send_telegram_message("🎉 You've completed the entire curriculum! Congratulations! 🎉")
        
    print("--- SCRIPT END ---")



    

