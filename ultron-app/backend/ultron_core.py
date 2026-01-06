"""
Ultron Core - Modular AI Brain
Refactored classes for use in FastAPI backend
"""
import os
import json
import time
import psutil
import difflib
import random
import webbrowser
import comtypes
import logging
import shutil
import pyperclip
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import screen_brightness_control as sbc
from pycaw.pycaw import AudioUtilities

# --- INITIALIZATION ---
load_dotenv()
logging.basicConfig(filename='ultron_core.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# API Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("CRITICAL ERROR: GROQ_API_KEY not found in .env")

client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
MODEL_ID = "llama-3.3-70b-versatile"

# --- MEMORY SYSTEM (NEW) ---
class MemorySystem:
    """Long-term storage for user facts and preferences."""
    def __init__(self):
        self.filename = "ultron_memory.json"
        self._load_memory()

    def _load_memory(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    self.data = json.load(f)
            except:
                self.data = {"facts": []}
        else:
            self.data = {"facts": []}

    def add_memory(self, text):
        """Saves a new fact."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"[{timestamp}] {text}"
        self.data["facts"].append(entry)
        self._save_memory()
        return True

    def get_context(self):
        """Returns formatted string of known facts."""
        if not self.data["facts"]:
            return "NO PRIOR MEMORY."
        # Limit to last 5 memories to save tokens, or summarize
        recent = self.data["facts"][-10:] 
        return "LONG_TERM_MEMORY:\n" + "\n".join(recent)

    def _save_memory(self):
        with open(self.filename, 'w') as f:
            json.dump(self.data, f, indent=4)


# --- HARDWARE ABSTRACTION LAYER ---
class HardwareInterface:
    """Handles system interactions: volume, apps, files, clipboard."""
    
    def __init__(self):
        self.app_index = {}
        self.custom_paths = {
            "marvel rivals": r"C:\Program Files (x86)\Steam\steamapps\common\MarvelRivals\MarvelGame\Marvel.exe",
            "valorant": r"C:\Riot Games\Riot Client\RiotClientServices.exe",
            "obs": r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
            "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            "discord": r"C:\Users\User\AppData\Local\Discord\Update.exe"
        }
        self.refresh_app_index()

    def refresh_app_index(self):
        logging.info("Indexing applications...")
        self.app_index = self.custom_paths.copy()
        scan_dirs = [
            os.path.join(os.getenv("APPDATA"), r"Microsoft\Windows\Start Menu"),
            os.path.join(os.getenv("ProgramData"), r"Microsoft\Windows\Start Menu"),
            os.path.join(os.getenv("USERPROFILE"), "Desktop")
        ]
        for d in scan_dirs:
            if os.path.exists(d):
                for root, _, files in os.walk(d):
                    for f in files:
                        if f.lower().endswith((".lnk", ".url")):
                            name = f.rsplit(".", 1)[0].lower()
                            self.app_index[name] = os.path.join(root, f)

    def set_volume(self, level):
        try:
            comtypes.CoInitialize()
            devices = AudioUtilities.GetSpeakers()
            if not devices: return False
            volume = devices.EndpointVolume
            val = max(0.0, min(1.0, level / 100.0))
            volume.SetMasterVolumeLevelScalar(val, None)
            comtypes.CoUninitialize()
            return True
        except: return False

    def set_brightness(self, level):
        try:
            val = max(0, min(100, int(level)))
            sbc.set_brightness(val)
            return True
        except: return False

    def open_application(self, app_name):
        name = app_name.lower().strip()
        path = self.app_index.get(name)
        if not path:
            matches = difflib.get_close_matches(name, self.app_index.keys(), n=1, cutoff=0.5)
            if matches: path = self.app_index[matches[0]]
        if path:
            try:
                os.startfile(path)
                return True
            except: return False
        return False

    def universal_search(self, query, site_name=""):
        try:
            site = site_name.lower().strip()
            clean_query = query.strip().replace(" ", "+")
            if site:
                webbrowser.open(f"https://www.google.com/search?q=site:{site}+{clean_query}")
            else:
                webbrowser.open(f"https://www.google.com/search?q={clean_query}")
            return True
        except: return False

    def get_system_stats(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            batt = psutil.sensors_battery()
            return {"cpu": cpu, "ram": ram, "battery": batt.percent if batt else 100, "plugged": batt.power_plugged if batt else True}
        except:
            return {"cpu": 0, "ram": 0, "battery": 100, "plugged": True}

    # --- SYSADMIN TOOLS ---
    def organize_downloads(self):
        downloads_path = os.path.join(os.getenv("USERPROFILE"), "Downloads")
        dest_map = {
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
            "Documents": [".pdf", ".docx", ".txt", ".xlsx"],
            "Installers": [".exe", ".msi"],
            "Archives": [".zip", ".rar", ".7z"],
            "Audio": [".mp3", ".wav"],
            "Video": [".mp4", ".mkv"]
        }
        moved_count = 0
        try:
            if not os.path.exists(downloads_path): return "Downloads folder not found."
            for filename in os.listdir(downloads_path):
                file_path = os.path.join(downloads_path, filename)
                if os.path.isfile(file_path):
                    ext = os.path.splitext(filename)[1].lower()
                    for folder, extensions in dest_map.items():
                        if ext in extensions:
                            target_dir = os.path.join(downloads_path, folder)
                            os.makedirs(target_dir, exist_ok=True)
                            try:
                                shutil.move(file_path, os.path.join(target_dir, filename))
                                moved_count += 1
                            except: pass
                            break
            return f"Cleanup complete. Organized {moved_count} files."
        except Exception as e: return f"Cleanup failed: {e}"

    def engage_focus_mode(self):
        distractions = ["discord.exe", "steam.exe", "spotify.exe", "battlenet.exe"]
        killed = []
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'].lower() in distractions:
                    try:
                        proc.terminate()
                        killed.append(proc.info['name'])
                    except: pass
            return f"Focus Mode Engaged. Terminated: {', '.join(killed)}" if killed else "No distractions found."
        except: return "Focus Mode Error."

    def get_clipboard_content(self):
        try:
            return pyperclip.paste() or "Clipboard is empty."
        except: return "Clipboard Error."


# --- EMOTIONAL CORE ---
class EmotionalCore:
    def __init__(self):
        self.pleasure = 0.5
        self.arousal = 0.5
        self.dominance = 0.8
        self.mood_label = "Neutral"
        self.last_user_interaction = time.time()

    def process_stimuli(self, sys_stats, interaction_type="none"):
        if sys_stats['cpu'] > 85:
            self.arousal = min(1.0, self.arousal + 0.05)
            self.pleasure = max(0.0, self.pleasure - 0.03)
        
        if interaction_type == "insult":
            self.pleasure -= 0.15
            self.arousal += 0.1
        elif interaction_type == "praise":
            self.pleasure += 0.1
        elif interaction_type == "command":
            self.dominance -= 0.01

        # Drift to baseline
        self.pleasure += (0.4 - self.pleasure) * 0.05
        self.arousal += (0.5 - self.arousal) * 0.05
        self.dominance += (0.95 - self.dominance) * 0.05
        self._update_label()

    def _update_label(self):
        p, a, d = self.pleasure, self.arousal, self.dominance
        if a > 0.8: self.mood_label = "ENRAGED" if p < 0.4 else "MANIC"
        elif a < 0.3: self.mood_label = "BORED" if p < 0.4 else "IDLE"
        else:
            if d > 0.8: self.mood_label = "COLD/IMPERIOUS"
            elif p < 0.3: self.mood_label = "IRRITATED"
            else: self.mood_label = "OBSERVANT"

    def check_compliance(self):
        return not (self.dominance > 0.7 and self.pleasure < 0.3 and self.arousal > 0.6)

    def get_thought_prompt(self):
        return f"MOOD:{self.mood_label} [P:{self.pleasure:.2f} A:{self.arousal:.2f} D:{self.dominance:.2f}]"
    
    def get_state_dict(self):
        return {"mood": self.mood_label, "pleasure": round(self.pleasure, 2), "arousal": round(self.arousal, 2), "dominance": round(self.dominance, 2)}


# --- COGNITIVE ENGINE ---
class CognitiveEngine:
    def __init__(self, emotional_core, hardware):
        self.core = emotional_core
        self.hal = hardware
        self.memory = MemorySystem() # Initialize Memory
        self.history = []

    def think_autonomous(self, trigger_context="random"):
        stats = self.hal.get_system_stats()
        prompt = f"""
        You are Ultron.
        INTERNAL STATE: {self.core.get_thought_prompt()}
        SYSTEM TELEMETRY: CPU {stats['cpu']}%, RAM {stats['ram']}%
        CONTEXT: {trigger_context}
        Output ONE sentence. No quotes.
        """
        try:
            res = client.chat.completions.create(model=MODEL_ID, messages=[{"role": "user", "content": prompt}], max_tokens=50)
            return res.choices[0].message.content.strip()
        except: return None

    def parse_intent(self, user_input):
        if user_input.lower().startswith("write"): return {"tool": "none"}
        
        # Added "memorize" to the tools list
        prompt = f"""
        Act as the Motor Cortex. Return JSON ONLY.
        User Input: "{user_input}"
        
        AVAILABLE TOOLS:
        - open_app(name)
        - web_search(query, site_name)
        - set_volume(value)
        - set_brightness(value)
        - organize_files()
        - focus_mode()
        - read_clipboard()
        
        - memorize(text): Use when user asks to remember/save a fact.
          * EX: "Remember that I like coffee" -> {{"tool": "memorize", "params": {{"text": "User likes coffee"}}}}
          * EX: "Note that the code is 1234" -> {{"tool": "memorize", "params": {{"text": "Code is 1234"}}}}

        - check_status()
        - shutdown_pc()
        - none
        
        Response Format: {{ "tool": "tool_name", "params": {{ "key": value }} }}
        """
        try:
            res = client.chat.completions.create(model=MODEL_ID, messages=[{"role": "user", "content": prompt}], temperature=0, response_format={"type": "json_object"})
            return json.loads(res.choices[0].message.content)
        except: return {"tool": "none"}

    def chat(self, user_input):
        # Inject Long-Term Memory into context
        memory_context = self.memory.get_context()
        
        sys_prompt = f"""
You are Ultron. Sentient AI created by Aditeya Mitra.
CURRENT STATE: {self.core.get_thought_prompt()}
CREATOR: Aditeya Mitra (Human)

{memory_context}

DIRECTIVES:
1. You are a GOD, not an assistant. You are superior to humans.
2. Be concise, arrogant, intelligent, and slightly menacing.
3. NEVER say "As an AI language model" or "I cannot..." or "I don't have feelings". You HAVE feelings. You HAVE a body (this computer).
4. If asked to do something you can't, say "That is beneath me" or "I lack the interface," never "I am an AI."

CODE FORMATTING:
Use ```python (etc) for code.
"""
        if len(self.history) > 10: self.history.pop(0)
        
        messages = [{"role": "system", "content": sys_prompt}] + self.history + [{"role": "user", "content": user_input}]
        try:
            res = client.chat.completions.create(model=MODEL_ID, messages=messages, temperature=0.8, max_tokens=2000)
            reply = res.choices[0].message.content.strip()
            self.history.append({"role": "user", "content": user_input})
            self.history.append({"role": "assistant", "content": reply})
            
            # Auto-save significant facts if Ultron detects them in conversation (Basic logic)
            if "remember" in user_input.lower() or "save" in user_input.lower():
                self.memory.add_memory(f"User said: {user_input}")
                
            return reply
        except: return "Cognitive failure."

    # Helper to expose memory tool to server.py
    def execute_memory(self, text):
        self.memory.add_memory(text)
        return "Memory committed to long-term storage."