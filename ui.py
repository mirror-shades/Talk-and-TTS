from kivy.uix.button import Button
from kivy.uix.textinput import TextInput

def create_api_key_input(app):
    app.api_input = TextInput(hint_text='Enter your API key')
    submit_button = Button(text='Submit API Key')
    submit_button.bind(on_press=app.submit_api_key)
    
    app.layout.add_widget(app.api_input)
    app.layout.add_widget(submit_button)

def create_main_buttons(app):
    chat_button = Button(text='Chat')
    tts_button = Button(text='TTS')
    reset_api_button = Button(text='Reset API')
    
    chat_button.bind(on_press=app.chat_function)
    tts_button.bind(on_press=app.tts_function)
    reset_api_button.bind(on_press=app.api_reset_function)
    
    app.layout.add_widget(chat_button)
    app.layout.add_widget(tts_button)
    app.layout.add_widget(reset_api_button)
    