from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from ui import create_main_buttons, create_api_key_input
from api_key_manager import load_api_key, save_api_key
from chat_function import chat_function
from tts_function import tts_function

class ChatbotApp(App):
    def build(self):
        self.api_key = load_api_key()
        
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        if not self.api_key:
            create_api_key_input(self)
        else:
            create_main_buttons(self)
        
        return self.layout
    
    def submit_api_key(self, instance):
        api_key = self.api_input.text.strip()
        if api_key:
            save_api_key(api_key)
            self.api_key = api_key
            self.layout.clear_widgets()

    def build_menu_function(self, instance):
        self.layout.clear_widgets()
        create_main_buttons(self)
    
    def chat_function(self, instance):
        self.layout.clear_widgets()
        chat_function(self)
    
    def tts_function(self, instance):
        self.layout.clear_widgets()
        tts_function(self)

    def api_reset_function(self, instance):
        self.api_key = None
        self.layout.clear_widgets()
        create_api_key_input(self)
        
if __name__ == '__main__':
    ChatbotApp().run()