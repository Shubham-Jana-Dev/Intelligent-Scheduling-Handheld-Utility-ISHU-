import speech_recognition as sr
import os
import requests
import json
from datetime import datetime, time
import re
import random
import subprocess 
import pyjokes
import whisper 
import time as time_lib 

# ==============================
# 1. WHISPER CONFIGURATION
# ==============================

# Ensure the whisper model is loaded once at the start
# NOTE: The 'base' model offers a good balance of accuracy and speed.
try:
    WHISPER_MODEL = whisper.load_model("base") 
except Exception as e:
    print(f"Error loading Whisper model: {e}")
    WHISPER_MODEL = None

# +++ 2. OLLAMA CONFIGURATION (NEW SECTION) +++
# ============================================
OLLAMA_API_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "phi3" # <<< Recommend using a fast, small model like 'llama3' or 'phi3'
OLLAMA_SYSTEM_PROMPT = "You are Ishu, a helpful and friendly local AI assistant created by Shubham Jana. If a user's request matches one of your available tools, generate a JSON object to call the function. If not, answer the question directly. Always be concise and polite."
# ============================================

# 🔥🔥🔥 NEW SECTION: OLLAMA TOOL DEFINITIONS 🔥🔥🔥
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "tell_joke",
            "description": "Tells a random programming or general joke.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_favorite_color",
            "description": "Sets the user's favorite color in the settings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "color": {
                        "type": "string",
                        "description": "The name of the color to be set as the user's favorite.",
                    }
                },
                "required": ["color"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_favorite",
            "description": "Recalls the user's favorite color from the settings.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_routine_entry",
            "description": "Adds a new activity entry to the user's daily routine schedule. Requires start time (HH:MM), end time (HH:MM), and the activity description.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start": {
                        "type": "string",
                        "description": "The starting time of the activity in HH:MM format (e.g., 08:30)."
                    },
                    "end": {
                        "type": "string",
                        "description": "The ending time of the activity in HH:MM format (e.g., 10:00)."
                    },
                    "activity": {
                        "type": "string",
                        "description": "A description of the activity to be scheduled."
                    }
                },
                "required": ["start", "end", "activity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_routine_entry",
            "description": "Removes one or more routine entries based on a keyword match in the activity description.",
            "parameters": {
                "type": "object",
                "properties": {
                    "activity_keyword": {
                        "type": "string",
                        "description": "A keyword or phrase found in the activity to be removed."
                    }
                },
                "required": ["activity_keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_routine",
            "description": "Retrieves the full list of scheduled activities for the user's daily routine.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    # 🔥🔥🔥 NEW TOOL: tell_story (COMMIT 7) 🔥🔥🔥
    {
        "type": "function",
        "function": {
            "name": "tell_story",
            "description": "Generates a creative and imaginative story for the user. Provide the topic or subject for the story. The topic argument is optional.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The specific subject or topic the story should be about (e.g., 'a robot who loves to paint'). This is optional."
                    }
                },
            },
        },
    },
]

# 🔥🔥🔥 END NEW SECTION 🔥🔥🔥

# ========== Helper functions ==========

# --- RASPBERRY PI NOTE START ---
# NOTE for Raspberry Pi TTS:
# The Mac 'say' command is fast and local, but won't work on Pi.
# For Pi, consider using PicoTTS or Piper TTS (high quality, local).
# Example Piper command: os.system(f"echo '{text}' | piper --model [path/to/model] | aplay")
# --- RASPBERRY PI NOTE END ---

def speak(text, blocking=False):
    """
    Handles text-to-speech using the fast, local Mac 'say' command via subprocess.
    This function has been streamlined for macOS development.
    """
    print(f"Ishu says: {text}")
    
    # --- MAC/DARWIN TTS (Current Working Environment) ---
    if os.name == "posix" and os.uname().sysname == "Darwin":
        try:
            # Added shell=True for simple execution in some environments
            command = ['say', text]
            if blocking:
                # Waits for the speech to finish (blocking)
                subprocess.run(command)
            else:
                # Starts the speech and moves on (non-blocking)
                subprocess.Popen(command) 
        except FileNotFoundError:
            print("Warning: Mac 'say' command not found. Speech failed.")

    # --- RASPBERRY PI/LINUX TTS Placeholder ---
    elif os.uname().sysname == "Linux" and ("arm" in os.uname().machine or "aarch64" in os.uname().machine):
        # NOTE for Raspberry Pi TTS (PicoTTS/Piper):
        # The Mac 'say' command will not work on the Pi.
        # You need to replace this section with a Pi-compatible TTS engine.

        # --- OPTION 1: Using PicoTTS (Simple, lower quality, often pre-installed) ---
        # NOTE: PicoTTS command setup is often complex, requiring piping.
        # Example: command = f"pico2wave -w /tmp/tts.wav '{text}' && aplay /tmp/tts.wav"
        
        # --- OPTION 2: Using Piper TTS (Recommended: High quality, local) ---
        # NOTE: You must install Piper and download a model first.
        # EXAMPLE CODE TO USE LATER (uncomment when configured on Pi):
        # try:
        #     PIPER_MODEL_PATH = "/path/to/your/piper/model.onnx" # <<< REPLACE THIS PATH
        #     # The command uses 'echo', pipes text to 'piper', and then uses 'aplay' 
        #     # to play the audio file generated by piper.
        #     command = f"echo '{text}' | piper --model {PIPER_MODEL_PATH} --output_file /tmp/tts_pi.wav && aplay /tmp/tts_pi.wav"
        #     if blocking:
        #         subprocess.run(command, shell=True)
        #     else:
        #         subprocess.Popen(command, shell=True)
        # except Exception as e:
        #     print(f"Pi TTS (Piper/Pico) failed. Check installation: {e}")
        
        # Current behavior on Pi is just a print statement until code is uncommented:
        print("Pi/Linux environment detected. TTS engine (Piper/Pico) needs to be configured and uncommented.")
            
    # Placeholder/Error message for non-Mac/Pi environments
    else:
        print("TTS currently configured for macOS 'say' command. Speech unavailable.")


