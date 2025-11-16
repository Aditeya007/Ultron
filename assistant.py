import subprocess
import webbrowser
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Load API key
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

MODEL = "llama-3.3-70b-versatile"

# ---------------------------------------------------
# UNIVERSAL SEARCH PATTERNS FOR DIRECT SITE SEARCH
# ---------------------------------------------------

SEARCH_PATTERNS = {
    "amazon.com": "https://www.amazon.com/s?k=",
    "amazon.in": "https://www.amazon.in/s?k=",
    "flipkart.com": "https://www.flipkart.com/search?q=",
    "imdb.com": "https://www.imdb.com/find?q=",
    "wikipedia.org": "https://en.wikipedia.org/w/index.php?search=",
    "reddit.com": "https://www.reddit.com/search/?q=",
    "youtube.com": "https://www.youtube.com/results?search_query=",
}

# ---------------------------------------------------
# UNIVERSAL APP SCANNER (Windows)
# ---------------------------------------------------

APP_INDEX_FILE = "app_index.json"

def build_app_index():
    print("🔍 Scanning installed apps...")

    app_map = {}

    # 1. Start Menu shortcuts (.lnk files)
    start_menu_paths = [
        os.environ.get("ProgramData") + r"\Microsoft\Windows\Start Menu\Programs",
        os.environ.get("APPDATA") + r"\Microsoft\Windows\Start Menu\Programs"
    ]

    for start_path in start_menu_paths:
        if start_path and os.path.exists(start_path):
            for root, dirs, files in os.walk(start_path):
                for file in files:
                    if file.endswith(".lnk"):
                        name = file.replace(".lnk", "").lower()
                        app_map[name] = os.path.join(root, file)

    # 2. Program Files & Program Files (x86)
    system_paths = [
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)")
    ]

    for sys_path in system_paths:
        if sys_path and os.path.exists(sys_path):
            for root, dirs, files in os.walk(sys_path):
                for file in files:
                    if file.endswith(".exe"):
                        exe_path = os.path.join(root, file)
                        name = file.replace(".exe", "").lower()
                        app_map[name] = exe_path

    # Save index
    with open(APP_INDEX_FILE, "w") as f:
        json.dump(app_map, f, indent=2)

    print("✅ Indexed", len(app_map), "apps.")
    return app_map


def load_app_index():
    if os.path.exists(APP_INDEX_FILE):
        with open(APP_INDEX_FILE, "r") as f:
            return json.load(f)
    return build_app_index()


APP_INDEX = load_app_index()

# ---------------------------------------------------
# APP LAUNCHER (UNIVERSAL)
# ---------------------------------------------------

def open_app(app_name):
    name = app_name.lower().strip()

    # Exact match
    if name in APP_INDEX:
        print("Opening:", APP_INDEX[name])
        subprocess.Popen(APP_INDEX[name])
        return

    # Fuzzy match (partial word)
    for key in APP_INDEX:
        if name in key:
            print("Opening:", APP_INDEX[key])
            subprocess.Popen(APP_INDEX[key])
            return

    print("❌ App not found:", app_name)

# ---------------------------------------------------
# WEBSITE & SEARCH ACTIONS
# ---------------------------------------------------

def open_website(url):
    print("Opening website:", url)
    webbrowser.open(url)

def google_search(query):
    url = "https://www.google.com/search?q=" + query.replace(" ", "+")
    print("Google search:", query)
    webbrowser.open(url)

def youtube_search(query):
    url = "https://www.youtube.com/results?search_query=" + query.replace(" ", "+")
    print("YouTube search:", query)
    webbrowser.open(url)

def google_search_on_site(site, query):
    clean = site.replace("https://", "").replace("http://", "").replace("www.", "")
    url = "https://www.google.com/search?q=" + query.replace(" ", "+") + "+site:" + clean
    print("Google search on", clean, ":", query)
    webbrowser.open(url)

def direct_site_search(site, query):
    clean = site.replace("https://", "").replace("http://", "").replace("www.", "")

    if clean in SEARCH_PATTERNS:
        url = SEARCH_PATTERNS[clean] + query.replace(" ", "+")
    else:
        url = "https://www.google.com/search?q=" + query.replace(" ", "+") + "+site:" + clean

    print("Direct search on", clean, ":", query)
    webbrowser.open(url)

# ---------------------------------------------------
# LLM PARSER (NO f-strings, 100% safe)
# ---------------------------------------------------

def ask_llm_for_action(user_input):
    prompt = """
Convert the user's request into a JSON action.
Output ONLY JSON. No explanations.

Allowed actions:
- open_app
- open_website
- google_search
- youtube_search
- google_search_on_site
- direct_site_search

Rules:
- If user says "open X.com and search Y" → direct_site_search
- If website isn't known → google_search_on_site
- Never output anything outside JSON.

Examples:

User: open youtube
{{"action": "open_website", "url": "https://youtube.com"}}

User: google best gaming laptops
{{"action": "google_search", "query": "best gaming laptops"}}

User: search spiderman on youtube
{{"action": "youtube_search", "query": "spiderman"}}

User: open amazon.com and search ps5 controllers
{{"action": "direct_site_search", "site": "amazon.com", "query": "ps5 controllers"}}

User command:
"""
    prompt += user_input

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.choices[0].message.content
    print("\nLLM RAW:", raw)

    try:
        return json.loads(raw)
    except:
        print("❌ JSON Parse Error")
        return None

# ---------------------------------------------------
# EXECUTOR
# ---------------------------------------------------

def execute_action(data):
    if not data:
        return

    action = data.get("action")

    # Accept both "app" and "app_name"
    app_value = data.get("app") or data.get("app_name")

    if action == "open_app":
        if app_value:
            open_app(app_value)
        else:
            print("❌ No app name provided by LLM.")
        return

    elif action == "open_website":
        open_website(data.get("url"))
        return

    elif action == "google_search":
        google_search(data.get("query"))
        return

    elif action == "youtube_search":
        youtube_search(data.get("query"))
        return

    elif action == "google_search_on_site":
        google_search_on_site(data.get("site"), data.get("query"))
        return

    elif action == "direct_site_search":
        direct_site_search(data.get("site"), data.get("query"))
        return

    else:
        print("❌ Unknown action:", action)

# ---------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------

def main():
    print("\n==============================")
    print("  AI Desktop Assistant (Text)")
    print("==============================")

    while True:
        user_input = input("\nYou: ")

        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Assistant shutting down…")
            break

        parsed = ask_llm_for_action(user_input)
        execute_action(parsed)

if __name__ == "__main__":
    main()
