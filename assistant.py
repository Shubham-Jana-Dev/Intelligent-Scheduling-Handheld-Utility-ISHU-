import subprocess 
import os
import requests
import json
from datetime import datetime, time
import re
import random
import time as time_lib 

# =========================================================
# 🐞🔫 CRITICAL FIX: Robust Safely Handled Imports
# =========================================================

# Initialize modules to None for safety
sr = None
pyjokes = None
torch = None
torchaudio = None
numpy = None
whisper = None

# 🔥🔥🔥 COMMIT 1 CHANGE: Added new state variables for robustness 🔥🔥🔥
SPEECH_RECOGNITION_AVAILABLE = False
PYJOKES_AVAILABLE = False
WHISPER_AVAILABLE = False
# ======================================================================

# 🔥🔥🔥 COMMIT 2 CHANGE: Global state for input mode 🔥🔥🔥
CURRENT_MODE = 'W' # Start in Written mode for ease of testing
# ======================================================================

# --- Speech Recognition Component ---
try:
    import speech_recognition as sr
     # 🔥🔥🔥 COMMIT 1 CHANGE: Update state variable in try block 🔥🔥🔥
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    print("Warning: Failed to import SpeechRecognition. Legacy STT unavailable.")
    
# --- Pyjokes Component ---
try:
    import pyjokes
    # 🔥🔥🔥 COMMIT 1 CHANGE: Update state variable in try block 🔥🔥🔥
    PYJOKES_AVAILABLE = True
except ImportError:
    print("Warning: Failed to import pyjokes. Joke command unavailable.")

# --- Whisper and PyTorch Components ---
try:
    import torch
    import torchaudio
    import numpy
    import whisper 
    # 🔥🔥🔥 COMMIT 1 CHANGE: Update state variable in try block 🔥🔥🔥
    WHISPER_AVAILABLE = True
except ImportError:
    print("Warning: Failed to import Whisper components. Voice command functionality may be limited.")

# ==============================
# 1. WHISPER CONFIGURATION
# ==============================
WHISPER_MODEL = None
# ============================================

# +++ 2. OLLAMA CONFIGURATION +++
# ============================================
OLLAMA_API_URL = "http://localhost:11434/api/chat"
# 🔥🔥🔥 COMMIT 4 FIX: Switching back to llama3 and manual tool calling 🔥🔥🔥
OLLAMA_MODEL = "llama3" 

# 🔥🔥🔥 COMMIT 4 FIX: New System Prompt for manual JSON output 🔥🔥🔥
OLLAMA_SYSTEM_PROMPT = """
You are Ishu, a helpful and friendly local AI assistant created by Shubham Jana.
Your primary function is to manage the user's daily schedule/routine.

When a user's request requires using a tool, you MUST respond ONLY with a JSON object 
in the following format: {"tool_call": {"name": "function_name", "arguments": {"arg1": "value", "arg2": "value"}}}.
Do NOT include any other text or markdown outside of the JSON block.

The available tools and their required arguments are:
- get_routine(): Retrieves the user's entire daily routine.
- get_task_by_time(query_time: str [optional]): Finds the activity at a specific time (HH:MM).
- add_routine_entry(start: str, end: str, activity: str): Adds a new entry.
- remove_routine_entry(activity_keyword: str): Removes an entry matching a keyword.

If the request is NOT a tool call (e.g., asking a general question, asking for a joke, or when provided with tool results), 
answer the question directly and concisely as Ishu.
"""
# ============================================

# --- File Paths (CRITICAL FIX: Use explicit relative path from the outer directory) ---
# Assuming you run the script from the parent directory: 
# /Users/shubhamjana/Desktop/Shubham-Jana-Dev-Intelligent-Scheduling-Handheld-Utility-ISHU-/
NESTED_DIR = "Intelligent-Scheduling-Handheld-Utility-ISHU-"
ROUTINE_FILE_PATH = os.path.join(NESTED_DIR, "routine.json")
FAVORITES_FILE_PATH = os.path.join(NESTED_DIR, "favorites.json")


# ========== Helper functions ==========

