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

#  Added new state variables for robustness 🔥🔥🔥
SPEECH_RECOGNITION_AVAILABLE = False
PYJOKES_AVAILABLE = False
WHISPER_AVAILABLE = False
# ======================================================================

# 🔥🔥🔥 COMMIT 2 CHANGE: Global state for input mode 🔥🔥🔥
CURRENT_MODE = 'S' # Start in Speech mode by default
# ======================================================================

# --- Speech Recognition Component ---
try:
    import speech_recognition as sr
     #  Update state variable in try block 🔥🔥🔥
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    print("Warning: Failed to import SpeechRecognition. Legacy STT unavailable.")
    
# --- Pyjokes Component ---
try:
    import pyjokes
    #  Update state variable in try block 🔥🔥🔥
    PYJOKES_AVAILABLE = True
except ImportError:
    print("Warning: Failed to import pyjokes. Joke command unavailable.")

# --- Whisper and PyTorch Components ---
try:
    import torch
    import torchaudio
    import numpy
    import whisper 
    #  Update state variable in try block 🔥🔥🔥
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
OLLAMA_MODEL = "llama3" 
OLLAMA_SYSTEM_PROMPT = "You are Ishu, a helpful and friendly local AI assistant created by Shubham Jana. If a user's request matches one of your available tools, generate a JSON object to call the function. If not, answer the question directly. Always be concise and polite."
# ============================================

#  TEMPORARILY DISABLE TOOLS FOR STABILITY 🔥🔥🔥
TOOL_DEFINITIONS = []

# 🔥🔥🔥 END OLLAMA TOOL DEFINITIONS 🔥🔥🔥

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

    # 🔥🔥🔥  Use new state variables for check 🔥🔥🔥
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
            # 🔥🔥🔥  Added timeout and phrase_time_limit for robustness 🔥🔥🔥
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
    print(f"User said: {result}")
    return result

# +++ NEW FUNCTION: Handles initial mode selection +++
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
         #  Added indent=4 for readable JSON files 🔥🔥🔥
        with open(filename, "w") as f:
            json.dump(obj, f, indent=4)
    except Exception as e:
        print(f"Error saving JSON: {e}")

# +++ NEW FUNCTION: OLLAMA RESPONSE (MODIFIED FOR TOOL USE) +++
def ollama_response(prompt, tools=None, history=None):
    """
    Sends a prompt to the local Ollama LLM and returns the response. 
    Accepts conversation history for context.
    """
    print(f"Ollama thinking...")

    #  History handling logic 🔥🔥🔥
    if history and len(history) > 0:
        messages = history
    else:
        # Include system prompt and user message for the initial call
        messages = [
            {"role": "system", "content": OLLAMA_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]

    # Ensure the final message is the current user prompt if history was provided
    # THIS BLOCK NEEDS TO BE INDENTED CONSISTENTLY (e.g., 4 spaces)
    if history and messages[-1]['role'] != 'user':
        messages.append({"role": "user", "content": prompt})
            
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages, # Use messages instead of prompt
        "stream": False, # Get the full response in one go
        "tools": tools if tools else [] # Pass tools if provided
    }
   
    # ===================================================

    try:
        # 2. Send the request to the Ollama API
        response = requests.post(OLLAMA_API_URL, json=payload)
        
        # 3. Check for successful response
        if response.status_code == 200:
            data = response.json()

            return data.get("message", {"content":"Sorry, the LLM returned an empty response."})
        else:
            #  Added response text snippet for better error reporting 🔥🔥🔥
            return {"content": f"Ollama API Error (Code {response.status_code}). Check your model name ({OLLAMA_MODEL}). Response text: {response.text[:100]}..."}
    # ===========================================================================================

    except requests.exceptions.ConnectionError:
        # Handle the case where the Ollama server is not running
        return {"content": "I can't connect to the local LLM. Please make sure Ollama is running on http://localhost:11434 and the model ('llama3') is pulled."}
    except Exception as e:
        # Catch all other potential errors
        print(f"Unexpected Ollama error: {e}")
        return {"content": "An unexpected error occurred while processing the LLM request."}
# +++++++++++++++++++++++++++++++++++++

# ========== Routine Features with Robust Time Logic ==========

def parse_time(timestr):
    # Accept "05:30", "5:30", "07:31", etc.
    h, m = [int(part) for part in timestr.strip().split(":")]
    return time(hour=h, minute=m)

