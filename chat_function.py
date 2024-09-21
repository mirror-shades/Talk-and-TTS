from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.uix.progressbar import ProgressBar
from kivy.core.audio import SoundLoader
from kivy.uix.boxlayout import BoxLayout
import threading
import wave
import pyaudio
import time
import os
from pathlib import Path
from openai import OpenAI
from pydub import AudioSegment
from pydub.utils import make_chunks
from dotenv import load_dotenv

def chat_function(app):
    # Remove any existing widgets
    app.layout.clear_widgets()
    
    # Initialize variables
    app.recording = False
    app.processing = False
    app.responding = False
    app.frames = []
    app.chat_history = []
    app.prompt = ("You are a chatbot named Mimesis. You are an audio chatbot, the user will be speaking to you, "
                  "and your responses will be read aloud to the user. Try and come off personable rather than formal. Be very friendly. "
                  "Try and keep chats as conversational as possible. If a question is complicated ask the user to use "
                  "your (you being the Mimesis Chatbot) text chat feature. DO NOT USE "
                  "LISTS. DO NOT MAKE A NUMBERED LIST UNLESS SPECIFICALLY ASKED.")
    
    # Load API key
    load_dotenv()
    api_key = os.getenv('API_KEY')
    app.client = OpenAI(api_key=api_key)
    add_to_history(app, "system", app.prompt)
    
    # Create UI elements
    speak_button = Button(text='Press and Hold to Speak')
    back_button = Button(text='Back')
    status_label = Label(text='')
    progress_bar = ProgressBar(max=1000)
    
    # Layout
    layout = BoxLayout(orientation='vertical')
    layout.add_widget(speak_button)
    layout.add_widget(progress_bar)
    layout.add_widget(status_label)
    layout.add_widget(back_button)
    
    app.layout.add_widget(layout)
    
    # Bind functions
    speak_button.bind(on_touch_down=lambda instance, touch: on_press_speak_button(app, instance, touch))
    speak_button.bind(on_touch_up=lambda instance, touch: on_release_speak_button(app, instance, touch))
    back_button.bind(on_press=app.build_menu_function)
    
    # Start the update loop
    Clock.schedule_interval(lambda dt: update_ui(app, status_label, progress_bar), 0.1)

def on_press_speak_button(app, instance, touch):
    if instance.collide_point(*touch.pos):
        if not app.processing and not app.responding:
            app.recording = True
            threading.Thread(target=record_audio, args=(app,)).start()

def on_release_speak_button(app, instance, touch):
    if app.recording:
        app.recording = False
        if app.frames:
            app.processing = True
            threading.Thread(target=run_program, args=(app,)).start()

def record_audio(app):
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    CHUNK = 1024
    WAVE_OUTPUT_FILENAME = "inputAudio.wav"
    py_audio = pyaudio.PyAudio()
    stream = None
    try:
        stream = py_audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True,
                               frames_per_buffer=CHUNK)
        app.frames = []
        while app.recording:
            data = stream.read(CHUNK)
            app.frames.append(data)
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
        py_audio.terminate()
        # Save the recorded audio
        with wave.open(WAVE_OUTPUT_FILENAME, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(py_audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(app.frames))

def run_program(app):
    response_text = convert_audio_to_string(app)
    if response_text:
        process_output(app, response_text)
    app.processing = False

def convert_audio_to_string(app):
    WAVE_OUTPUT_FILENAME = "inputAudio.wav"
    try:
        with Path(WAVE_OUTPUT_FILENAME).open("rb") as audio_file:
            transcription = app.client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
        user_message = transcription.text
        add_to_history(app, "user", user_message)
        response = app.client.chat.completions.create(
            model="gpt-4o",
            messages=app.chat_history
        )
        response_text = response.choices[0].message.content
        if not response_text:
            raise ValueError("No response text generated")
        add_to_history(app, "assistant", response_text)
        return response_text
    except Exception as e:
        print(f"Error converting audio to string: {e}")
        return None

def process_output(app, response_text):
    app.responding = True
    try:
        speech_response = app.client.audio.speech.create(
            model="tts-1-hd", 
            voice="nova", 
            input=response_text
        )
        if not speech_response or not speech_response.content:
            raise ValueError("Failed to generate speech response")
        
        output_audio_path = Path("./outputAudio.mp3")

        with output_audio_path.open("wb") as out_file:
            out_file.write(speech_response.content)
        
        if output_audio_path.stat().st_size == 0:
            raise ValueError("Written audio file is empty")

        # Play the audio
        sound = SoundLoader.load(str(output_audio_path))
        if sound:
            sound.play()
            # Wait until playback is finished
            while sound.state == 'play':
                time.sleep(0.1)
    except Exception as e:
        print(f"Error processing output: {e}")
    finally:
        app.responding = False

def update_ui(app, status_label, progress_bar):
    if app.recording:
        status_label.text = "Recording..."
    elif app.processing:
        status_label.text = "Processing..."
    elif app.responding:
        status_label.text = "Responding..."
    else:
        status_label.text = ""
    # Update progress bar if needed
    # progress_bar.value = some_value

def add_to_history(app, role, content):
    app.chat_history.append({'role': role, 'content': content})