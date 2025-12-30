import subprocess
import webbrowser
import json
import os
import difflib
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import random
import pyautogui
import screen_brightness_control as sbc
import comtypes
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

MODEL = "llama-3.3-70b-versatile"


MY_CUSTOM_APPS = {
    "marvel rivals": r"C:\Program Files (x86)\Steam\steamapps\common\MarvelRivals\Launcher.exe",
    "valorant": r"C:\Riot Games\Riot Client\RiotClientServices.exe",
    "obs": r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
}

APP_INDEX_FILE = "app_database.json"


PERSONALITY = (
    "Calm, friendly, and confident. Speaks like a seasoned mentor who's seen worse and survived it. "
    "Supportive and relaxed, occasionally sarcastic—never mean or constant. "
    "Gives clear guidance without overexplaining. Responds to mistakes with patience and light humor. "
    "Observant first, clever second, decisive when needed."
)


def persona_response(kind, **kwargs):
    """Return a short, varied reply in Ezio's persona.

    kind: one of 'volume', 'brightness', 'screenshot', 'open_app_ok', 'open_app_not_found',
          'open_website', 'google_search', 'unknown', 'error'
    """
    templates = {
        'volume': [
            "Volume bumped to {value}%. Easy peasy.",
            "All right — volume's now at {value}%."
            ,"Set to {value}% — that's a solid level."
        ],
        'brightness': [
            "Brightness at {value}%. Eyes should thank you.",
            "Done. Screen brightness: {value}%.",
            "Adjusting light to {value}% — comfortable and practical."
        ],
        'screenshot': [
            "Saved screenshot to {path}. Good memory.",
            "Got it — screenshot stored at {path}.",
            "Picture taken: {path}. Don't lose it."
        ],
        'open_app_ok': [
            "Opened {name} for you.",
            "Launched {name}. There you go.",
            "{name} should be running now."
        ],
        'open_app_not_found': [
            "Couldn't find {name}. Try 'refresh' to rescan.",
            "I don't see {name} here — maybe run a refresh.",
            "No match for {name}. You can 'refresh' and I'll try again."
        ],
        'open_website': [
            "Opening the site now.",
            "Here you go — launching that page.",
            "On it. The browser should open shortly."
        ],
        'google_search': [
            "Searching Google for '{query}'."
            ,"I'll look that up: {query}."
            ,"Searching the web for: {query}."
        ],
        'unknown': [
            "Hmm — I don't know that command. Try something else.",
            "No idea what that means. Rephrase?",
            "I can't do that — try a different request."
        ],
        'error': [
            "Ran into an error: {msg}",
            "Something went sideways: {msg}"
        ]
    }

    opts = templates.get(kind, ["Done."])
    choice = random.choice(opts)
    try:
        return choice.format(**kwargs)
    except Exception:
        return choice



def set_system_volume(level):
    """
    Sets the master volume. Level should be an integer between 0 and 100.
    """
    try:
        level = max(0, min(100, int(level)))
        scalar_volume = level / 100.0

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(scalar_volume, None)
        return True, level

    except Exception:
        try:
            from comtypes import GUID

            CLSID_MMDeviceEnumerator = GUID('{BCDE0395-E52F-467C-8E3D-C4579291692E}')
            IID_IMMDeviceEnumerator = GUID('{A95664D2-9614-4F35-A746-DE8DB63617E6}')

            enumerator = comtypes.CoCreateInstance(
                CLSID_MMDeviceEnumerator,
                comtypes.IUnknown,
                CLSCTX_ALL
            )

            from pycaw.pycaw import IMMDeviceEnumerator, EDataFlow, ERole
            enumerator = enumerator.QueryInterface(IMMDeviceEnumerator)
            endpoint = enumerator.GetDefaultAudioEndpoint(0, 1)
            interface = endpoint.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(scalar_volume, None)
            return True, level

        except Exception as e2:
            return False, str(e2)

def set_system_brightness(level):
    """
    Sets the screen brightness. Level should be an integer between 0 and 100.
    """
    try:
        level = max(0, min(100, int(level)))
        sbc.set_brightness(level)
        return True, level
    except Exception as e:
        return False, str(e)

def take_screenshot():
    """
    Takes a screenshot of the entire screen and saves it to a 'Screenshots' folder.
    """
    try:
        folder_name = "Screenshots"
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(folder_name, filename)

        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)

        return True, filepath
    except Exception as e:
        return False, str(e)



def build_app_index():
    print("\n⚡ STARTING FULL SYSTEM SCAN (This happens once)...")
    print("   Please wait, looking for apps and games...")
    
    app_map = {}

    # 1. ADD CUSTOM APPS
    app_map.update(MY_CUSTOM_APPS)

    # 2. ADD SYSTEM COMMANDS
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

    # 3. SCAN START MENU & DESKTOP (Shortcuts)
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

    # 4. DEEP SCAN PROGRAM FILES (The "Heavy" Logic)
    print("   - Scanning Program Files (Deep Search)...")
    
    search_roots = [
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
    ]

    skip_keywords = ["uninstall", "setup", "update", "helper", "crash", "installer", "framework", "service", "system32"]

    for root_dir in search_roots:
        if not root_dir or not os.path.exists(root_dir): continue
        
        for root, dirs, files in os.walk(root_dir):
            # Optimization: Skip huge system folders
            if "Windows" in root or "Common Files" in root: 
                continue
                
            for file in files:
                if file.lower().endswith(".exe"):
                    name = file.lower().replace(".exe", "")
                    
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
    if os.path.exists(APP_INDEX_FILE):
        try:
            print("📂 Loading app database...")
            with open(APP_INDEX_FILE, "r") as f:
                data = json.load(f)
                print(f"✅ Loaded {len(data)} apps from cache.")
                return data
        except:
            print("⚠️ Database corrupt. Rebuilding...")
    
    return build_app_index()