def listen_whisper():
    """Records audio and uses Whisper for high-accuracy transcription."""
    r = sr.Recognizer()
    # Use a temporary file name
    temp_audio_file = "temp_audio.wav" 
    with sr.Microphone() as source:
        print("Whisper Listening...") # Updated message
        r.adjust_for_ambient_noise(source)
        try:
            audio = r.listen(source)
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
            # Use 'fp16=False' for better compatibility on Mac CPUs/older GPUs
            result = WHISPER_MODEL.transcribe(temp_audio_file, fp16=False) 
            text = result["text"].strip()
            print(f"User said: {result}")  # Debug print
            return text
        else:
            print("Whisper model not loaded.")
            return ""
            
    except Exception as e:
        print(f"Whisper/Audio error; {e}")
        return ""
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_audio_file):
            os.remove(temp_audio_file)


def listen_written():
    """Captures input from the keyboard."""
    result = input("Write your command: ").lower()
    print(f"User said: {result}")
    return result

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
        with open(filename, "w") as f:
            json.dump(obj, f)
    except Exception as e:
        print(f"Error saving JSON: {e}")

# +++ NEW FUNCTION: OLLAMA RESPONSE (MODIFIED FOR TOOL USE) +++
def ollama_response(prompt, tools=None, history=None):
    """Sends a prompt to the local Ollama LLM and returns the response."""
    print(f"Ollama thinking...")

    if history:
        messages = history
    else:
        # Include system prompt and user message for the initial call
        messages = [
            {"role": "system", "content": OLLAMA_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages, # Use messages instead of prompt
        "stream": False, # Get the full response in one go
        "tools": tools if tools else [] # Pass tools if provided
    }
    
    try:
        # 2. Send the request to the Ollama API
        response = requests.post(OLLAMA_API_URL, json=payload)
        
        # 3. Check for successful response
        if response.status_code == 200:
            data = response.json()
        �
            return data.get("message", {"content":"Sorry, the LLM returned an empty response."})
        else:
            # Handle non-200 status codes (e.g., model not found)
            return {"content": f"Ollama API Error (Code {response.status_code}). Check your model name ({OLLAMA_MODEL})."}

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
    Removes the dependency on the external 'icanhazdadjoke' API.
    """
    try:
        # Get a random joke from pyjokes
        return pyjokes.get_joke()
    except Exception as e:
        print(f"Error fetching joke from pyjokes: {e}")
        # Fallback to the original hardcoded joke
    return "Why do programmers prefer dark mode? Because light attracts bugs."

def tell_story(topic=""):
    """
    Generates a creative story using the Ollama LLM.
    If a topic is provided, the story will be based on that topic.
    """
    if topic:
        prompt = f"Tell me a short, imaginative story about {topic}. Make the story suitable for a student and end with a gentle lesson."
    else:
        prompt = "Tell me a short, imaginative story (about 100 words) focusing on the adventures of a young coder named Ishu. Make the story suitable for a student and end with a gentle lesson."
    
    # We call ollama_response without tools here, as we only need the content.
    response_message = ollama_response(prompt)

    return response_message.get("content", "I'm having trouble thinking of a good story right now.")
# 🔥🔥🔥 NOTE: The old hardcoded stories list and function are now fully replaced. 🔥🔥🔥

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

# 🔥🔥🔥 NOTE: The old 'help_study' function is now removed, as the LLM handles this directly. 🔥🔥🔥

# ========== Main Loop with Smart Routine Feature ==========

def main():
    # NOTE: You must replace this with your actual OpenWeatherMap API key
    WEATHER_API_KEY = "YOUR_OPENWEATHERMAP_API_KEY"
    speak("Hello! I'm Ishu.")

     # 🔥🔥🔥 ADD TOOL MAPPER FOR EXECUTION 🔥🔥🔥
    # Dictionary mapping tool names (as defined in TOOL_DEFINITIONS) to their Python function calls
    available_functions = {
        "tell_joke": tell_joke,
        "set_favorite_color": set_favorite_color,
        "get_favorite": get_favorite,
        "add_routine_entry": add_routine_entry, 
        "remove_routine_entry": remove_routine_entry, 
        "get_routine": get_routine, 
        "tell_story": tell_story, # <<< NEW
    }

    
    while True:
        # --- NEW INPUT CHOICE LOGIC ---
        print("\nChoose input mode: (S)peech or (W)ritten")
        mode = input("Enter S or W: ").upper().strip()

        query = ""
        if mode == 'S':
            # <<< FIX: speak() is now blocking so the microphone isn't drowned out.
            speak("Ishu is waiting for you. Speaking mode active.", blocking=True)
            # *** CALLING NEW WHISPER FUNCTION ***
            query = listen_whisper().lower()
            
            if not query:
                speak("Sorry, I didn't catch that. Can you repeat?", blocking=True)
                continue
        elif mode == 'W':
            print("Ishu is waiting for you. Written mode active.")
            query = listen_written()
        else:
            print("Invalid input. Please enter S or W.")
            continue
        # ------------------------------

        # --- COMMAND HANDLING LOGIC ---
       
        if "what should i do in this time" in query or "what should i do now" in query:
            speak(get_task_by_time())
        elif "what should i do at" in query:
            # "what should i do at 13:20"
            match = re.search(r'at (\d{1,2}:\d{2})', query)
            if match:
                query_time = match.group(1)
                speak(get_task_by_time(query_time))
            else:
                speak("Please specify the time in HH:MM format.")
       
        # 🔥🔥🔥 NOTE: Old 'elif "story" in query' is removed here. 🔥🔥🔥
        
        elif "weather" in query:
            city = ""
            # If in speech mode, prompt for city
            if mode == 'S':
                speak("Which city?")
                city = listen_whisper().lower() 
            # If in written mode, try to extract city from the query
            elif mode == 'W':
                # Simple extraction, e.g., "weather in london"
                parts = query.split('weather in')
                city = parts[1].strip() if len(parts) > 1 else 'unknown'
                if city == 'unknown':
                    print("Please specify the city.")
                    city = input("Which city?: ").lower()

            # Check if city was captured before calling the API    
            if city and city != 'unknown':   
                speak(get_weather(city, WEATHER_API_KEY))
            elif city == 'unknown':
                speak("I need a city name to check the weather.")
                
# 🔥🔥🔥 NOTE: Old 'elif "study" in query' is removed here. 🔥🔥🔥

        elif "thank you" in query:
            speak("Mention not! Have a great day!")
            break
        elif "exit" in query or "quit" in query or "Goodbye" in query or "stop listening" in query:
            speak("Goodbye! Have a great day!")
            break

        
        # *** NEW: Default Command to Ollama LLM (with Tool Use) ***
        else:
            history = []
            # Step 1: Send the query and the tool definitions to the LLM
            response_message = ollama_response(query, tools=TOOL_DEFINITIONS)

            # Record the user message and LLM's first response for the next turn
            history.append({"role": "user", "content": query})
            history.append(response_message)
            
            # 1. Check if the LLM requested a function call
            if "tool_calls" in response_message:
                
                function_calls = response_message["tool_calls"]
                
                # Iterate through all requested function calls
                for call in function_calls:
                    function_name = call["function"]["name"]
                    function_args = call["function"]["arguments"]
                    
                    if function_name in available_functions:
                        function_to_call = available_functions[function_name]
                        
                        try:
                            # 2. Execute the function with arguments
                            function_response = function_to_call(**function_args)
                            
                            # 3. Send the function result back to the LLM
                            history.append({
                                "role": "tool",
                                "content": function_response
                            })
                            
                            # Get the final answer from the LLM based on the tool result
                            final_response = ollama_response(query, tools=TOOL_DEFINITIONS, history=history)
                            
                            # Speak the final, informed response
                            speak(final_response.get("content", "I processed your request but the LLM did not provide a final answer."))
                            break # Exit the loop after getting the final response

                        except TypeError as e:
                            # Handle missing or incorrect arguments
                            speak(f"Error executing tool '{function_name}'. Missing arguments? {e}")
                        except Exception as e:
                            speak(f"An error occurred during tool execution: {e}")
                            
            # 4. If no function was called, or if the initial LLM response had content (general answer)
            elif "content" in response_message and response_message["content"]:
                speak(response_message["content"])
            else:
                speak("I received an empty response from the LLM. Please check your Ollama configuration or model.")


if __name__ == "__main__":
    # NOTE for Pi: Before running on a Raspberry Pi, ensure you have
    # installed pyjokes, speech_recognition dependencies, and configured 
    # a local TTS engine (like Piper/PicoTTS) in the speak() function.
    main()
