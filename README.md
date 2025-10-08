AI/ML Telegram Tutor Bot 🤖
This project is a fully automated Python script that functions as an AI and Machine Learning tutor named 'Synapse'. It fetches lesson topics from a Firestore database, uses the Google Gemini API to generate educational content, and sends it as a daily message to a specified Telegram chat.

Features ✨
Automated Content Generation: Uses Google's Gemini API to create high-quality, easy-to-understand lessons on complex AI/ML topics.

Curriculum Management: Leverages Google Firestore to manage a curriculum of lessons, tracking which ones are pending and which are complete.

Telegram Integration: Delivers the generated lessons directly to a Telegram chat or channel via a bot.

Structured Lessons: Each lesson is structured with a simple analogy, a clear explanation, a practical Python code example, and a key takeaway.

Resilient and Verifiable: Includes verification steps to ensure a lesson's status is correctly updated in the database after being sent.

How It Works ⚙️
The script executes the following workflow:

Initialize: Loads API keys and credentials from a .env file and configures the Google Gemini, Firebase, and Telegram clients.

Fetch Next Lesson: Queries the Firestore lessons collection to find the first document with a status of pending, ordered by day.

Generate Content: If a pending lesson is found, its topic is sent to the Gemini API, which generates the lesson content based on a structured prompt.

Send to Telegram: The generated lesson text is sent as a message to the configured Telegram chat ID.

Update Status: Upon successful delivery to Telegram, the script updates the lesson's status in Firestore from pending to complete.

Completion Message: If no pending lessons are found, it sends a final congratulatory message and the script concludes.

Tech Stack 🛠️
Language: Python 3

AI Model: Google Gemini API

Database: Google Firestore (NoSQL)

Messaging: Telegram Bot API

Libraries: google-generativeai, firebase-admin, python-dotenv, requests
