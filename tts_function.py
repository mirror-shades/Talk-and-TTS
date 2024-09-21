from kivy.app import App
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.core.audio import SoundLoader
from kivy.clock import Clock

from pydub import AudioSegment
from pydub.effects import speedup
from pydub.playback import play
import io

import re
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables and initialize OpenAI client
load_dotenv()
api_key = os.getenv('API_KEY')
client = OpenAI(api_key=api_key)

# Constants
INPUT_FILENAME = 'input.txt'
OUTPUT_DIR = Path('./output')
MAX_SECTION_LENGTH = 4000
TTS_MODEL = "tts-1-hd"
TTS_VOICE = "onyx"
AUDIO_EXT = ".mp3"

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def tts_function(app):
    """Build the Kivy UI for TTS function."""
    app.title = "Text-to-Speech App"

    # Main layout
    main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

    # Back button to return to main menu
    back_button = Button(
        text='Back to Main Menu',
        size_hint=(1, 0.1),
        background_color=(0.8, 0.2, 0.2, 1)
    )
    back_button.bind(on_press=app.build_menu_function)
    main_layout.add_widget(back_button)

    # TextInput for displaying text content
    app.text_input = TextInput(
        text='',
        size_hint=(1, 0.5),
        multiline=True,
        hint_text='Enter text here or leave empty to read from input.txt'
    )
    main_layout.add_widget(app.text_input)

    # Button to start TTS processing
    process_button = Button(
        text='Process Text',
        size_hint=(1, 0.1),
        background_color=(0.2, 0.6, 0.8, 1)
    )
    process_button.bind(on_press=lambda instance: process_text(app, instance))
    main_layout.add_widget(process_button)

    # Control layout for playback controls
    control_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.15), spacing=10)

    # Rewind button
    app.rewind_button = Button(
        text='<<',
        size_hint=(0.15, 1),
        disabled=True
    )
    app.rewind_button.bind(on_press=lambda instance: rewind_audio(app))
    control_layout.add_widget(app.rewind_button)

    # Play/Pause button
    app.play_button = Button(
        text='Play',
        size_hint=(0.2, 1),
        background_color=(0.6, 0.8, 0.2, 1),
        disabled=True
    )
    app.play_button.bind(on_press=lambda instance: play_pause_audio(app))
    control_layout.add_widget(app.play_button)

    # Fast-forward button
    app.fastforward_button = Button(
        text='>>',
        size_hint=(0.15, 1),
        disabled=True
    )
    app.fastforward_button.bind(on_press=lambda instance: fastforward_audio(app))
    control_layout.add_widget(app.fastforward_button)

    # Playback speed dropdown menu
    speed_options = [str(1+(i / 10)) for i in range(5, -1, -1)]
    app.speed_dropdown = Spinner(
        text='1.0',  # Default value
        values=speed_options,
        size_hint=(0.5, 1)
    )
    control_layout.add_widget(app.speed_dropdown)

    main_layout.add_widget(control_layout)

    app.layout.add_widget(main_layout)

def process_text(app, instance):
    """Process the text input and generate audio files."""
    # Disable play controls while processing
    disable_play_controls(app)

    text_content = app.text_input.text.strip()
    if not text_content:
        text_content = process_input(INPUT_FILENAME)
        app.text_input.text = text_content

    split_text_array = split_text(text_content)
    app.audio_file_paths = generate_audio_files(client, split_text_array)
    if app.audio_file_paths:
        print("Audio files generated successfully.")
        # Enable play controls after processing
        enable_play_controls(app)
    else:
        print("Failed to generate audio files.")

def disable_play_controls(app):
    app.play_button.disabled = True
    app.rewind_button.disabled = True
    app.fastforward_button.disabled = True

def enable_play_controls(app):
    app.play_button.disabled = False
    app.rewind_button.disabled = False
    app.fastforward_button.disabled = False


def change_audio_speed(sound, speed=1.0):
    """Change the playback speed of the sound without changing pitch."""
    if speed == 1.0:  # No change needed
        return sound
    
    # Ensure speed is within a reasonable range
    speed = max(1, min(speed, 1.5))
    
    # Use speedup function to change speed while preserving pitch
    changed = speedup(sound, playback_speed=speed, chunk_size=150, crossfade=25)
    return changed