def get_routine():
    routine = load_json("routine.json", [])
    if not routine:
        return "You have not set your daily routine yet."
    lines = [f"{entry['start']} - {entry['end']}: {entry['activity']}" for entry in routine]
    return "Here's your detailed daily routine:\n" + "\n".join(lines)

def get_task_by_time(query_time=None):
    routine = load_json("routine.json", [])
    if not routine:
        return "You have not set your daily routine yet."
    # Use current system time if not specified
    if query_time is None:
        now = datetime.now()
        query_time = now.strftime('%H:%M')
    # Convert to datetime.time
    try:
        qt = parse_time(query_time)
    except Exception:
        return "Invalid time format. Please use HH:MM."
    for slot in routine:
        start = parse_time(slot['start'])
        end = parse_time(slot['end'])
        # If the slot wraps around midnight (e.g. 23:30–05:30)
        if start < end:
            in_range = start <= qt < end
        else:  # wraps over midnight
            in_range = qt >= start or qt < end
        if in_range:
            return f"At {query_time}, you should: {slot['activity']}."
    return "No scheduled activity for this time."

def add_routine_entry(start, end, activity):
    """Adds a new routine entry if start/end times are valid (HH:MM)."""
    routine = load_json("routine.json", [])
    try:
        # Validate time format using the existing parse_time helper
        parse_time(start)
        parse_time(end)
    except Exception:
        return "Error: Invalid time format. Please ensure 'start' and 'end' are in HH:MM format (e.g., 09:00)."
    
    # Check if a similar entry already exists (optional but good practice)
    for entry in routine:
        if entry['start'] == start and entry['end'] == end:
            return f"A routine entry already exists for {start} to {end}. Please try a different time slot."

    new_entry = {
        "start": start,
        "end": end,
        "activity": activity.strip()
    }
    routine.append(new_entry)
    # Sort the routine by start time before saving
    routine.sort(key=lambda x: parse_time(x['start']))
    save_json("routine.json", routine)
    
    return f"Success! I have added '{activity}' from {start} to {end} to your routine."

def remove_routine_entry(activity_keyword):
    """Removes a routine entry based on a partial match of the activity name."""
    routine = load_json("routine.json", [])
    initial_count = len(routine)
    
    # Filter out entries that contain the keyword (case-insensitive)
    new_routine = [
        entry for entry in routine 
        if activity_keyword.lower() not in entry['activity'].lower()
    ]
    
    if len(new_routine) < initial_count:
        removed_count = initial_count - len(new_routine)
        save_json("routine.json", new_routine)
        return f"Successfully removed {removed_count} routine entry/entries containing the keyword '{activity_keyword}'."
    else:
        return f"No routine entry found matching the keyword '{activity_keyword}'. Your routine is unchanged."


# ========== Other Assistant Features ==========

def get_favorite():
    favs = load_json("favorites.json", {})
    if "color" in favs:
        return f"Your favorite color is {favs['color']}."
    else:
        return "It's a tricky question, you don't have any favorite color."

def set_favorite_color(color):
    favs = load_json("favorites.json", {})
    favs["color"] = color
    save_json("favorites.json", favs)
    return f"Got it! I'll remember your favorite color is {color}."

def tell_joke():
    """
    Tells a joke using the local pyjokes library.
    """
    # CRITICAL CHECK: Ensure pyjokes was successfully imported
    if pyjokes is not None: 
        try:
            return pyjokes.get_joke()
        except Exception as e:
            print(f"Error fetching joke from pyjokes: {e}")
    
    # Fallback if pyjokes failed or was not imported
    return "Why do programmers prefer dark mode? Because light attracts bugs."

def tell_story(topic=""):
    """
    Generates a creative story using the Ollama LLM.
    """
    if topic:
        prompt = f"Tell me a short, imaginative story about {topic}. Make the story suitable for a student and end with a gentle lesson."
    else:
        prompt = "Tell me a short, imaginative story (about 100 words) focusing on the adventures of a young coder named Ishu. Make the story suitable for a student and end with a gentle lesson."
    
    # We call ollama_response without tools here, as we only need the content.
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

# ========== Main Loop with Smart Routine Feature ==========

