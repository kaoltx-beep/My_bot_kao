import pyttsx3

engine = pyttsx3.init()

voices = engine.getProperty('voices')
engine.setProperty('voice', voices[0].id)  # บังคับ voice

engine.setProperty('rate', 170)

engine.say("test voice working")
engine.runAndWait()