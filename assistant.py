import subprocess
import webbrowser
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# --------------------------------------------
# Load API key
# --------------------------------------------
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

MODEL = "llama-3.3-70b-versatile"

# --------------------------------------------
# DIRECT WEBSITE SEARCH PATTERNS
# --------------------------------------------
SEARCH_PATTERNS = {
    "amazon.com": "https://www.amazon.com/s?k=",
    "amazon.in": "https://www.amazon.in/s?k=",
    "flipkart.com": "https://www.flipkart.com/search?q=",
    "imdb.com": "https://www.imdb.com/find?q=",
    "wikipedia.org": "https://en.wikipedia.org/w/index.php?search=",
    "reddit.com": "https://www.reddit.com/search/?q=",
    "youtube.com": "https://www.youtube.com/results?search_query=",
}

# --------------------------------------------
# UNIVERSAL FULL-PC APP SCANNER
# --------------------------------------------

APP_INDEX_FILE = "app_index.json"

def get_all_drives():
    drives = []
    for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        if os.path.exists(f"{letter}:/"):
            drives.append(f"{letter}:/")
    return drives

def scan_drive_for_exe(drive_path, app_map):
    print(f"🔍 Scanning drive {drive_path} ... (may take time)")
    for root, dirs, files in os.walk(drive_path, topdown=True):
        # optional performance skip
        if "\\Windows" in root or "\\ProgramData" in root:
            continue

        for file in files:
            if file.endswith(".exe"):
                clean_name = file.replace(".exe", "").lower().strip()
                full_path = os.path.join(root, file)
                app_map[clean_name] = full_path

    return app_map

def build_app_index():
    print("🔍 Full system scan started — scanning ALL drives for .exe files...")
    app_map = {}

    drives = get_all_drives()
    for drive in drives:
        scan_drive_for_exe(drive, app_map)

    with open(APP_INDEX_FILE, "w") as f:
        json.dump(app_map, f, indent=2)

    print(f"✅ App index built — {len(app_map)} apps found.")
    return app_map

def load_app_index():
    if os.path.exists(APP_INDEX_FILE):
        print("📂 Loading existing app index...")
        with open(APP_INDEX_FILE, "r") as f:
            return json.load(f)
    else:
        print("⚠ No index file found. Starting full scan.")
        return build_app_index()

APP_INDEX = load_app_index()

# --------------------------------------------
# UNIVERSAL APP OPENER
# --------------------------------------------
def open_app(app_name):
    name = app_name.lower().strip()

    # exact match
    if name in APP_INDEX:
        print("Opening:", APP_INDEX[name])
        subprocess.Popen(APP_INDEX[name])
        return

    # fuzzy match
    for key in APP_INDEX:
        if name in key:
            print("Opening:", APP_INDEX[key])
            subprocess.Popen(APP_INDEX[key])
            return

    print("❌ App not found:", app_name)

# --------------------------------------------
# WEBSITE & SEARCH FUNCTIONS
# --------------------------------------------
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
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}+site:{clean}"
    print(f"Google search on {clean}: {query}")
    webbrowser.open(url)

def direct_site_search(site, query):
    clean = site.replace("https://", "").replace("http://", "").replace("www.", "")

    if clean in SEARCH_PATTERNS:
        url = SEARCH_PATTERNS[clean] + query.replace(" ", "+")
    else:
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}+site:{clean}"

    print(f"Direct search on {clean}: {query}")
    webbrowser.open(url)

# --------------------------------------------
# LLM PARSING LOGIC
# --------------------------------------------
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
- Unknown sites → google_search_on_site
- Never output extra text.

Examples:

User: open youtube
{{"action": "open_website", "url": "https://youtube.com"}}

User: google best budget phones
{{"action": "google_search", "query": "best budget phones"}}

User: search Iron Man trailer on youtube
{{"action": "youtube_search", "query": "Iron Man trailer"}}

User: open amazon.com and search vr headset
{{"action": "direct_site_search", "site": "amazon.com", "query": "vr headset"}}

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

# --------------------------------------------
# EXECUTOR
# --------------------------------------------
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
            print("❌ LLM did not provide app name.")
        return

    if action == "open_website":
        open_website(data.get("url"))
        return

    if action == "google_search":
        google_search(data.get("query"))
        return

    if action == "youtube_search":
        youtube_search(data.get("query"))
        return

    if action == "google_search_on_site":
        google_search_on_site(data.get("site"), data.get("query"))
        return

    if action == "direct_site_search":
        direct_site_search(data.get("site"), data.get("query"))
        return

    print("❌ Unknown action:", action)

# --------------------------------------------
# MAIN LOOP
# --------------------------------------------
def main():
    print("\n==============================")
    print("      AI Desktop Assistant")
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
