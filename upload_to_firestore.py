import json
import firebase_admin
from firebase_admin import credentials, firestore

# --- SETUP ---
# Path to your downloaded Firebase credentials
CRED_PATH = 'firebase-credentials.json'
CURRICULUM_FILE = 'Curriculam.json'
COLLECTION_NAME = 'lessons' # This will be the name of our collection in Firestore

# Initialize Firebase Admin SDK
cred = credentials.Certificate(CRED_PATH)
firebase_admin.initialize_app(cred)
db = firestore.client()

# --- UPLOAD LOGIC ---
print(f"Uploading lessons from {CURRICULUM_FILE} to Firestore collection '{COLLECTION_NAME}'...")

try:
    with open(CURRICULUM_FILE, 'r') as f:
        curriculum = json.load(f)

    # Loop through each lesson and add it to Firestore
    # We use the 'day' number as the document ID for easy reference
    for lesson in curriculum:
        day_id = str(lesson['day'])
        db.collection(COLLECTION_NAME).document(day_id).set(lesson)
        print(f"  > Uploaded Day {day_id}: {lesson['topic']}")

    print("\n✅ Upload complete!")

except Exception as e:
    print(f"\nAn error occurred: {e}")
