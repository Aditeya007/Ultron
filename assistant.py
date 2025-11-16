import os
import json
import subprocess
import webbrowser
import shlex
import time
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path

# ===============================================
# CONFIG
# ===============================================
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
MODEL = "llama-3.3-70b-versatile"

USER_HOME = r"C:\Users\Abcom"
APP_INDEX_FILE = "app_index.json"

SEARCH_PATTERNS = {
    "youtube.com": "https://www.youtube.com/results?search_query=",
    "amazon.com": "https://www.amazon.com/s?k=",
    "amazon.in": "https://www.amazon.in/s?k=",
    "flipkart.com": "https://www.flipkart.com/search?q=",
    "imdb.com": "https://www.imdb.com/find?q=",
    "wikipedia.org": "https://en.wikipedia.org/w/index.php?search=",
    "reddit.com": "https://www.reddit.com/search/?q=",
}

SCAN_PATHS = [
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    os.path.join(USER_HOME, "AppData", "Local", "Programs"),
    os.path.join(USER_HOME, "AppData", "Local"),
    os.path.join(USER_HOME, "AppData", "Roaming"),
    os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"),
                 "Microsoft", "Windows", "Start Menu", "Programs"),
    r"C:\Program Files (x86)\Steam\steamapps\common"
]

INSTALLER_KEYWORDS = ["installer", "setup", "uninstall", "update", "patch"]

PRIORITY_PREFIXES = [
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    os.path.join(USER_HOME, "AppData", "Local", "Programs"),
    os.path.join(USER_HOME, "AppData", "Roaming"),
]


# ===============================================
# JSON CLEANER + NORMALIZER
# ===============================================

def clean_json(raw):
    if not raw:
        return raw

    raw = raw.strip()

    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.replace("json", "", 1).replace("JSON", "", 1).strip()

    raw = raw.replace("```", "").strip()
    return raw


def normalize(obj):
    if not obj:
        return {}

    return {
        "action": obj.get("action"),
        "app": obj.get("app") or obj.get("app_name") or obj.get("application"),
        "url": obj.get("url") or obj.get("website") or obj.get("link"),
        "site": obj.get("site") or obj.get("domain"),
        "query": obj.get("query") or obj.get("search_query"),
    }


# ===============================================
# INDEX BUILDER
# ===============================================

def should_skip(name, full):
    name = name.lower()
    full = full.lower()
    if any(k in name for k in INSTALLER_KEYWORDS):
        return True
    if "downloads" in full:
        return True
    return False


def priority_score(path):
    score = 0
    lp = path.lower()
    for i, prefix in enumerate(PRIORITY_PREFIXES):
        if lp.startswith(prefix.lower()):
            score += (len(PRIORITY_PREFIXES) - i) * 10
    if "steamapps" in lp:
        score += 20
    return score


def scan_paths():
    apps = {}
    start = time.time()

    for base in SCAN_PATHS:
        if not os.path.exists(base):
            continue

        for root, dirs, files in os.walk(base):
            for f in files:
                if not f.lower().endswith(".exe"):
                    continue

                name = f[:-4].lower()
                full = os.path.join(root, f)

                if should_skip(name, full):
                    continue

                if name not in apps:
                    apps[name] = full
                else:
                    if priority_score(full) > priority_score(apps[name]):
                        apps[name] = full

    print(f"Indexed {len(apps)} apps in {time.time() - start:.1f}s")
    return apps