def main():
    global CURRENT_MODE # Need to declare CURRENT_MODE as global to modify it.

    # NOTE: You must replace this with your actual OpenWeatherMap API key
    WEATHER_API_KEY = "YOUR_OPENWEATHERMAP_API_KEY"
    
    speak("Hello! I'm Ishu.")
    # 🔥🔥🔥 COMMIT 2 CHANGE: Initial mode selection and greeting 🔥🔥🔥
    select_initial_mode()
    speak(f"Starting in {'Speech' if CURRENT_MODE == 'S' else 'Written'} mode. Say or type 'change mode' to switch.", blocking=True)
    # ======================================================================

    #  Initialize chat history outside the loop 🔥🔥🔥
    chat_history = [
        {"role": "system", "content": OLLAMA_SYSTEM_PROMPT},
    ]

    
    while True:
        
        # 🔥🔥🔥 COMMIT 2 CHANGE: STATEFUL INPUT LOGIC 🔥🔥🔥
        query = ""
        if CURRENT_MODE == 'S':
            speak("Listening...", blocking=True)
            query = listen_whisper().lower()
            if not query:
                speak("Sorry, I didn't catch that. Can you repeat?", blocking=True)
                continue
        else: # CURRENT_MODE == 'W'
            query = listen_written()
        # ---------------------------------------------------

        # --- COMMAND HANDLING LOGIC ---
        
        # 🔥🔥🔥 COMMIT 2 CHANGE: New command to change mode 🔥🔥🔥
        if "change mode" in query:
            new_mode = 'W' if CURRENT_MODE == 'S' else 'S'
            CURRENT_MODE = new_mode
            speak(f"Mode switched to {'Speech' if CURRENT_MODE == 'S' else 'Written'}.", blocking=True)
            continue
       
        if "what should i do in this time" in query or "what should i do now" in query:
            # <<< COMMIT 1 CHANGE: speak() is now blocking for better UX.
            speak(get_task_by_time(), blocking=True)
        elif "what should i do at" in query:
            match = re.search(r'at (\d{1,2}:\d{2})', query)
            if match:
                query_time = match.group(1)
                speak(get_task_by_time(query_time), blocking=True)
            else:
                speak("Please specify the time in HH:MM format.", blocking=True)
       
        elif "weather" in query:
            city = ""
            # If in speech mode, prompt for city
            if CURRENT_MODE == 'S': # 🔥🔥🔥 COMMIT 2 CHANGE: Use global state
                speak("Which city?", blocking=True)
                city = listen_whisper().lower() 
            # If in written mode, try to extract city from the query
            elif CURRENT_MODE == 'W': # 🔥🔥🔥 COMMIT 2 CHANGE: Use global state
                # Simple extraction, e.g., "weather in london"
                parts = query.split('weather in')
                city = parts[1].strip() if len(parts) > 1 else 'unknown'
                if city == 'unknown':
                    print("Please specify the city.")
                    city = input("Which city?: ").lower()

            # Check if city was captured before calling the API    
            if city and city != 'unknown':   
                #<<< COMMIT 1 CHANGE: speak() is now blocking for better UX.
                speak(get_weather(city, WEATHER_API_KEY), blocking=True)
            elif city == 'unknown':
                #<<< COMMIT 1 CHANGE: speak() is now blocking for better UX.
                speak("I need a city name to check the weather.", blocking=True)
                
        elif "thank you" in query:
            #<<< COMMIT 1 CHANGE: speak() is now blocking for better UX.
            speak("Mention not! Have a great day!", blocking=True)
            break
        elif "exit" in query or "quit" in query or "Goodbye" in query or "stop listening" in query:
            #<<< COMMIT 1 CHANGE: speak() is now blocking for better UX.
            speak("Goodbye! Have a great day!", blocking=True)
            break

        
        # *** NEW: Default Command to Ollama LLM (with Tool Use) ***
        else:
            #  History handling in main loop 🔥🔥🔥
            # Create a copy of the history and add the current user message for the API call
            current_messages = chat_history + [{"role": "user", "content": query}]
            
            # Step 1: Send the query (and history) to the LLM with tools=None
            response_message = ollama_response(query, tools=None, history=current_messages)
            
            # --- History Update ---
            # 1. Add user message to history
            chat_history.append({"role": "user", "content": query})
            
            # 2. Check if the LLM provided a response
            if "content" in response_message and response_message["content"]:
                # 3. Add LLM's response to history
                chat_history.append(response_message)
                # <<< COMMIT 1 CHANGE: speak() is now blocking for better UX.
                speak(response_message["content"], blocking=True) 
            else:
                # <<< COMMIT 1 CHANGE: speak() is now blocking for better UX.
                speak("I received an empty response from the LLM. Please check your Ollama configuration or model.", blocking=True) 
            # ============================================================


if __name__ == "__main__":
    main()