APP_INDEX = load_app_index()


def open_app(app_name):
    if not app_name:
        return False, "no app name"

    query = app_name.lower().strip()

    if query in APP_INDEX:
        try:
            os.startfile(APP_INDEX[query])
            return True, query
        except Exception as e:
            return False, str(e)

    matches = difflib.get_close_matches(query, APP_INDEX.keys(), n=1, cutoff=0.4)
    if matches:
        best = matches[0]
        try:
            os.startfile(APP_INDEX[best])
            return True, best
        except Exception as e:
            return False, str(e)

    return False, f"not_found:{app_name}"

def ask_llm(user_input):
    prompt = f"""
    Act as a desktop assistant. Return JSON ONLY.

    Personality: {PERSONALITY}
    
    1. APP CONTROL: {{ "action": "open_app", "app_name": "name" }}
    
    2. SYSTEM CONTROL (Volume/Brightness):
       - Extract the number (0-100). If user says "max", use 100. "Mute" is 0.
       - "Set volume to 50%" -> {{ "action": "set_volume", "value": 50 }}
       - "Brightness 20" -> {{ "action": "set_brightness", "value": 20 }}
    
    3. SCREENSHOT:
       - "Take a screenshot" -> {{ "action": "take_screenshot" }}
    
    4. SEARCH SPECIFIC SITE: 
       - "Search Amazon for ps5" -> {{ "action": "open_website", "url": "https://www.amazon.com/s?k=ps5" }}
    
    5. GENERAL SEARCH: {{ "action": "google_search", "query": "your query" }}

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

def chat_mode():
    print("\n💬 Entered CHAT MODE. (Type 'relax ezio' to return to menu)")
    chat_history = [
        {"role": "system", "content": f"You are Ezio, a helpful and intelligent AI assistant. {PERSONALITY} Keep answers concise."}
    ]
    
    while True:
        user_input = input("Ezio (Chat): ").strip()
        if not user_input: continue
        
        if user_input.lower() == "relax ezio":
            print("Returning to main menu...")
            break
            
        chat_history.append({"role": "user", "content": user_input})
        
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=chat_history,
                temperature=0.7
            )
            reply = response.choices[0].message.content.strip()
            print(f"Ezio: {reply}")
            chat_history.append({"role": "assistant", "content": reply})
            
        except Exception as e:
            print(f"❌ Chat Error: {e}")

def assist_mode():
    print("\n🤖 Entered ASSIST MODE. (Type 'relax ezio' to return to menu)")
    print("• Try: 'Set volume to 50%', 'Open Notepad', 'Search Google'")
    
    while True:
        user_input = input("Ezio (Assist): ").strip()
        if not user_input: continue
        
        if user_input.lower() == "relax ezio":
            print("Returning to main menu...")
            break
        
        if user_input.lower() == "refresh":
            global APP_INDEX
            APP_INDEX = build_app_index() 
            continue

        data = ask_llm(user_input)
        
        if data:
            action = data.get("action")

            if action == "open_app":
                ok, info = open_app(data.get("app_name"))
                if ok:
                    print(persona_response('open_app_ok', name=info))
                else:
                    if isinstance(info, str) and info.startswith("not_found:"):
                        name = info.split(":", 1)[1]
                        print(persona_response('open_app_not_found', name=name))
                    else:
                        print(persona_response('error', msg=info))

            elif action == "open_website":
                webbrowser.open(data.get("url"))
                print(persona_response('open_website'))

            elif action == "google_search":
                query = data.get('query')
                webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")
                print(persona_response('google_search', query=query))

            elif action == "set_volume":
                ok, info = set_system_volume(data.get("value"))
                if ok:
                    print(persona_response('volume', value=info))
                else:
                    print(persona_response('error', msg=info))

            elif action == "set_brightness":
                ok, info = set_system_brightness(data.get("value"))
                if ok:
                    print(persona_response('brightness', value=info))
                else:
                    print(persona_response('error', msg=info))

            elif action == "take_screenshot":
                ok, info = take_screenshot()
                if ok:
                    print(persona_response('screenshot', path=info))
                else:
                    print(persona_response('error', msg=info))

            else:
                print(persona_response('unknown'))

def main_menu():
    print("\n===========================================")
    print(" 🦅 EZIO AI ASSISTANT (v3.0 - State Machine)")
    print("===========================================")
    print("Select a mode:")
    print("1. Type 'Chat' for Conversation Mode")
    print("2. Type 'Assist' for Desktop Control Mode")
    print("3. Type 'Exit' to quit")
    
    while True:
        choice = input("\nMenu > ").strip().lower()
        
        if choice == "chat":
            chat_mode()
        elif choice == "assist":
            assist_mode()
        elif choice in ["exit", "quit"]:
            print("Goodbye!")
            break
        else:
            print("❌ Invalid option. Please type 'Chat', 'Assist', or 'Exit'.")

if __name__ == "__main__":
    main_menu()