def speak(text, blocking=False):
    """
    Handles text-to-speech using the fast, local Mac 'say' command via subprocess.
    """
    print(f"Ishu says: {text}")
    
    # --- MAC/DARWIN TTS ---
    is_mac = os.name == "posix" and os.uname().sysname == "Darwin"

    if is_mac:
        try:
            command = ['say', text]
            if blocking:
                # Waits for the speech to finish (blocking)
                subprocess.run(command)
            else:
                # Starts the speech and moves on (non-blocking)
                subprocess.Popen(command) 
        except FileNotFoundError:
            print("Warning: Mac 'say' command not found. Speech failed.")
            print("TTS currently configured for macOS 'say' command. Speech unavailable.")

    # --- RASPBERRY PI/LINUX TTS Placeholder ---
    elif os.uname().sysname == "Linux" and ("arm" in os.uname().machine or "aarch64" in os.uname().machine):
        # NOTE: Placeholder for Pi-compatible TTS engine (e.g., Piper/PicoTTS)
        print("Pi/Linux environment detected. TTS engine (Piper/Pico) needs to be configured and uncommented.")
            
    # Placeholder/Error message for non-Mac/Pi environments
    else:
        print("TTS currently configured for macOS 'say' command. Speech unavailable.")


def listen_whisper():
    """Records audio and uses Whisper for high-accuracy transcription."""
    global WHISPER_MODEL 

    # 🔥🔥🔥 COMMIT 1 CHANGE: Use new state variables for check 🔥🔥🔥
    if not WHISPER_AVAILABLE or not SPEECH_RECOGNITION_AVAILABLE:
        return "Required speech modules (Whisper/SpeechRecognition) failed to load."

    if WHISPER_MODEL is None:
        try:
            print("Lazily loading Whisper model...")
            WHISPER_MODEL = whisper.load_model("base") 
        except Exception as e:
            print(f"Error loading Whisper model: {e}")
            WHISPER_MODEL = False # Mark as failed
            return "Whisper model failed to load during runtime."
    
    # Proceed with listening
    r = sr.Recognizer()
    temp_audio_file = "temp_audio.wav" 
    with sr.Microphone() as source:
        print("Whisper Listening...")
        r.adjust_for_ambient_noise(source)
        try:
            # 🔥🔥🔥 COMMIT 1 CHANGE: Added timeout and phrase_time_limit for robustness 🔥🔥🔥
            audio = r.listen(source, timeout=5, phrase_time_limit=15)
        except sr.WaitTimeoutError:
            print("No speech detected within the timeout period.")
            return ""
            
    try:
        # 1. Save the recorded audio to a temporary file
        with open(temp_audio_file, "wb") as f:
            f.write(audio.get_wav_data())

        # 2. Use Whisper to transcribe the file
        if WHISPER_MODEL:
            print("Transcribing with Whisper...")
            result = WHISPER_MODEL.transcribe(temp_audio_file, fp16=False) 
            text = result["text"].strip()
            print(f"User said: {text}")
            return text
        else:
            print("Whisper model not loaded.")
            return ""
            
    except Exception as e:
        print(f"Whisper/Audio error; {e}")
        return ""
    finally:
        if os.path.exists(temp_audio_file):
            os.remove(temp_audio_file)


def listen_written():
    """Captures input from the keyboard."""
    result = input("Write your command: ").lower()
    return result

# 🔥🔥🔥 COMMIT 2 CHANGE: Handles initial mode selection 🔥🔥🔥
def select_initial_mode():
    """Prompts user to select the initial input mode."""
    global CURRENT_MODE
    while True:
        print("\nChoose initial input mode: (S)peech or (W)ritten")
        mode = input("Enter S or W: ").upper().strip()
        if mode in ['S', 'W']:
            CURRENT_MODE = mode
            return mode
        else:
            print("Invalid input. Please enter S or W.")
# +++++++++++++++++++++++++++++++++++++

def load_json(filename, default):
    try:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return default

def save_json(filename, obj):
    try:
         
        # Ensure directory exists before saving
        os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
        with open(filename, "w") as f:
            json.dump(obj, f, indent=4)
    except Exception as e:
        print(f"Error saving JSON: {e}")

