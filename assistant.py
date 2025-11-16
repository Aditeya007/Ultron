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
# ACTION FUNCTIONS
# ---------------------------------------------------

def open_app(app_name):
    try:
        subprocess.Popen(app_name)
        print(f"Opening app: {app_name}")
    except:
        print(f"Failed to open app: {app_name}")

def open_website(url):
    print(f"Opening website: {url}")
    webbrowser.open(url)

def google_search(query):
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    print(f"Google search: {query}")
    webbrowser.open(url)

def youtube_search(query):
    url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
    print(f"YouTube search: {query}")
    webbrowser.open(url)

def google_search_on_site(site, query):
    site = site.replace("https://", "").replace("http://", "").replace("www.", "")
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}+site:{site}"
    print(f"Google search on {site}: {query}")
    webbrowser.open(url)

# ---------------------------------------------------
# LLM PARSER
# ---------------------------------------------------

def ask_llm_for_action(user_input):
    prompt = """
Convert the user's command into a JSON action.  
ONLY output JSON. Never add explanation.

Allowed actions:
- open_app
- open_website
- google_search
- youtube_search
- google_search_on_site

Rules:
- If user says "open X", output open_website or open_app
- If user says "search Y on youtube", use youtube_search
- If user says "google X", use google_search
- If user says "search Y on X.com" → use google_search_on_site
- If user says "open X.com and search Y" → google_search_on_site

Examples:

User: open youtube
{{"action": "open_website", "url": "https://youtube.com"}}

User: search iron man trailer on youtube
{{"action": "youtube_search", "query": "iron man trailer"}}

User: google best budget phones
{{"action": "google_search", "query": "best budget phones"}}

User: open chrome
{{"action": "open_app", "app": "chrome"}}

User: open amazon.com in google and search ps5 controllers
{{"action": "google_search_on_site", "site": "amazon.com", "query": "ps5 controllers"}}

User: open flipkart.com and search gaming laptops
{{"action": "google_search_on_site", "site": "flipkart.com", "query": "gaming laptops"}}

User command: "{}"
""".format(user_input)

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
