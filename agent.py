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
load_dotenv()

# Load Google Gemini API Key and configure the client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-pro') # Using the stable gemini-pro model

# Load Telegram secrets and clean them to prevent errors in automation
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip().strip('"')
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip().strip('"')

# Load Firebase credentials from a JSON string in environment variables for GitHub Actions
FIREBASE_CREDS_JSON = os.getenv("FIREBASE_CREDS_JSON")
try:
    if FIREBASE_CREDS_JSON:
        creds_dict = json.loads(FIREBASE_CREDS_JSON)
        cred = credentials.Certificate(creds_dict)
    else:
        # Fallback for local development using the credentials file
        cred = credentials.Certificate("firebase-credentials.json")

    # Initialize Firebase App (only if it hasn't been initialized yet)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
except Exception as e:
    print(f"Error initializing Firebase: {e}")
    exit() # Exit if Firebase can't be configured

db = firestore.client()
LESSONS_COLLECTION = 'lessons'

# --- 2. EDITED CODE: DATABASE FUNCTIONS ---

def find_next_lesson_from_db():
    """Finds the first lesson with status 'pending' from Firestore, ordered by day."""
    print("Querying Firestore for the next pending lesson...")
    try:
        lessons_ref = db.collection(LESSONS_COLLECTION)
        # Query for pending lessons, order by the 'day' field, and get the first one
        query = lessons_ref.where('status', '==', 'pending').order_by('day').limit(1)
        results = query.stream()

        for lesson_doc in results:
            return lesson_doc.to_dict()
        return None # Return None if no pending lessons are found
    except Exception as e:
        print(f"An error occurred while querying Firestore: {e}")
        return None

# New, more robust function
def update_lesson_status_in_db(lesson_data):
    """Overwrites the lesson document in Firestore with an updated status."""
    day = lesson_data.get('day')
    print(f"Updating status for Day {day} in Firestore...")
    try:
        # Create a copy of the lesson data and change the status
        updated_lesson = lesson_data.copy()
        updated_lesson['status'] = 'complete'

        # Use .set() to completely overwrite the document. This is more reliable.
        lesson_ref = db.collection(LESSONS_COLLECTION).document(str(day))
        lesson_ref.set(updated_lesson)
        print(f"  > Successfully updated Day {day} to 'complete'.")
    except Exception as e:
        print(f"  > Failed to update status for Day {day}: {e}")

# --- 3. UNEDITED CODE: CORE LOGIC FUNCTIONS ---

def generate_lesson_content(topic):
    """(Unchanged) Generates the educational content and a Mermaid diagram for a given topic."""
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
    """(Unchanged) Finds Mermaid code, generates an image from it, and returns the path."""
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
    """(Unchanged) Sends a text message and optionally an image to Telegram."""
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

# --- 4. EDITED CODE: MAIN EXECUTION ---

if __name__ == "__main__":
    print("--- Stateful AI Tutor Agent started ---")

    # The main logic now calls the database functions
    next_lesson = find_next_lesson_from_db()

    if next_lesson:
        day = next_lesson.get('day')
        topic = next_lesson.get('topic')
        
        print(f"Found next lesson from DB: Day {day} - {topic}")
        
        raw_content = generate_lesson_content(topic)
        
        if raw_content:
            diagram_path, clean_text = generate_diagram_image(raw_content)
            
            if send_telegram_message(clean_text, diagram_path):
                # If the message is sent successfully, update the status in the database
                update_lesson_status_in_db(next_lesson)
    else:
        print("Congratulations! All lessons in Firestore are complete.")
        send_telegram_message("🎉 You've completed the entire curriculum! Congratulations! 🎉")
        
    print("--- Stateful AI Tutor Agent finished ---")

