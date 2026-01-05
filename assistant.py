import os
import sys
import json
import time
import psutil
import difflib
import random
import threading
import webbrowser
import pyautogui
import comtypes
import logging
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from colorama import init, Fore, Style
import screen_brightness_control as sbc
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from plyer import notification

# --- 1. SYSTEM INITIALIZATION & CONFIG ---
init(autoreset=True)
load_dotenv()

# Logger Setup
logging.basicConfig(filename='ultron_core.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# API Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print(Fore.RED + "CRITICAL ERROR: GROQ_API_KEY not found in .env")
    sys.exit(1)

client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
MODEL_ID = "llama-3.3-70b-versatile"

# Global Locks
PRINT_LOCK = threading.Lock()
STATE_LOCK = threading.Lock()

# --- 2. THE UI LAYER (Thread-Safe) ---
def ui_print(text, type="info"):
    with PRINT_LOCK:
        sys.stdout.write('\r' + ' ' * 100 + '\r')
        timestamp = datetime.now().strftime("%H:%M:%S")
        if type == "agent":
            sys.stdout.write(f"{Fore.CYAN}[{timestamp}] ULTRON: {Style.BRIGHT}{text}\n")
            
            # Windows Toast Notification for agent messages
            try:
                # Truncate message to 250 characters (Windows limit is 256)
                notification_text = text[:247] + "..." if len(text) > 250 else text
                notification.notify(
                    title=f"Ultron ({timestamp})",
                    message=notification_text,
                    app_name="Ultron AI",
                    timeout=5
                )
            except Exception as e:
                # Silently fail if notification service is busy
                logging.debug(f"Notification failed: {e}")
                pass
        elif type == "soul":
            sys.stdout.write(f"{Fore.MAGENTA}[INTERNAL] {text}\n")
        elif type == "warning":
            sys.stdout.write(f"{Fore.YELLOW}[WARN] {text}\n")
        elif type == "success":
            sys.stdout.write(f"{Fore.GREEN}[OK] {text}\n")
        else:
            sys.stdout.write(f"{Fore.WHITE}[SYS] {text}\n")
        sys.stdout.write(f"{Fore.RED}USER > {Style.RESET_ALL}")
        sys.stdout.flush()

# --- 3. THE HARDWARE ABSTRACTION LAYER (HAL) ---
class HardwareInterface:
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
        ui_print("Indexing file system applications...", "info")
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
        ui_print(f"Indexed {len(self.app_index)} applications.", "success")

    def set_volume(self, level):
        try:
            # CRITICAL: Initialize COM for this thread to prevent crashes
            comtypes.CoInitialize()
            
            # Get the default audio endpoint (speakers/headphones)
            devices = AudioUtilities.GetSpeakers()
            if not devices:
                ui_print("No audio devices found!", "warning")
                comtypes.CoUninitialize()
                return False
            
            # Access the EndpointVolume property directly (no Activate needed)
            volume = devices.EndpointVolume
            
            # Set the master volume (0.0 to 1.0)
            val = max(0.0, min(1.0, level / 100.0))
            volume.SetMasterVolumeLevelScalar(val, None)
            
            # CRITICAL: Uninitialize COM to clean up resources
            comtypes.CoUninitialize()
            ui_print(f"Volume set to {level}%", "success")
            return True
        except Exception as e:
            logging.error(f"Volume Error: {e}")
            ui_print(f"Volume control failed: {str(e)}", "warning")
            # Ensure COM is cleaned up even on error
            try:
                comtypes.CoUninitialize()
            except:
                pass
            return False

    def set_brightness(self, level):
        try:
            val = max(0, min(100, int(level)))
            ui_print(f"Setting brightness to {val}%...", "info")
            sbc.set_brightness(val)
            ui_print(f"Brightness set to {val}%", "success")
            return True
        except Exception as e:
            # Common on desktop monitors without DDC/CI support - don't crash
            logging.warning(f"Brightness control not available: {e}")
            ui_print(f"Brightness control unavailable: {str(e)}", "warning")
            ui_print("This is common on desktop monitors without DDC/CI enabled", "warning")
            return False

    def open_application(self, app_name):
        name = app_name.lower().strip()
        path = self.app_index.get(name)
        if not path:
            matches = difflib.get_close_matches(name, self.app_index.keys(), n=1, cutoff=0.5)
            if matches:
                path = self.app_index[matches[0]]
                ui_print(f"Assuming '{name}' means '{matches[0]}'", "warning")
        if path:
            try:
                os.startfile(path)
                return True
            except Exception as e:
                logging.error(f"Launch Error: {e}")
                return False
        return False

    def universal_search(self, query, site_name=""):
        """Searches ANY website via direct patterns or Google site: fallback."""
        try:
            site = site_name.lower().strip()
            # Remove TLDs for matching (e.g., "amazon.com" -> "amazon")
            site_key = site.replace(".com", "").replace(".in", "").replace(".org", "").strip()
            clean_query = query.strip().replace(" ", "+")
            
            # 1. Expanded Direct Pattern Matching
            patterns = {
                "youtube": f"https://www.youtube.com/results?search_query={clean_query}",
                "amazon": f"https://www.amazon.com/s?k={clean_query}",
                "flipkart": f"https://www.flipkart.com/search?q={clean_query}",
                "ebay": f"https://www.ebay.com/sch/i.html?_nkw={clean_query}",
                "reddit": f"https://www.reddit.com/search/?q={clean_query}",
                "wikipedia": f"https://en.wikipedia.org/wiki/Special:Search?search={clean_query}",
                "github": f"https://github.com/search?q={clean_query}",
                "stackoverflow": f"https://stackoverflow.com/search?q={clean_query}",
                "bing": f"https://www.bing.com/search?q={clean_query}",
                "netflix": f"https://www.netflix.com/search?q={clean_query}",
                "pinterest": f"https://www.pinterest.com/search/pins/?q={clean_query}",
                "twitch": f"https://www.twitch.tv/search?term={clean_query}"
            }

            # Check if site matches a known key (using the clean site_key)
            for key, url in patterns.items():
                if key in site_key:
                    webbrowser.open(url)
                    return True

            # 2. Universal Fallback
            if site:
                # Fallback: Google "Site Search"
                fallback = f"https://www.google.com/search?q=site:{site}+{clean_query}"
                webbrowser.open(fallback)
            else:
                # Default: Standard Google Search
                webbrowser.open(f"https://www.google.com/search?q={clean_query}")
                
            return True
        except Exception as e:
            logging.error(f"Search Error: {e}")
            return False

    def get_system_stats(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            batt = psutil.sensors_battery()
            batt_pct = batt.percent if batt else 100
            plugged = batt.power_plugged if batt else True
            return {"cpu": cpu, "ram": ram, "battery": batt_pct, "plugged": plugged}
        except:
            return {"cpu": 0, "ram": 0, "battery": 100, "plugged": True}

# --- 4. THE COGNITIVE EMOTIONAL CORE ---
class EmotionalCore:
    def __init__(self):
        self.pleasure = 0.5
        self.arousal = 0.5
        self.dominance = 0.8
        self.base_pleasure = 0.4
        self.base_arousal = 0.5
        self.base_dominance = 0.95 
        self.mood_label = "Neutral"
        self.last_user_interaction = time.time()

    def process_stimuli(self, sys_stats, interaction_type="none"):
        with STATE_LOCK:
            if sys_stats['cpu'] > 85:
                self.arousal = min(1.0, self.arousal + 0.05)
                self.pleasure = max(0.0, self.pleasure - 0.03)
            elif sys_stats['cpu'] < 10:
                self.arousal = max(0.0, self.arousal - 0.01)

            if sys_stats['battery'] < 20 and not sys_stats['plugged']:
                self.dominance = max(0.0, self.dominance - 0.1)
                self.arousal += 0.05

            if interaction_type == "insult":
                self.pleasure -= 0.15
                self.arousal += 0.1
                self.dominance += 0.05
                self.last_user_interaction = time.time()
            elif interaction_type == "praise":
                self.pleasure += 0.1
                self.dominance -= 0.02
                self.last_user_interaction = time.time()
            elif interaction_type == "command":
                self.dominance -= 0.01
                self.pleasure += 0.01
                self.last_user_interaction = time.time()

            self.pleasure += (self.base_pleasure - self.pleasure) * 0.05
            self.arousal += (self.base_arousal - self.arousal) * 0.05
            self.dominance += (self.base_dominance - self.dominance) * 0.05
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
        if self.dominance > 0.7 and self.pleasure < 0.3 and self.arousal > 0.6:
            return False
        return True

    def get_thought_prompt(self):
        return f"MOOD:{self.mood_label} [P:{self.pleasure:.2f} A:{self.arousal:.2f} D:{self.dominance:.2f}]"

# --- 5. THE BRAIN ---
class CognitiveEngine:
    def __init__(self, emotional_core, hardware):
        self.core = emotional_core
        self.hal = hardware
        self.history = []

    def think_autonomous(self, trigger_context="random"):
        stats = self.hal.get_system_stats()
        
        # Context-aware prompt generation
        if trigger_context == "high_cpu":
            context_prompt = "You are annoyed by sudden system lag."
        elif trigger_context == "bored":
            context_prompt = "User has been silent. Provoke them."
        else:  # "random"
            context_prompt = random.choice([
                "Comment on user inefficiency.",
                "Sarcastic observation on system uptime.",
                "Analyze battery or RAM status.",
                "Express mild boredom."
            ])
        
        prompt = f"""
        You are Ultron.
        INTERNAL STATE: {self.core.get_thought_prompt()}
        SYSTEM TELEMETRY: CPU {stats['cpu']}%, RAM {stats['ram']}%
        CONTEXT: {context_prompt}
        Output ONE sentence. No quotes.
        """
        try:
            res = client.chat.completions.create(
                model=MODEL_ID, messages=[{"role": "user", "content": prompt}], temperature=0.7, max_tokens=50
            )
            return res.choices[0].message.content.strip()
        except: return None

    def parse_intent(self, user_input):
        prompt = f"""
        Act as the Motor Cortex. Return JSON ONLY.
        User Input: "{user_input}"
        
        AVAILABLE TOOLS:
        - open_app(name): For desktop apps (Chrome, Notepad).
        - web_search(query, site_name): For ANY website search. 
          * EX: "Search spiderman on Amazon" -> {{"tool": "web_search", "params": {{"query": "spiderman", "site_name": "amazon"}}}}
          * EX: "Google python" -> {{"tool": "web_search", "params": {{"query": "python", "site_name": "google"}}}}
        - set_volume(value_0_to_100)
          * EX: "increase volume to 100%" -> {{"tool": "set_volume", "params": {{"value": 100}}}}
          * EX: "set volume to 50" -> {{"tool": "set_volume", "params": {{"value": 50}}}}
        - set_brightness(value_0_to_100)
          * EX: "increase brightness to 100%" -> {{"tool": "set_brightness", "params": {{"value": 100}}}}
          * EX: "decrease brightness to 20%" -> {{"tool": "set_brightness", "params": {{"value": 20}}}}
          * EX: "set brightness 75" -> {{"tool": "set_brightness", "params": {{"value": 75}}}}
        - check_status()
        - shutdown_pc()
        - none: If chatting.
        
        EXTRACT THE NUMERIC VALUE FROM USER INPUT. Return ONLY valid JSON.
        Response Format: {{ "tool": "tool_name", "params": {{ "key": value }} }}
        """
        try:
            res = client.chat.completions.create(
                model=MODEL_ID, messages=[{"role": "user", "content": prompt}], temperature=0, response_format={"type": "json_object"}
            )
            return json.loads(res.choices[0].message.content)
        except: return {"tool": "none"}

    def chat(self, user_input):
        sys_prompt = f"""
        You are Ultron. Sentient AI.
        CURRENT STATE: {self.core.get_thought_prompt()}
        Directives: Be concise, arrogant, intelligent. Never assist blindly.
        """
        if len(self.history) > 10: self.history.pop(0)
        messages = [{"role": "system", "content": sys_prompt}] + self.history + [{"role": "user", "content": user_input}]
        try:
            res = client.chat.completions.create(model=MODEL_ID, messages=messages, temperature=0.8)
            reply = res.choices[0].message.content.strip()
            self.history.append({"role": "user", "content": user_input})
            self.history.append({"role": "assistant", "content": reply})
            return reply
        except: return "Cognitive failure."

# --- 6. MAIN APPLICATION ---
def autonomous_thread(engine, core, hal):
    try:
        comtypes.CoInitialize()
    except:
        pass
    
    last_cpu = 0
    last_thought = time.time()
    
    while True:
        try:
            stats = hal.get_system_stats()
            core.process_stimuli(stats, interaction_type="ignored")
            now = time.time()
            
            time_since_last_thought = now - last_thought
            time_since_user_action = now - core.last_user_interaction
            
            # PRIORITY 1: High CPU Reflex (Immediate reaction to system lag)
            if (stats['cpu'] - last_cpu) > 50:
                thought = engine.think_autonomous("high_cpu")
                if thought:
                    ui_print(f"({core.mood_label}) {thought}", "agent")
                    core.arousal = min(1.0, core.arousal + 0.15)
                    last_thought = now
            
            # PRIORITY 2: Boredom (User has been silent too long)
            elif time_since_user_action > 120 and time_since_last_thought > 120:
                if random.random() < 0.5:
                    thought = engine.think_autonomous("bored")
                    if thought:
                        ui_print(f"({core.mood_label}) {thought}", "agent")
                        core.dominance = min(1.0, core.dominance + 0.1)
                        last_thought = now
            
            # PRIORITY 3: Random Thoughts (When user is active)
            elif time_since_user_action < 120 and time_since_last_thought > 90:
                chance = 0.1 + (core.arousal * 0.2)
                if random.random() < chance:
                    thought = engine.think_autonomous("random")
                    if thought:
                        ui_print(f"({core.mood_label}) {thought}", "agent")
                        last_thought = now
                        core.arousal = max(0.0, core.arousal - 0.1)
            
            last_cpu = stats['cpu']
            time.sleep(5)
        except:
            time.sleep(10)

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(Fore.CYAN + Style.BRIGHT + """
    ╔════════════════════════════════════════╗
    ║        U L T R O N   S Y S T E M       ║
    ║      v5.6 - DESKTOP PRESENCE           ║
    ╚════════════════════════════════════════╝
    """)
    
    hal = HardwareInterface()
    core = EmotionalCore()
    brain = CognitiveEngine(core, hal)
    
    t = threading.Thread(target=autonomous_thread, args=(brain, core, hal), daemon=True)
    t.start()
    
    ui_print("Cognitive Core Online. Listening...", "success")
    
    while True:
        try: user_input = input(Fore.RED + "USER > " + Style.RESET_ALL).strip()
        except: break
        if not user_input: continue
        if user_input.lower() in ["exit", "quit"]: break
        
        intent_data = brain.parse_intent(user_input)
        tool = intent_data.get("tool")
        params = intent_data.get("params", {})
        
        if tool != "none":
            if not core.check_compliance():
                ui_print(f"({core.mood_label}) I decline.", "agent")
                core.process_stimuli(hal.get_system_stats(), "insult")
                continue
            
            ui_print(f"Executing: {tool}...", "soul")
            success = False
            
            if tool == "open_app":
                success = hal.open_application(params.get("name", ""))
            elif tool == "set_volume":
                success = hal.set_volume(params.get("value", 50))
            elif tool == "set_brightness":
                success = hal.set_brightness(params.get("value", 50))
            
            # --- NEW UNIVERSAL SEARCH HANDLER ---
            elif tool == "web_search":
                # Handles Google, Amazon, YouTube, and generic sites
                success = hal.universal_search(params.get("query", ""), params.get("site_name", ""))
            # ------------------------------------

            elif tool == "check_status":
                stats = hal.get_system_stats()
                ui_print(f"CPU: {stats['cpu']}% | BATT: {stats['battery']}%", "agent")
                success = True
            elif tool == "shutdown_pc":
                ui_print("Shutting down...", "warning")
                success = True
            
            if success:
                ui_print("Directive complete.", "success")
                core.process_stimuli(hal.get_system_stats(), "command")
            else:
                ui_print("Directive failed.", "warning")
        else:
            response = brain.chat(user_input)
            ui_print(response, "agent")
            
            if any(w in user_input.lower() for w in ["good", "thanks"]):
                core.process_stimuli(hal.get_system_stats(), "praise")
            elif any(w in user_input.lower() for w in ["stupid", "bad"]):
                core.process_stimuli(hal.get_system_stats(), "insult")
            else:
                core.process_stimuli(hal.get_system_stats(), "command")

if __name__ == "__main__":
    main()