def load_app_index():
    if os.path.exists(APP_INDEX_FILE):
        with open(APP_INDEX_FILE, "r", encoding="utf-8") as f:
            apps = json.load(f)
            print(f"Loaded {len(apps)} apps from index.")
            return apps

    print("Building index...")
    apps = scan_paths()
    with open(APP_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(apps, f, indent=2)
    return apps


APP_INDEX = load_app_index()


# ===============================================
# APP LAUNCHING
# ===============================================

def try_launch(path):
    try:
        subprocess.Popen(shlex.split(f'"{path}"'))
        return True
    except:
        try:
            os.startfile(path)
            return True
        except:
            return False


def launch_uwp(name):
    name = name.lower()

    if name in ("calculator", "calc"):
        try:
            subprocess.Popen("calc.exe")
            return True
        except:
            pass

        try:
            subprocess.Popen(shlex.split(
                'explorer.exe shell:Appsfolder\\Microsoft.WindowsCalculator_8wekyb3d8bbwe!App'))
            return True
        except:
            pass

    return False


# ⭐ FINAL FIXED APP OPENER
def open_app(name):
    name = name.lower().strip()
    tokens = name.split()

    # exact
    if name in APP_INDEX:
        if try_launch(APP_INDEX[name]):
            return

    candidates = []
    for key, path in APP_INDEX.items():
        key_lower = key.lower()
        score = 0

        if key_lower == name:
            score += 200

        if key_lower.startswith(tokens[0]):
            score += 150

        for t in tokens:
            if t in key_lower:
                score += 60

        if name.replace(" ", "") in key_lower.replace(" ", ""):
            score += 100

        if all(t in key_lower for t in tokens):
            score += 200

        score += priority_score(path)

        if score > 0:
            candidates.append((score, key, path))

    candidates.sort(reverse=True)

    for score, k, path in candidates[:5]:
        print(f"Trying: {k} -> {path}")
        if try_launch(path):
            return

    if launch_uwp(name):
        return

    print("❌ App not found:", name)


# ===============================================
# WEB ACTIONS
# ===============================================

def open_website(url):
    if url:
        webbrowser.open(url)
    else:
        print("❌ No URL provided")

def google_search(q):
    webbrowser.open("https://www.google.com/search?q=" + q.replace(" ", "+"))

def youtube_search(q):
    webbrowser.open("https://www.youtube.com/results?search_query=" + q.replace(" ", "+"))

def google_site_search(site, q):
    clean = site.replace("www.", "")
    webbrowser.open(f"https://www.google.com/search?q={q.replace(' ', '+')}+site:{clean}")

def direct_site_search(site, q):
    clean = site.replace("www.", "")

    if clean in SEARCH_PATTERNS:
        url = SEARCH_PATTERNS[clean] + q.replace(" ", "+")
    else:
        url = f"https://www.google.com/search?q={q.replace(' ','+')}+site:{clean}"

    webbrowser.open(url)


# ===============================================
# LLM PARSER (FINAL + STABLE)
# ===============================================

def ask_llm(text):
    prompt = f"""
Return ONLY valid JSON. No code blocks. No ```json. No markdown.

Allowed actions:
- open_app
- open_website
- google_search
- youtube_search
- google_search_on_site
- direct_site_search

User request: {text}
"""

    res = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = res.choices[0].message.content
    print("\nLLM RAW:", raw)

    raw = clean_json(raw)

    try:
        parsed = json.loads(raw)
    except:
        print("❌ JSON parse failed")
        return {}

    return normalize(parsed)


# ===============================================
# EXECUTOR
# ===============================================

def execute(data):
    action = data.get("action")

    if action == "open_app":
        return open_app(data.get("app"))

    if action == "open_website":
        return open_website(data.get("url"))

    if action == "google_search":
        return google_search(data.get("query"))

    if action == "youtube_search":
        return youtube_search(data.get("query"))

    if action == "google_search_on_site":
        return google_site_search(data.get("site"), data.get("query"))

    if action == "direct_site_search":
        return direct_site_search(data.get("site"), data.get("query"))

    print("❌ Unknown action:", action)


# ===============================================
# MAIN LOOP
# ===============================================

def main():
    print("\n==============================")
    print("   AI Desktop Assistant")
    print("==============================")

    while True:
        q = input("\nYou: ").strip()

        if q.lower() in ("exit", "quit", "bye"):
            print("Shutting down…")
            break

        data = ask_llm(q)
        execute(data)


if __name__ == "__main__":
    main()
