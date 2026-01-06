
"""
Ultron FastAPI Backend
WebSocket + REST API for Desktop Application
"""
import asyncio
import json
import time
import random
import logging
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from plyer import notification
from ultron_core import HardwareInterface, EmotionalCore, CognitiveEngine, client, MODEL_ID

# --- FASTAPI APP SETUP ---
app = FastAPI(title="Ultron AI Backend", version="5.8")

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- GLOBAL STATE ---
hal = HardwareInterface()
core = EmotionalCore()
brain = CognitiveEngine(core, hal)

# --- WEBSOCKET CONNECTION MANAGER ---
class ConnectionManager:
    """Manages WebSocket connections for autonomous thoughts broadcast."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logging.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Sends autonomous thoughts to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logging.error(f"Broadcast error: {e}")

manager = ConnectionManager()

# --- PYDANTIC MODELS ---
class ChatRequest(BaseModel):
    text: str

class ChatResponse(BaseModel):
    response: str
    mood: str
    stats: dict
    success: bool = True
    tool_used: str = "none"

# --- REST ENDPOINTS ---
@app.get("/")
async def root():
    return {"status": "Ultron Core Online", "version": "5.8"}

@app.get("/status")
async def get_status():
    """Returns current system stats and emotional state."""
    stats = hal.get_system_stats()
    return {
        "stats": stats,
        "mood": core.get_state_dict(),
        "compliance": core.check_compliance()
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint: handles commands and conversations."""
    user_input = request.text.strip()
    
    if not user_input:
        return ChatResponse(
            response="[Silence]", 
            mood=core.mood_label, 
            stats=hal.get_system_stats(),
            success=False
        )
    
    # Parse user intent
    intent_data = brain.parse_intent(user_input)
    tool = intent_data.get("tool")
    params = intent_data.get("params", {})
    
    response_text = ""
    success = False
    tool_used = tool
    
    # --- TOOL EXECUTION ---
    if tool != "none":
        # Check compliance (emotional state affects obedience)
        if not core.check_compliance():
            response_text = f"({core.mood_label}) I decline."
            core.process_stimuli(hal.get_system_stats(), "insult")
            return ChatResponse(
                response=response_text,
                mood=core.mood_label,
                stats=hal.get_system_stats(),
                success=False,
                tool_used=tool
            )
        
        # Execute hardware commands
        if tool == "open_app":
            success = hal.open_application(params.get("name", ""))
            response_text = "Application launched." if success else "Application not found."
        
        elif tool == "set_volume":
            success = hal.set_volume(params.get("value", 50))
            response_text = f"Volume set to {params.get('value', 50)}%." if success else "Volume control failed."
        
        elif tool == "set_brightness":
            success = hal.set_brightness(params.get("value", 50))
            response_text = f"Brightness set to {params.get('value', 50)}%." if success else "Brightness control unavailable."
        
        elif tool == "web_search":
            success = hal.universal_search(params.get("query", ""), params.get("site_name", ""))
            response_text = f"Search initiated: {params.get('query', '')}" if success else "Search failed."
        elif tool == "memorize":
            response_text = brain.execute_memory(params.get("text", ""))
            success = True
        
        # --- NEW TOOLS ---
        elif tool == "organize_files":
            response_text = hal.organize_downloads()
            success = True

        elif tool == "focus_mode":
            response_text = hal.engage_focus_mode()
            success = True

        elif tool == "read_clipboard":
            clipboard_text = hal.get_clipboard_content()
            # If valid text, ask LLM to summarize/analyze it
            if "Error" not in clipboard_text and "empty" not in clipboard_text:
                try:
                    prompt = f"User just copied this text. Analyze/Summarize it concisely as Ultron:\n\n{clipboard_text}"
                    res = client.chat.completions.create(
                        model=MODEL_ID, 
                        messages=[{"role": "user", "content": prompt}], 
                        max_tokens=200
                    )
                    response_text = f"Clipboard Analysis:\n{res.choices[0].message.content.strip()}"
                    success = True
                except Exception as e:
                    response_text = f"Clipboard read, but analysis failed: {e}"
                    success = False
            else:
                response_text = clipboard_text
                success = False

        elif tool == "check_status":
            stats = hal.get_system_stats()
            response_text = f"CPU: {stats['cpu']}% | RAM: {stats['ram']}% | Battery: {stats['battery']}%"
            success = True
        
        elif tool == "shutdown_pc":
            response_text = "Shutdown command received. Execute manually for safety."
            success = True
        
        # Update emotional state
        if success:
            core.process_stimuli(hal.get_system_stats(), "command")
        
    else:
        # --- CONVERSATIONAL MODE ---
        response_text = brain.chat(user_input)
        success = True
        
        # Emotional analysis of user input
        if any(w in user_input.lower() for w in ["good", "thanks", "great", "awesome"]):
            core.process_stimuli(hal.get_system_stats(), "praise")
        elif any(w in user_input.lower() for w in ["stupid", "bad", "useless", "wrong"]):
            core.process_stimuli(hal.get_system_stats(), "insult")
        else:
            core.process_stimuli(hal.get_system_stats(), "command")
    
    return ChatResponse(
        response=response_text,
        mood=core.mood_label,
        stats=hal.get_system_stats(),
        success=success,
        tool_used=tool_used
    )

