import os
import json
import requests
import re
import base64
from openai import OpenAI
from dotenv import load_dotenv

# --- 1. SETUP: LOAD SECRETS and CONFIGURE API ---

# Load environment variables from .env file
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Configure the OpenAI API client
# The script will exit if the API key is not found.
if not OPENAI_API_KEY:
    print("Error: OPENAI_API_KEY not found in .env file.")
    exit()
client = OpenAI(api_key=OPENAI_API_KEY)

CURRICULUM_FILE = "Curriculam.json"

# --- 2. CORE FUNCTIONS ---

def load_curriculum():
    """Loads the curriculum data from the JSON file."""
    try:
        with open(CURRICULUM_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {CURRICULUM_FILE} not found.")
        return None

def find_next_lesson(curriculum):
    """Finds the first lesson with the status 'pending'."""
    for lesson in curriculum:
        if lesson.get("status") == "pending":
            return lesson
    return None

def generate_lesson_content(topic):
    """Generates the educational content for a given topic using the OpenAI API."""
    print(f"Generating lesson for topic: {topic}...")
    
    system_prompt = """
    You are an expert AI and Machine Learning tutor named 'Synapse'.
    Your goal is to explain complex topics in the simplest way possible for a Telegram message.
    You must follow the requested structure and formatting rules STRICTLY.
    """
    
    user_prompt = f"""
    Today's topic is: "{topic}"

    **STRUCTURE:**
    1.  **Simple Analogy:** Start with a simple, real-world analogy.
    2.  **Clear Explanation:** Give a concise, easy-to-read explanation.
    3.  **Diagram:** Create a flowchart diagram using Mermaid syntax. Enclose it in a markdown code block with the language set to 'mermaid'. For example:
        ```mermaid
        graph TD;
            A[Start] --> B[Process];
            B --> C[End];
        ```
    4.  **Practical Example:** Provide a short, well-commented Python code snippet if applicable.
    5.  **Key Takeaway:** Summarize the most important point in one sentence.

    **FORMATTING RULES:**
    - Use ONLY these Markdown styles: *bold text* for bolding and _italic text_ for italics.
    - Use backticks for code, like `print("Hello")`.
    - DO NOT use Markdown headings (#), lists (- or *), or horizontal lines (---).
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # You can also use "gpt-3.5-turbo"
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"An error occurred while generating content with OpenAI: {e}")
        return None

def generate_diagram_image(content):
    """Finds Mermaid code in text, generates an image, and saves it."""
    mermaid_match = re.search(r"```mermaid\n(.*?)\n```", content, re.DOTALL)
    if not mermaid_match:
        print("No Mermaid diagram found in the content.")
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
        text_response = requests.post(text_url, json=text_payload)
        text_response.raise_for_status()
        print("Text message sent successfully!")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send text message: {e}")
        return False

    if image_path:
        photo_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        photo_payload = {"chat_id": TELEGRAM_CHAT_ID}
        try:
            with open(image_path, "rb") as image_file:
                files = {"photo": image_file}
                photo_response = requests.post(photo_url, data=photo_payload, files=files)
                photo_response.raise_for_status()
            print("Image sent successfully!")
        except (requests.exceptions.RequestException, FileNotFoundError) as e:
            print(f"Failed to send image: {e}")
            return False
            
    return True

def update_curriculum_status(curriculum, day):
    """Updates the status of a lesson to 'complete' and saves the file."""
    for lesson in curriculum:
        if lesson.get("day") == day:
            lesson["status"] = "complete"
            break
            
    with open(CURRICULUM_FILE, 'w') as f:
        json.dump(curriculum, f, indent=2)
    print(f"Updated Day {day} to 'complete'.")

# --- 3. MAIN EXECUTION ---

if __name__ == "__main__":
    print("OpenAI Tutor Agent started...")
    
    curriculum_data = load_curriculum()
    if not curriculum_data:
        exit()

    next_lesson = find_next_lesson(curriculum_data)

    if next_lesson:
        day = next_lesson['day']
        topic = next_lesson['topic']
        
        print(f"Found next lesson: Day {day} - {topic}")
        
        raw_content = generate_lesson_content(topic)
        
        if raw_content:
            diagram_path, clean_text = generate_diagram_image(raw_content)
            
            if send_telegram_message(clean_text, diagram_path):
                update_curriculum_status(curriculum_data, day)
    else:
        print("Congratulations! All lessons are complete.")
        send_telegram_message("🎉 You've completed the entire curriculum! Congratulations! 🎉")
        
    print("OpenAI Tutor Agent finished.")
