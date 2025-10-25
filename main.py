from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.properties import StringProperty, BooleanProperty
from kivy.utils import platform
from tracker import track_phone_number, get_history, clear_history, export_full_history
import webbrowser
import os

class TrackerApp(App):
    map_style = StringProperty("Standard")
    include_ip = BooleanProperty(False)

    def build(self):
        self.title = 'Phone Number Location Tracker'
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Input
        self.input = TextInput(hint_text='Enter phone number (+1234567890)', multiline=False, size_hint=(1, 0.1))
        layout.add_widget(self.input)

        # Options
        options = BoxLayout(orientation='horizontal', size_hint=(1, 0.1))
        options.add_widget(Label(text='Map Style:', size_hint=(0.3, 1)))
        self.standard = CheckBox(group='map', active=True, size_hint=(0.2, 1))
        self.standard.bind(active=self.set_standard)
        options.add_widget(self.standard)
        options.add_widget(Label(text='Standard', size_hint=(0.2, 1)))
        self.satellite = CheckBox(group='map', size_hint=(0.2, 1))
        self.satellite.bind(active=self.set_satellite)
        options.add_widget(self.satellite)
        options.add_widget(Label(text='Satellite', size_hint=(0.2, 1)))
        self.terrain = CheckBox(group='map', size_hint=(0.2, 1))
        self.terrain.bind(active=self.set_terrain)
        options.add_widget(self.terrain)
        options.add_widget(Label(text='Terrain', size_hint=(0.2, 1)))
        layout.add_widget(options)

        # IP Checkbox
        ip_box = BoxLayout(orientation='horizontal', size_hint=(1, 0.1))
        self.ip_check = CheckBox(active=False)
        self.ip_check.bind(active=self.set_ip)
        ip_box.add_widget(self.ip_check)
        ip_box.add_widget(Label(text='Include IP-Based Location'))
        layout.add_widget(ip_box)

        # Track Button
        track_btn = Button(text='Track Number', size_hint=(1, 0.1))
        track_btn.bind(on_press=self.track)
        layout.add_widget(track_btn)

        # Results
        self.results = Label(text='Results will appear here...', halign='left', valign='top', text_size=(None, None), size_hint=(1, 0.3))
        scroll = ScrollView()
        scroll.add_widget(self.results)
        layout.add_widget(scroll)

        # Buttons
        buttons = BoxLayout(orientation='horizontal', size_hint=(1, 0.1))
        history_btn = Button(text='View History')
        history_btn.bind(on_press=self.show_history)
        buttons.add_widget(history_btn)
        clear_btn = Button(text='Clear History')
        clear_btn.bind(on_press=self.clear_history)
        buttons.add_widget(clear_btn)
        export_btn = Button(text='Export History')
        export_btn.bind(on_press=self.export_history)
        buttons.add_widget(export_btn)
        layout.add_widget(buttons)

        return layout

    def set_standard(self, checkbox, value):
        if value:
            self.map_style = "Standard"

    def set_satellite(self, checkbox, value):
        if value:
            self.map_style = "Satellite"

    def set_terrain(self, checkbox, value):
        if value:
            self.map_style = "Terrain"

    def set_ip(self, checkbox, value):
        self.include_ip = value

    def track(self, instance):
        number = self.input.text.strip()
        result = track_phone_number(number, self.map_style, self.include_ip)
        if "error" in result:
            self.show_popup("Error", result["error"])
            return
        self.results.text = (
            f"Phone Number: {result['number']}\n"
            f"Type: {result['number_type']}\n"
            f"Country: {result['location']}\n"
            f"Location: {result['detailed_location']}\n"
            f"Provider: {result['service_provider']}\n"
            f"Time Zone: {result['time_zone']}\n"
            f"Coordinates: ({result['lat']}, {result['lng']})\n"
            f"Confidence: {result['confidence']}\n"
            f"IP Location: {result['ip_location']}\n"
            f"Map saved as: {result['map_file']}"
        )
        self.show_map(result['map_file'])

    def show_map(self, map_file):
        if platform == 'android':
            from jnius import autoclass
            from kivy.uix.webview import WebView
            popup = Popup(title='Map', size_hint=(0.9, 0.9))
            webview = WebView(url=map_file)
            popup.content = webview
            popup.open()
        else:
            webbrowser.open(f"file://{os.path.abspath(map_file)}")

    def show_history(self, instance):
        history = get_history()
        if not history:
            self.show_popup("Info", "No history available.")
            return
        popup = Popup(title='History', size_hint=(0.9, 0.9))
        layout = GridLayout(cols=1, padding=10, spacing=10, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        for entry in history:
            layout.add_widget(Label(
                text=f"Number: {entry['number']} ({entry['number_type']})\n"
                     f"Country: {entry['country']}, Location: {entry['detailed_location']}\n"
                     f"Time: {entry['timestamp']}\n"
                     f"IP: {entry['ip_location']}",
                halign='left', valign='top', text_size=(None, None)
            ))
        scroll = ScrollView()
        scroll.add_widget(layout)
        popup.content = scroll
        popup.open()

    def clear_history(self, instance):
        clear_history()
        self.show_popup("Success", "History cleared.")

    def export_history(self, instance):
        csv_file = export_full_history()
        self.show_popup("Success", f"History exported to {csv_file}")

    def show_popup(self, title, msg):
        popup = Popup(title=title, content=Label(text=msg), size_hint=(0.6, 0.4))
        popup.open()

if __name__ == '__main__':
    TrackerApp().run()