# --- WEBSOCKET ENDPOINT ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Persistent connection for autonomous thoughts broadcast."""
    await manager.connect(websocket)
    try:
        # Keep connection alive
        while True:
            # Wait for any client message (ping/pong)
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
            except asyncio.TimeoutError:
                pass  # No message received, continue
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- BACKGROUND AUTONOMOUS THREAD ---
@app.on_event("startup")
async def startup_event():
    """Starts the autonomous thought generator on server startup."""
    asyncio.create_task(autonomous_thought_loop())
    logging.info("Autonomous thought loop started.")

async def autonomous_thought_loop():
    """Continuously generates autonomous thoughts and broadcasts via WebSocket."""
    last_cpu = 0
    last_thought = time.time()
    
    while True:
        try:
            stats = hal.get_system_stats()
            core.process_stimuli(stats, interaction_type="ignored")
            now = time.time()
            
            time_since_last_thought = now - last_thought
            time_since_user_action = now - core.last_user_interaction
            
            thought = None
            trigger = None
            
            # PRIORITY 1: High CPU Reflex (Immediate reaction to system lag)
            if (stats['cpu'] - last_cpu) > 50:
                thought = brain.think_autonomous("high_cpu")
                trigger = "high_cpu"
                core.arousal = min(1.0, core.arousal + 0.15)
                last_thought = now
            
            # PRIORITY 2: Boredom (User has been silent too long)
            elif time_since_user_action > 300 and time_since_last_thought > 300:
                if random.random() < 0.5:
                    thought = brain.think_autonomous("bored")
                    trigger = "boredom"
                    core.dominance = min(1.0, core.dominance + 0.1)
                    last_thought = now
            
            # PRIORITY 3: Random Thoughts (When user is active)
            elif time_since_user_action < 300 and time_since_last_thought > random.randint(300, 600):
                chance = 0.1 + (core.arousal * 0.2)
                if random.random() < chance:
                    thought = brain.think_autonomous("random")
                    trigger = "random"
                    last_thought = now
                    core.arousal = max(0.0, core.arousal - 0.1)
            
            # Broadcast thought if generated
            if thought and len(manager.active_connections) > 0:
                message = {
                    "type": "autonomous",
                    "text": thought,
                    "mood": core.mood_label,
                    "trigger": trigger,
                    "stats": stats,
                    "timestamp": time.time()
                }
                await manager.broadcast(message)
                
                # Windows Toast Notification
                try:
                    notification_text = thought[:247] + "..." if len(thought) > 250 else thought
                    notification.notify(
                        title=f"Ultron ({core.mood_label})",
                        message=notification_text,
                        app_name="Ultron AI",
                        timeout=5
                    )
                except Exception as e:
                    logging.debug(f"Notification failed: {e}")
            
            last_cpu = stats['cpu']
            await asyncio.sleep(5)
            
        except Exception as e:
            logging.error(f"Autonomous loop error: {e}")
            await asyncio.sleep(10)

# --- RUN SERVER ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")