# +++ NEW FUNCTION: OLLAMA RESPONSE (MODIFIED FOR MANUAL TOOL USE) +++
def ollama_response(prompt, history=None):
    """
    Sends a prompt to the local Ollama LLM and returns the response. 
    """
    print(f"Ollama thinking...")

    # Set up messages for the API call
    if history and len(history) > 0:
        messages = history
    else:
        messages = [
            {"role": "system", "content": OLLAMA_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]

    # If the last message in history is not the user's current prompt, append it
    if not history or messages[-1].get('content') != prompt:
        messages.append({"role": "user", "content": prompt})
            
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages, 
        "stream": False, 
    }

    try:
        # 2. Send the request to the Ollama API
        response = requests.post(OLLAMA_API_URL, json=payload)
        
        # 3. Check for successful response
        if response.status_code == 200:
            data = response.json()
            return data.get("message", {"content":"Sorry, the LLM returned an empty response."})
        else:
            return {"content": f"Ollama API Error (Code {response.status_code}). Check your model name ({OLLAMA_MODEL}). Response text: {response.text[:100]}..."}

    except requests.exceptions.ConnectionError:
        return {"content": "I can't connect to the local LLM. Please make sure Ollama is running on http://localhost:11434 and the model ('llama3') is pulled."}
    except Exception as e:
        print(f"Unexpected Ollama error: {e}")
        return {"content": "An unexpected error occurred while processing the LLM request."}
# +++++++++++++++++++++++++++++++++++++

# ========== Routine Features with Robust Time Logic (TOOL FUNCTIONS) ==========

def parse_time(timestr):
    # Accept "05:30", "5:30", "07:31", etc.
    h, m = [int(part) for part in timestr.strip().split(":")]
    return time(hour=h, minute=m)

def get_routine():
    # 🔥🔥🔥 CRITICAL FIX: Use correct file path variable 🔥🔥🔥
    routine = load_json(ROUTINE_FILE_PATH, [])
    if not routine:
        # LLM needs a concise string response
        return "You have not set your daily routine yet."
    
    # Sort the routine by start time before returning
    routine.sort(key=lambda x: parse_time(x['start']))
    return json.dumps(routine)

def get_task_by_time(query_time=None):
    # 🔥🔥🔥 CRITICAL FIX: Use correct file path variable 🔥🔥🔥
    routine = load_json(ROUTINE_FILE_PATH, [])
    if not routine:
        return json.dumps({"status": "error", "message": "No daily routine is set."})
    
    # 1. Use current system time if not specified
    if query_time is None:
        now_dt = datetime.now()
        query_time = now_dt.strftime('%H:%M')
    else:
        # Validate time format
        try:
            datetime.strptime(query_time, '%H:%M')
            now_dt = datetime.combine(datetime.today().date(), parse_time(query_time))
        except ValueError:
            return json.dumps({"status": "error", "message": "Invalid time format. Please use HH:MM."})

    qt = now_dt.time()
    
    # 2. Check for task in progress (current task)
    for slot in routine:
        start = parse_time(slot['start'])
        end = parse_time(slot['end'])
        
        if start < end:
            in_range = start <= qt < end
        else:  # wraps over midnight
            in_range = qt >= start or qt < end
            
        if in_range:
            return json.dumps({"status": "found", "time": query_time, "start": slot['start'], "end": slot['end'], "activity": slot['activity']})
            
    # 3. Check for the next upcoming task
    # Sort routine by start time
    routine.sort(key=lambda x: parse_time(x['start']))
    
    next_task = None
    
    # Find the next task in the future (after the current time)
    for slot in routine:
        start_time = parse_time(slot['start'])
        # Check if the start time is later than the current time
        # NOTE: We use >= here so if query_time is 12:00, the 12:00 task is found
        if start_time >= qt: 
            next_task = slot
            break
    
    if next_task:
        return json.dumps({"status": "next_found", "time": query_time, "start": next_task['start'], "end": next_task['end'], "activity": next_task['activity']})
        
    # 🔥🔥🔥 CRITICAL FIX: Add wrap-around logic to find the next task (first task of the day) 🔥🔥🔥
    # If the loop finished and no task was found (because qt is past the last task)
    # the next task is the first task of the day.
    if routine:
        wrap_around_task = routine[0]
        return json.dumps({"status": "next_found", "time": query_time, "start": wrap_around_task['start'], "end": wrap_around_task['end'], "activity": wrap_around_task['activity']})
    
    return json.dumps({"status": "not_found", "time": query_time, "message": "No activity found for the current or upcoming time."})


