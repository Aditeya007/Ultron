import subprocess
import webbrowser
import json
import os
import difflib
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

# ============================================================
# 🔧 CONFIGURATION: CUSTOM APPS & PATHS
# ============================================================
# Add your games or specific apps here if the scanner misses them.
# Use double backslashes "\\" for paths.

MY_CUSTOM_APPS = {
    # Examples (You can add your own here):
    "marvel rivals": r"C:\Program Files (x86)\Steam\steamapps\common\MarvelRivals\Launcher.exe",
    "valorant": r"C:\Riot Games\Riot Client\RiotClientServices.exe",
    "obs": r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
}

APP_INDEX_FILE = "app_database.json"

# ============================================================
# 🔍 INDEXING ENGINE (Runs once, then loads from file)
# ============================================================

def build_app_index():
    print("\n⚡ STARTING FULL SYSTEM SCAN (This happens once)...")
    print("   Please wait, looking for apps and games...")
    
    app_map = {}

    # 1. ADD CUSTOM APPS (Highest Priority)
    app_map.update(MY_CUSTOM_APPS)

    # 2. ADD SYSTEM COMMANDS (Windows defaults)
    # These fix the "Open Calculator" or "Open Notepad" issues.
    system_commands = {
        "calculator": "calc", "calc": "calc",
        "notepad": "notepad", "paint": "mspaint",
        "cmd": "cmd", "terminal": "wt",
        "powershell": "powershell", "explorer": "explorer",
        "task manager": "taskmgr", "control panel": "control",
        "settings": "ms-settings:", "camera": "microsoft.windows.camera:",
        "photos": "ms-photos:"
    }
    app_map.update(system_commands)

    # 3. SCAN START MENU & DESKTOP (Shortcuts are the most reliable)
    shortcut_dirs = [
        os.path.join(os.getenv("APPDATA"), r"Microsoft\Windows\Start Menu"),
        os.path.join(os.getenv("ProgramData"), r"Microsoft\Windows\Start Menu"),
        os.path.join(os.getenv("USERPROFILE"), "Desktop"),
        os.path.join(os.getenv("PUBLIC"), "Desktop"),
    ]

    print("   - Scanning Shortcuts...")
    for folder in shortcut_dirs:
        if os.path.exists(folder):
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith((".lnk", ".url")):
                        name = file.rsplit(".", 1)[0].lower()
                        app_map[name] = os.path.join(root, file)

    # 4. DEEP SCAN PROGRAM FILES (Finds installed .exe directly)
    print("   - Scanning Program Files (Deep Search)...")
    
    search_roots = [
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
        # os.path.join(os.environ.get("SystemDrive"), "Games") # Optional: Add if you have a Games folder
    ]

    skip_keywords = ["uninstall", "setup", "update", "helper", "crash", "installer", "framework", "service", "system32"]

    for root_dir in search_roots:
        if not root_dir or not os.path.exists(root_dir): continue
        
        for root, dirs, files in os.walk(root_dir):
            # Optimization: Skip huge system folders to speed up scan
            if "Windows" in root or "Common Files" in root: 
                continue
                
            for file in files:
                if file.lower().endswith(".exe"):
                    name = file.lower().replace(".exe", "")
                    
                    # Filter out junk EXEs
                    if any(bad in name for bad in skip_keywords): continue
                    
                    # Only add if not already found (Shortcuts take priority)
                    if name not in app_map:
                        app_map[name] = os.path.join(root, file)

    # Save to JSON file
    print(f"   - Saving database to {APP_INDEX_FILE}...")
    with open(APP_INDEX_FILE, "w") as f:
        json.dump(app_map, f, indent=2)

    print(f"✅ Scan Complete! Found {len(app_map)} apps.")
    return app_map

def load_app_index():
    # If the file exists, load it instantly (No scanning!)
    if os.path.exists(APP_INDEX_FILE):
        try:
            print("📂 Loading app database...")
            with open(APP_INDEX_FILE, "r") as f:
                data = json.load(f)
                print(f"✅ Loaded {len(data)} apps from cache.")
                return data
        except:
            print("⚠️ Database corrupt. Rebuilding...")
    
    # If file doesn't exist, build it
    return build_app_index()

# Load index on startup
APP_INDEX = load_app_index()

# ============================================================
# 🚀 EXECUTION & AI
# ============================================================

def open_app(app_name):
    if not app_name: return
    query = app_name.lower().strip()

    # 1. Exact Match
    if query in APP_INDEX:
        print(f"🚀 Opening: {query}")
        try: os.startfile(APP_INDEX[query])
        except Exception as e: print(f"❌ Failed to open: {e}")
        return

    # 2. Fuzzy Match (Smart Guess)
    matches = difflib.get_close_matches(query, APP_INDEX.keys(), n=1, cutoff=0.4)
    if matches:
        best = matches[0]
        print(f"🚀 Opening: {best} (guessed for '{query}')")
        try: os.startfile(APP_INDEX[best])
        except Exception as e: print(f"❌ Failed to open: {e}")
        return

    # 3. Substring Match (Fallback)
    for key in APP_INDEX:
        if query in key:
            print(f"🚀 Opening: {key}")
            try: os.startfile(APP_INDEX[key])
            except: pass
            return
    
    print(f"❌ App '{app_name}' not found.")
    print("👉 Tip: Add the path to 'MY_CUSTOM_APPS' in the Python script, or type 'refresh'.")

def open_website(url):
    if not url.startswith("http"): url = "https://" + url
    print(f"🌐 Opening: {url}")
    webbrowser.open(url)

def ask_llm(user_input):
    # AI generates the URL dynamically for ANY website
    prompt = f"""
    Act as a desktop assistant. Return JSON ONLY.
    
    1. OPEN APP: {{ "action": "open_app", "app_name": "name" }}
    
    2. SEARCH SPECIFIC SITE: 
       - Generate the search URL for the site yourself.
       - Examples:
         - "Search Amazon for ps5" -> {{ "action": "open_website", "url": "https://www.amazon.com/s?k=ps5" }}
         - "Search Reddit for news" -> {{ "action": "open_website", "url": "https://www.reddit.com/search/?q=news" }}
         - "Search ChatGPT for python" -> {{ "action": "open_website", "url": "https://chatgpt.com/?q=python" }}
    
    3. GENERAL SEARCH: {{ "action": "google_search", "query": "your query" }}

    User: "{user_input}"
    """
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        res = response.choices[0].message.content.strip()
        if res.startswith("```"): res = res.replace("```json", "").replace("```", "")
        return json.loads(res)
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return None

# ============================================================
# 🏁 MAIN LOOP
# ============================================================

def main():
    print("\n===========================================")
    print("  🤖 AI DESKTOP ASSISTANT (Final Version)")
    print("===========================================")
    print("• Type 'refresh' to re-scan your PC.")
    print("• Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input: continue
        
        if user_input.lower() in ["exit", "quit"]: break
        
        # Force re-scan command
        if user_input.lower() == "refresh":
            global APP_INDEX
            APP_INDEX = build_app_index() 
            continue

        data = ask_llm(user_input)
        
        if data:
            action = data.get("action")
            
            if action == "open_app": 
                open_app(data.get("app_name"))
                
            elif action == "open_website": 
                open_website(data.get("url"))
                
            elif action == "google_search": 
                print(f"🔍 Google: {data.get('query')}")
                webbrowser.open(f"[https://www.google.com/search?q=](https://www.google.com/search?q=){data.get('query').replace(' ', '+')}")
            
            else: 
                print("❌ Unknown command.")

if __name__ == "__main__":
    main()