# 🤖 AI/ML Telegram Tutor Bot — *Synapse*

**Synapse** is a fully automated **AI & Machine Learning tutor bot** built in Python.  
It delivers daily lessons directly to a Telegram chat, automatically generating educational content using the **Google Gemini API** and managing lesson progression through **Firestore**.

---

## ✨ Features

### 🔹 Automated Content Generation  
Generates high-quality, easy-to-understand AI/ML lessons using **Google’s Gemini API**, simplifying complex topics into digestible formats.

### 🔹 Curriculum Management  
Integrates with **Google Firestore** to maintain a structured curriculum — tracking which lessons are **pending** and which are **completed**.

### 🔹 Telegram Integration  
Automatically sends generated lessons to a **Telegram chat or channel** via the **Telegram Bot API**.

### 🔹 Structured Lessons  
Each lesson follows a clear, easy-to-learn structure:
- **Analogy** – A relatable example for intuition  
- **Explanation** – Concept breakdown in simple terms  
- **Code Example** – A short, practical Python snippet  
- **Key Takeaway** – The main concept in one line  

### 🔹 Resilient & Verifiable  
Ensures data accuracy by verifying message delivery and updating lesson status in Firestore accordingly.

---

## ⚙️ How It Works

The script executes the following workflow:

1. **Initialize**  
   - Loads API keys and credentials from a `.env` file.  
   - Configures the Google Gemini, Firebase, and Telegram clients.

2. **Fetch Next Lesson**  
   - Queries Firestore’s `lessons` collection for the first document with a status of **pending**, ordered by day.

3. **Generate Content**  
   - Sends the topic to **Gemini API** with a structured prompt to generate a complete lesson.

4. **Send to Telegram**  
   - Posts the generated content directly to the specified **Telegram chat ID**.

5. **Update Status**  
   - Marks the lesson as **complete** in Firestore once the Telegram message is successfully sent.

6. **Completion Message**  
   - If no pending lessons remain, sends a **final congratulatory message** to the chat.

---

## 🛠️ Tech Stack

| Component | Technology Used |
|------------|------------------|
| **Language** | Python 3 |
| **AI Model** | Google Gemini API |
| **Database** | Google Firestore (NoSQL) |
| **Messaging** | Telegram Bot API |
| **Libraries** | `google-generativeai`, `firebase-admin`, `python-dotenv`, `requests` |

---

> 💡 **Note:**  
> You can automate this bot for **any type of educational or content-based project**, not just AI/ML.  
> This implementation was built **as a fun experiment** to teach AI and ML concepts automatically.

---
