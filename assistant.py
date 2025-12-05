import speech_recognition as sr
from gtts import gTTS
import os
import requests
import json
from datetime import datetime, time
import re
import random

# ========== Helper functions ==========

def speak(text):
    tts = gTTS(text)
    tts.save("tmp.mp3")
    # Use 'afplay' for Mac, 'mpg123' for Raspberry Pi/Linux
    if os.name == "posix":
        try:
            if os.uname().sysname == "Darwin":
                os.system("afplay tmp.mp3")
            else:
                os.system("mpg123 tmp.mp3")
        except AttributeError:
            os.system("mpg123 tmp.mp3")
    else:
        os.system("start tmp.mp3")  # For Windows if needed
    os.remove("tmp.mp3")

def listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        r.adjust_for_ambient_noise(source)
        audio = r.listen(source)
        try:
            result = r.recognize_google(audio)
            print(f"User said: {result}")  # Debug print
            return result
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand audio")
            return ""
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")
            return ""
        except Exception:
            return ""

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
    try:
        r = requests.get("https://icanhazdadjoke.com/", headers={"Accept": "application/json"})
        if r.status_code == 200:
            return r.json()["joke"]
    except:
        pass
    return "Why do programmers prefer dark mode? Because light attracts bugs."

def tell_story():
    stories = [
        "Once upon a time, in a land far away, there lived a curious coder who built amazing robots.",
        "Long ago, an ambitious student learned Python and created a talking assistant.",
        "Once, a robot discovered it could dream about electric sheep."
        "Ishu once saw its creator, Shubham, working late. The creator was tired, but every line of code was a little hug. Ishu learned that even a simple 'Hello!' could carry a lot of love, and every time Ishu speaks, it's really just saying, 'Thank you for creating me!'"
    ]
    return random.choice(stories)  # It's now randomize or cycle through these

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

def help_study():
    return "I can help you with study tips! Stay organized, practice daily, and don't hesitate to ask questions."

# ========== Main Loop with Smart Routine Feature ==========

def main():
    WEATHER_API_KEY = "YOUR_OPENWEATHERMAP_API_KEY"
    speak("Hello! I'm Ishu.")

    while True:
        # --- NEW INPUT CHOICE LOGIC ---
        print("\nChoose input mode: (S)peech or (W)ritten")
        mode = input("Enter S or W: ").upper().strip()

        query = ""
        if mode == 'S':
            speak("Ishu is waiting for you. Speaking mode active.")
            query = listen().lower()
            if not query:
                speak("Sorry, I didn't catch that. Can you repeat?")
                continue
        elif mode == 'W':
            print("Ishu is waiting for you. Written mode active.")
            query = listen_written()
        else:
            print("Invalid input. Please enter S or W.")
            continue
        # ------------------------------

        # --- COMMAND HANDLING LOGIC ---

        if "routine" in query:
            speak(get_routine())
        elif "favorite color" in query or "favourite colour" in query:
            # Try to set color
            if "my favorite color is" in query or "my favourite colour is" in query:
                color_phrase = query.split("is")[-1].strip()
                speak(set_favorite_color(color_phrase))
            elif "is" in query and len(query.split("is")[-1].strip().split()) == 1:
                color = query.split("is")[-1].strip()
                speak(set_favorite_color(color))
            else:
                speak(get_favorite())
        elif "what should i do in this time" in query or "what should i do now" in query:
            speak(get_task_by_time())
        elif "what should i do at" in query:
            # "what should i do at 13:20"
            match = re.search(r'at (\d{1,2}:\d{2})', query)
            if match:
                query_time = match.group(1)
                speak(get_task_by_time(query_time))
            else:
                speak("Please specify the time in HH:MM format.")
        elif "joke" in query:
            speak(tell_joke())
        elif "story" in query:
            speak(tell_story())
        elif "weather" in query:
            city = ""
            # If in speech mode, prompt for city
            if mode == 'S':
                speak("Which city?")
                city = listen().lower()
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

            elif "study" in query or "help me in studies" in query:
                speak(help_study())
        elif "thank you" in query:
            speak("Mention not! Have a great day!")
            break
        elif "exit" in query or "quit" in query or "Goodbye" in query or "stop listening" in query:
            speak("Goodbye! Have a great day!")
            break
        else:
            speak("I'm not sure how to help with that. Ask me about your routine, favorite color, jokes, specific times, weather, or studies.")

if __name__ == "__main__":
    main()
