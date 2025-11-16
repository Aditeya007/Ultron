import subprocess
import webbrowser
import json
import os
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
# UNIVERSAL SEARCH PATTERNS FOR ANY WEBSITE
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
# ACTION FUNCTIONS
# ---------------------------------------------------

def open_app(app_name):
    try:
        subprocess.Popen(app_name)
        print("Opening app:", app_name)
    except:
        print("Failed to open app:", app_name)

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
        base = SEARCH_PATTERNS[clean]
        url = base + query.replace(" ", "+")
    else:
        url = "https://www.google.com/search?q=" + query.replace(" ", "+") + "+site:" + clean

    print("Direct search on", clean, ":", query)
    webbrowser.open(url)

# ---------------------------------------------------
# LLM PARSER
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
- If site is unknown → google_search_on_site
- Never output text outside JSON.

Examples:

User: open youtube
{{"action": "open_website", "url": "https://youtube.com"}}

User: search iron man on youtube
{{"action": "youtube_search", "query": "iron man"}}

User: google best gaming laptops
{{"action": "google_search", "query": "best gaming laptops"}}

User: open chrome
{{"action": "open_app", "app": "chrome"}}

User: open amazon.com and search for ps5 controllers
{{"action": "direct_site_search", "site": "amazon.com", "query": "ps5 controllers"}}

User: open imdb.com and search spiderman
{{"action": "direct_site_search", "site": "imdb.com", "query": "spiderman"}}

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

    if action == "open_app":
        open_app(data["app"])

    elif action == "open_website":
        open_website(data["url"])

    elif action == "google_search":
        google_search(data["query"])

    elif action == "youtube_search":
        youtube_search(data["query"])

    elif action == "google_search_on_site":
        google_search_on_site(data["site"], data["query"])

    elif action == "direct_site_search":
        direct_site_search(data["site"], data["query"])

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