def add_routine_entry(start, end, activity):
    """Adds a new routine entry if start/end times are valid (HH:MM)."""
    # 🔥🔥🔥 CRITICAL FIX: Use correct file path variable 🔥🔥🔥
    routine = load_json(ROUTINE_FILE_PATH, [])
    try:
        # Validate time format using the existing parse_time helper
        parse_time(start)
        parse_time(end)
    except Exception:
        return "ERROR: Invalid time format. Please ensure 'start' and 'end' are in HH:MM format (e.g., 09:00)."
    
    new_entry = {
        "start": start,
        "end": end,
        "activity": activity.strip()
    }
    routine.append(new_entry)
    # Sort the routine by start time before saving
    routine.sort(key=lambda x: parse_time(x['start']))
    # 🔥🔥🔥 CRITICAL FIX: Use correct file path variable 🔥🔥🔥
    save_json(ROUTINE_FILE_PATH, routine)
    
    return json.dumps({"status": "success", "message": f"Added {activity} from {start} to {end}."})

def remove_routine_entry(activity_keyword):
    """Removes a routine entry based on a partial match of the activity name."""
    # 🔥🔥🔥 CRITICAL FIX: Use correct file path variable 🔥🔥🔥
    routine = load_json(ROUTINE_FILE_PATH, [])
    initial_count = len(routine)
    
    # Filter out entries that contain the keyword (case-insensitive)
    new_routine = [
        entry for entry in routine 
        if activity_keyword.lower() not in entry['activity'].lower()
    ]
    
    if len(new_routine) < initial_count:
        removed_count = initial_count - len(new_routine)
        # 🔥🔥🔥 CRITICAL FIX: Use correct file path variable 🔥🔥🔥
        save_json(ROUTINE_FILE_PATH, new_routine)
        return json.dumps({"status": "success", "removed_count": removed_count, "keyword": activity_keyword})
    else:
        return json.dumps({"status": "not_found", "keyword": activity_keyword})


# ========== Other Assistant Features (Included for functionality) ==========

def get_favorite():
    # 🔥🔥🔥 CRITICAL FIX: Use correct file path variable 🔥🔥🔥
    favs = load_json(FAVORITES_FILE_PATH, {})
    if "color" in favs:
        return f"Your favorite color is {favs['color']}."
    else:
        return "It's a tricky question, you don't have any favorite color."

def set_favorite_color(color):
    # 🔥🔥🔥 CRITICAL FIX: Use correct file path variable 🔥🔥🔥
    favs = load_json(FAVORITES_FILE_PATH, {})
    favs["color"] = color
    # 🔥🔥🔥 CRITICAL FIX: Use correct file path variable 🔥🔥🔥
    save_json(FAVORITES_FILE_PATH, favs)
    return f"Got it! I'll remember your favorite color is {color}."

def tell_joke():
    """Tells a joke using the local pyjokes library."""
    if pyjokes is not None: 
        try:
            return pyjokes.get_joke()
        except Exception as e:
            print(f"Error fetching joke from pyjokes: {e}")
    return "Why do programmers prefer dark mode? Because light attracts bugs."

def tell_story(topic=""):
    """Generates a creative story using the Ollama LLM."""
    if topic:
        prompt = f"Tell me a short, imaginative story about {topic}. Make the story suitable for a student and end with a gentle lesson."
    else:
        prompt = "Tell me a short, imaginative story (about 100 words) focusing on the adventures of a young coder named Ishu. Make the story suitable for a student and end with a gentle lesson."
    
    response_message = ollama_response(prompt) 
    return response_message.get("content", "I'm having trouble thinking of a good story right now.")

def get_weather(city, api_key):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            temp = data["main"]["temp"]
            cond = data["weather"][0]["description"]
            return f"The weather in {city} is {cond} with a temperature of {temp}°C."
        else:
            return "Sorry, I couldn't get the weather. Is the city name correct?"
    except Exception:
        return "Sorry, there was an error fetching the weather."

# ========== End of Other Assistant Features ==========