def play_pause_audio(app):
    """Toggle play and pause for audio playback."""
    if hasattr(app, 'is_playing') and app.is_playing:
        if hasattr(app, 'playback_thread') and app.playback_thread.is_alive():
            app.is_playing = False
            app.play_button.text = 'Play'
    else:
        if hasattr(app, 'audio_file_paths') and app.audio_file_paths:
            app.is_playing = True
            app.play_button.text = 'Pause'
            if not hasattr(app, 'current_audio_index'):
                app.current_audio_index = 0
            play_current_audio(app)
        else:
            print("No audio files to play. Please process the text first.")


def play_current_audio(app):
    """Play the current audio file."""
    if app.current_audio_index < len(app.audio_file_paths):
        audio_path = app.audio_file_paths[app.current_audio_index]
        speed = float(app.speed_dropdown.text)

        try:
            # Load the audio file
            sound = AudioSegment.from_file(str(audio_path), format="mp3")
            
            # Adjust speed
            adjusted_sound = change_audio_speed(sound, speed)

            # Use a separate thread to play audio to prevent blocking UI
            import threading

            def playback():
                print(f"Playing {audio_path.name} at {speed}x speed")
                # Convert the AudioSegment to a file-like object
                buffer = io.BytesIO()
                adjusted_sound.export(buffer, format="mp3")
                buffer.seek(0)
                
                # Play the audio
                play(AudioSegment.from_file(buffer, format="mp3"))

                # After playback, move to the next audio
                if app.is_playing:
                    app.current_audio_index += 1
                    if app.current_audio_index < len(app.audio_file_paths):
                        Clock.schedule_once(lambda dt: play_current_audio(app), 0)
                    else:
                        print("Finished playing all audio files.")
                        app.is_playing = False
                        app.play_button.text = 'Play'

            app.playback_thread = threading.Thread(target=playback)
            app.playback_thread.start()

        except Exception as e:
            print(f"Error playing audio: {e}")
            app.current_audio_index += 1
            play_current_audio(app)

    else:
        print("Finished playing all audio files.")
        app.is_playing = False
        app.play_button.text = 'Play'


def rewind_audio(app):
    """Rewind audio by going back one track."""
    if hasattr(app, 'current_audio_index') and app.current_audio_index > 0:
        app.current_audio_index -= 1
        if app.is_playing and hasattr(app, 'playback_thread'):
            app.is_playing = False
            app.playback_thread.join()
            app.is_playing = True
            play_current_audio(app)
    else:
        print("No previous track to rewind to.")

def fastforward_audio(app):
    """Fast-forward audio by skipping to next track."""
    if hasattr(app, 'current_audio_index') and app.current_audio_index < len(app.audio_file_paths) - 1:
        app.current_audio_index += 1
        if app.is_playing and hasattr(app, 'playback_thread'):
            app.is_playing = False
            app.playback_thread.join()
            app.is_playing = True
            play_current_audio(app)
    else:
        print("No more tracks to fast-forward to.")

def process_input(file_path):
    """Read and return content of the given text file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin-1') as file:
            return file.read()

def split_text(text):
    """Split the input text into smaller sections."""
    sentences = re.split(r'(\. )', text)  # Split on '. ' but keep the delimiter
    sections, current_section = [], ''

    for i in range(0, len(sentences), 2):
        sentence = sentences[i]
        if i + 1 < len(sentences):  # Append the delimiter back to the sentence
            sentence += sentences[i + 1]

        if len(current_section) + len(sentence) > MAX_SECTION_LENGTH:
            sections.append(current_section.strip())
            current_section = sentence
        else:
            current_section += sentence

    if current_section:
        sections.append(current_section.strip())

    return sections

def generate_audio_files(client, text_array):
    """Generate audio files for each text section."""
    file_paths = []
    for n, text_section in enumerate(text_array):
        try:
            # Replace with actual OpenAI TTS API call
            speech_response = client.audio.speech.create(
                model=TTS_MODEL, voice=TTS_VOICE, input=text_section
            )
            if not speech_response or not speech_response.content:
                raise ValueError("Failed to generate speech response")

            audio_path = OUTPUT_DIR / f"outputAudio{n}{AUDIO_EXT}"

            with audio_path.open("wb") as out_file:
                out_file.write(speech_response.content)

            if audio_path.stat().st_size == 0:
                raise ValueError("Written audio file is empty")

            file_paths.append(audio_path)
        except Exception as e:
            print(f"Error generating audio file: {e}")

    return file_paths