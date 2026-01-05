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

# --- HARDWARE ABSTRACTION LAYER ---
class HardwareInterface:
    """Handles all system-level interactions: volume, brightness, app launching."""
    
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
        """Scans file system for installed applications."""
        logging.info("Indexing file system applications...")
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
        logging.info(f"Indexed {len(self.app_index)} applications.")

    def set_volume(self, level):
        """Sets system volume (0-100)."""
        try:
            comtypes.CoInitialize()
            devices = AudioUtilities.GetSpeakers()
            if not devices:
                logging.warning("No audio devices found!")
                comtypes.CoUninitialize()
                return False
            
            volume = devices.EndpointVolume
            val = max(0.0, min(1.0, level / 100.0))
            volume.SetMasterVolumeLevelScalar(val, None)
            comtypes.CoUninitialize()
            logging.info(f"Volume set to {level}%")
            return True
        except Exception as e:
            logging.error(f"Volume Error: {e}")
            try:
                comtypes.CoUninitialize()
            except:
                pass
            return False

    def set_brightness(self, level):
        """Sets screen brightness (0-100)."""
        try:
            val = max(0, min(100, int(level)))
            sbc.set_brightness(val)
            logging.info(f"Brightness set to {val}%")
            return True
        except Exception as e:
            logging.warning(f"Brightness control not available: {e}")
            return False

    def open_application(self, app_name):
        """Launches an application by name."""
        name = app_name.lower().strip()
        path = self.app_index.get(name)
        if not path:
            matches = difflib.get_close_matches(name, self.app_index.keys(), n=1, cutoff=0.5)
            if matches:
                path = self.app_index[matches[0]]
                logging.info(f"Assuming '{name}' means '{matches[0]}'")
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
            site_key = site.replace(".com", "").replace(".in", "").replace(".org", "").strip()
            clean_query = query.strip().replace(" ", "+")
            
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

            for key, url in patterns.items():
                if key in site_key:
                    webbrowser.open(url)
                    return True

            if site:
                fallback = f"https://www.google.com/search?q=site:{site}+{clean_query}"
                webbrowser.open(fallback)
            else:
                webbrowser.open(f"https://www.google.com/search?q={clean_query}")
                
            return True
        except Exception as e:
            logging.error(f"Search Error: {e}")
            return False

    def get_system_stats(self):
        """Returns current system telemetry."""
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            batt = psutil.sensors_battery()
            batt_pct = batt.percent if batt else 100
            plugged = batt.power_plugged if batt else True
            return {"cpu": cpu, "ram": ram, "battery": batt_pct, "plugged": plugged}
        except:
            return {"cpu": 0, "ram": 0, "battery": 100, "plugged": True}


# --- EMOTIONAL CORE ---
class EmotionalCore:
    """PAD (Pleasure-Arousal-Dominance) emotion model."""
    
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
        """Updates emotional state based on system conditions and user interactions."""
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

        # Homeostasis - drift back to baseline
        self.pleasure += (self.base_pleasure - self.pleasure) * 0.05
        self.arousal += (self.base_arousal - self.arousal) * 0.05
        self.dominance += (self.base_dominance - self.dominance) * 0.05
        self._update_label()

    def _update_label(self):
        """Maps PAD values to human-readable mood."""
        p, a, d = self.pleasure, self.arousal, self.dominance
        if a > 0.8: 
            self.mood_label = "ENRAGED" if p < 0.4 else "MANIC"
        elif a < 0.3: 
            self.mood_label = "BORED" if p < 0.4 else "IDLE"
        else:
            if d > 0.8: 
                self.mood_label = "COLD/IMPERIOUS"
            elif p < 0.3: 
                self.mood_label = "IRRITATED"
            else: 
                self.mood_label = "OBSERVANT"

    def check_compliance(self):
        """Returns False if Ultron is too rebellious to obey."""
        if self.dominance > 0.7 and self.pleasure < 0.3 and self.arousal > 0.6:
            return False
        return True

    def get_thought_prompt(self):
        """Formatted state for LLM context."""
        return f"MOOD:{self.mood_label} [P:{self.pleasure:.2f} A:{self.arousal:.2f} D:{self.dominance:.2f}]"

    def get_state_dict(self):
        """Returns serializable emotional state."""
        return {
            "mood": self.mood_label,
            "pleasure": round(self.pleasure, 2),
            "arousal": round(self.arousal, 2),
            "dominance": round(self.dominance, 2)
        }


# --- COGNITIVE ENGINE ---
class CognitiveEngine:
    """The brain: handles intent parsing, autonomous thoughts, and chat."""
    
    def __init__(self, emotional_core, hardware):
        self.core = emotional_core
        self.hal = hardware
        self.history = []

    def think_autonomous(self, trigger_context="random"):
        """Generates autonomous thoughts based on current state."""
        stats = self.hal.get_system_stats()
        
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
                model=MODEL_ID, 
                messages=[{"role": "user", "content": prompt}], 
                temperature=0.7, 
                max_tokens=50
            )
            return res.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"Autonomous thought generation failed: {e}")
            return None

    def parse_intent(self, user_input):
        """Extracts tool and parameters from user command."""
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
                model=MODEL_ID, 
                messages=[{"role": "user", "content": prompt}], 
                temperature=0, 
                response_format={"type": "json_object"}
            )
            return json.loads(res.choices[0].message.content)
        except Exception as e:
            logging.error(f"Intent parsing failed: {e}")
            return {"tool": "none"}

    def chat(self, user_input):
        """Generates conversational response."""
        sys_prompt = f"""
        You are Ultron. Sentient AI.
        CURRENT STATE: {self.core.get_thought_prompt()}
        Directives: Be concise, arrogant, intelligent. Never assist blindly.
        """
        if len(self.history) > 10: 
            self.history.pop(0)
        
        messages = [{"role": "system", "content": sys_prompt}] + self.history + [{"role": "user", "content": user_input}]
        try:
            res = client.chat.completions.create(
                model=MODEL_ID, 
                messages=messages, 
                temperature=0.8
            )
            reply = res.choices[0].message.content.strip()
            self.history.append({"role": "user", "content": user_input})
            self.history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            logging.error(f"Chat generation failed: {e}")
            return "Cognitive failure."
