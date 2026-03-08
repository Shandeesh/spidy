import speech_recognition as sr
import pyttsx3
import sys

class SpidyVoice:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.engine = pyttsx3.init()
        # Set voice property to a clearer one if available
        voices = self.engine.getProperty('voices')
        if len(voices) > 1:
            self.engine.setProperty('voice', voices[1].id) # Usually female/clearer on Windows

    def speak(self, text):
        """Convert text to speech"""
        print(f"Spidy Says: {text}")
        self.engine.say(text)
        self.engine.runAndWait()

    def listen(self):
        """Capture microphone input and return text"""
        with sr.Microphone() as source:
            print("Listening...")
            self.recognizer.adjust_for_ambient_noise(source)
            try:
                audio = self.recognizer.listen(source, timeout=5)
                text = self.recognizer.recognize_google(audio)
                print(f"You said: {text}")
                return text
            except sr.WaitTimeoutError:
                print("Listening timed out.")
                return None
            except sr.UnknownValueError:
                print("Could not understand audio.")
                return None
            except sr.RequestError as e:
                print(f"Could not request results; {e}")
                return None

if __name__ == "__main__":
    import json
    bot_voice = SpidyVoice()
    
    if len(sys.argv) > 1 and sys.argv[1] == "speak":
        # python voice_handler.py speak "Hello World"
        try:
            bot_voice.speak(sys.argv[2])
            print(json.dumps({"status": "success", "action": "speak", "message": sys.argv[2]}))
        except Exception as e:
            print(json.dumps({"status": "error", "message": str(e)}))
    else:
        # Default test: Listen
        try:
            text = bot_voice.listen()
            result = {
                "status": "success" if text else "no_input",
                "transcribed_text": text if text else ""
            }
        except Exception as e:
            result = {
                "status": "error",
                "message": str(e)
            }
        print(json.dumps(result))