# 🔥🔥🔥 COMMIT 3 CHANGE: MAPPER to link LLM function names to Python functions 🔥🔥🔥
TOOL_MAPPER = {
    "get_routine": get_routine,
    "get_task_by_time": get_task_by_time,
    "add_routine_entry": add_routine_entry,
    "remove_routine_entry": remove_routine_entry,
}
# ===================================================================================

# ========== Main Loop with Manual Tool Execution Logic (NOW/NEXT FIX APPLIED) ==========

def main():
    global CURRENT_MODE

    # NOTE: You must replace this with your actual OpenWeatherMap API key
    WEATHER_API_KEY = "YOUR_OPENWEATHERMAP_API_KEY"
    
    speak("Hello! I'm Ishu.")
    select_initial_mode()
    speak(f"Starting in {'Speech' if CURRENT_MODE == 'S' else 'Written'} mode. Say or type 'change mode' to switch.", blocking=True)

    chat_history = [
        {"role": "system", "content": OLLAMA_SYSTEM_PROMPT},
    ]

    
    while True:
        
        query = ""
        if CURRENT_MODE == 'S':
            speak("Listening...", blocking=True)
            query = listen_whisper().lower()
            if not query:
                speak("Sorry, I didn't catch that. Can you repeat?", blocking=True)
                continue
        else: # CURRENT_MODE == 'W'
            query = listen_written()
        
        print(f"User said: {query}")

        # --- COMMAND HANDLING LOGIC ---
        
        if "change mode" in query:
            new_mode = 'W' if CURRENT_MODE == 'S' else 'S'
            CURRENT_MODE = new_mode
            speak(f"Mode switched to {'Speech' if CURRENT_MODE == 'S' else 'Written'} mode.", blocking=True)
            continue
       
        elif "thank you" in query:
            speak("Mention not! Have a great day!", blocking=True)
            break
        elif "exit" in query or "quit" in query or "goodbye" in query or "stop listening" in query:
            speak("Goodbye! Have a great day!", blocking=True)
            break

        # --- CRITICAL FIX: Local Query Interception (NOW/NEXT Distinction) ---
        user_input_lower = query.lower()
        
        # Define phrases for NOW (simple current task)
        time_query_now = [
            "what should i do now", 
            "what is my current task"
        ]
        
        # Define phrases for NEXT (current task + next task)
        time_query_next = [
            "what should i do next",
            "what's my next task",
            "what is my next task"
        ]
        
        routine_query_phrases = ["what is my routine", "show my routine", "daily schedule"]
        
        is_local_tool_query = False
        tool_to_call = None
        is_next_task_query = False # NEW FLAG to distinguish NOW vs NEXT
        
        if any(phrase in user_input_lower for phrase in routine_query_phrases):
            is_local_tool_query = True
            tool_to_call = "get_routine"
        elif any(phrase in user_input_lower for phrase in time_query_next):
            is_local_tool_query = True
            tool_to_call = "get_task_by_time"
            is_next_task_query = True # This will trigger the dual-task response
        elif any(phrase in user_input_lower for phrase in time_query_now):
            is_local_tool_query = True
            tool_to_call = "get_task_by_time"

        if is_local_tool_query:
            # Execute the function locally and bypass Ollama.
            print(f"Executing Local Tool: {tool_to_call}()")
            
            # --- Local Output Handling ---
            try:
                output = ""
                
                # 1. Handle get_routine()
                if tool_to_call == "get_routine":
                    response_json_string = get_routine()
                    
                    if response_json_string.startswith('['):
                        task_list = json.loads(response_json_string)
                        # Format for clear console output
                        header = "| Start | End | Activity |\n|---|---|---|"
                        output_list = [f"| {t['start']} | {t['end']} | {t['activity']} |" for t in task_list]
                        output = f"## Your Full Daily Routine 🗓️\n{header}\n" + "\n".join(output_list)
                    else:
                        output = response_json_string 
                
                # 2. Handle get_task_by_time()
                elif tool_to_call == "get_task_by_time":
                    
                    # First call to find the current/next task based on current time
                    response_json_string = get_task_by_time() 
                    task_data = json.loads(response_json_string)
                    output = ""
                    
                    if task_data.get("status") == "found":
                        current_activity = task_data.get('activity')
                        current_end_time = task_data.get('end')
                        
                        # --- LOGIC FOR "WHAT SHOULD I DO NEXT" ---
                        if is_next_task_query:
                            # Search for the next one using the current task's end time
                            next_task_json_string = get_task_by_time(query_time=current_end_time) 
                            next_task_data = json.loads(next_task_json_string)
                            
                            if next_task_data.get("status") == "next_found":
                                next_activity = next_task_data.get('activity')
                                next_start_time = next_task_data.get('start')
                                
                                output = (
                                    f"Your current task is **{current_activity}** (Ends at {current_end_time}). "
                                    f"Your *next* scheduled task is **{next_activity}** starting at {next_start_time}."
                                )
                            else:
                                output = f"You are currently doing **{current_activity}** (Ends at {current_end_time}). There is no further scheduled task after this."
                        
                        # LOGIC for "WHAT SHOULD I DO NOW"
                        else: 
                            output = f"Right now, you should be doing: **{current_activity}** (Ends at {current_end_time})."
                        
                    elif task_data.get("status") == "next_found":
                        # If no task is found, but the next one is found (user is free)
                        output = f"You are currently free! Your next scheduled activity is **{task_data.get('activity')}** starting at {task_data.get('start')}."
                    
                    else:
                        output = "No scheduled activity found for the current or upcoming time. Enjoy the free time!"
                
                speak(output, blocking=False)
                # Ensure the full, formatted output is printed to the console
                print(f"Ishu says: {output}")
                
                continue # Skip the Ollama process entirely
                
            except json.JSONDecodeError:
                print(f"Error processing local tool output for {tool_to_call}. Falling through to Ollama.")
                pass 
            # --- End of Local Output Handling ---
            
        # --- End of Local Query Interception ---
        
        # *** NEW: Default Command to Ollama LLM (Manual Tool Execution) ***
        else:
            # 1. Start the conversation with the user's query
            current_messages = chat_history + [{"role": "user", "content": query}]
            response_message = ollama_response(query, history=current_messages)
            
            response_content = response_message.get("content", "")
            
            tool_call = None
            tool_output = None

            # 🔥🔥🔥 COMMIT 4: Manual JSON Parsing for Tool Call 🔥🔥🔥
            try:
                if response_content.strip().startswith('{') and response_content.strip().endswith('}'):
                    # Use a simpler check for tool_call as regex is unreliable with nested JSON
                    parsed_json = json.loads(response_content)
                    if "tool_call" in parsed_json:
                        tool_call = parsed_json["tool_call"]
            except json.JSONDecodeError:
                pass
            # -------------------------------------------------------------
            
            if tool_call:
                # Tool call detected
                func_name = tool_call.get("name")
                func_args = tool_call.get("arguments", {})
                
                # 2. Add the LLM's tool call request to history (formatted for clarity)
                chat_history.append({"role": "assistant", "content": response_content})
                
                if func_name in TOOL_MAPPER:
                    print(f"Executing Tool: {func_name} with args: {func_args}")
                    
                    try:
                        # Ensure we handle the case where the tool takes no arguments (e.g., get_routine)
                        if func_args is None:
                            func_args = {}
                            
                        tool_output = TOOL_MAPPER[func_name](**func_args)
                    except Exception as e:
                        tool_output = f"ERROR executing {func_name}: {e}"
                    
                    # 3. Add the Tool's output (as a function result) to history
                    chat_history.append({
                        "role": "tool",
                        "content": tool_output,
                    })
                    
                    # 4. Re-call the LLM with the tool output (RAG/Function Calling pattern)
                    # NOTE: The query is the user's *original* query
                    final_response_message = ollama_response(query, history=chat_history)
                    
                    # 5. Add final LLM response to history and speak
                    chat_history.append(final_response_message)
                    speak(final_response_message["content"], blocking=True)
                else:
                    speak(f"Error: Tool '{func_name}' requested by LLM is not implemented.", blocking=True)

            # 5. Handle standard LLM conversation (No tool call returned)
            elif response_content:
                # Ensure user query is recorded if it wasn't a tool call path
                if not chat_history or chat_history[-1]['role'] != 'user': 
                    chat_history.append({"role": "user", "content": query})

                chat_history.append(response_message)
                speak(response_message["content"], blocking=True) 
            else:
                speak("I received an empty response from the LLM. Please check your Ollama configuration or model.", blocking=True) 


if __name__ == "__main__":
    main()