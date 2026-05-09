import customtkinter as ctk
import json
import threading
import time
from voice_engine import VoiceEngine

class RiderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SmartShell Rider App")
        self.geometry("800x480")
        
        # State
        self.countdown_active = False
        self.time_left = 5
        self.ws = None
        
        self.voice_engine = VoiceEngine(self.handle_voice_cancel)
        
        # UI Setup
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.status_frame.grid_rowconfigure(0, weight=1)
        self.status_frame.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(self.status_frame, text="System Armed\nWaiting for triggers...", font=("Inter", 40), text_color="#aaaaaa")
        self.status_label.grid(row=0, column=0)
        
        self.emergency_frame = ctk.CTkFrame(self, fg_color="#aa0000")
        self.emergency_frame.grid_rowconfigure((0, 1, 2), weight=1)
        self.emergency_frame.grid_columnconfigure(0, weight=1)
        
        self.alert_label = ctk.CTkLabel(self.emergency_frame, text="CRASH DETECTED!", font=("Inter", 60, "bold"), text_color="white")
        self.alert_label.grid(row=0, column=0, pady=(40, 0))
        
        self.timer_label = ctk.CTkLabel(self.emergency_frame, text="5", font=("Inter", 150, "bold"), text_color="#ffaaaa")
        self.timer_label.grid(row=1, column=0)
        
        self.instruction_label = ctk.CTkLabel(self.emergency_frame, text="Say 'CANCEL' or 'I AM OKAY' to abort", font=("Inter", 24), text_color="white")
        self.instruction_label.grid(row=2, column=0, pady=(0, 40))
        
        self.show_idle_screen()
        
        # Start Websocket Thread
        self.ws_thread = threading.Thread(target=self.run_ws_client, daemon=True)
        self.ws_thread.start()

    def show_idle_screen(self):
        self.emergency_frame.grid_forget()
        self.status_frame.grid(row=0, column=0, sticky="nsew")
        
    def show_emergency_screen(self):
        self.status_frame.grid_forget()
        self.emergency_frame.grid(row=0, column=0, sticky="nsew")
        self.timer_label.configure(text=str(self.time_left), text_color="#ffaaaa")
        
    def trigger_emergency(self):
        print("UI: Triggering emergency!")
        self.countdown_active = True
        self.time_left = 5
        self.show_emergency_screen()
        self.voice_engine.start_listening()
        self.update_timer()
        
    def update_timer(self):
        if not self.countdown_active:
            return
            
        if self.time_left > 0:
            self.timer_label.configure(text=str(self.time_left))
            self.time_left -= 1
            # Schedule next update in 1 second
            self.after(1000, self.update_timer)
        else:
            self.timer_label.configure(text="ALERT DISPATCHED")
            self.countdown_active = False
            self.voice_engine.stop_listening()
            # Send timeout to backend
            self.send_ws_message({"event": "CRASH_TIMEOUT", "rider_name": "Test Rider", "gps_lat": 34.0522, "gps_lng": -118.2437})
            
            # Reset UI after 5 seconds
            self.after(5000, self.reset_system)

    def handle_voice_cancel(self):
        self.after(0, self._ui_handle_cancel)
        
    def _ui_handle_cancel(self):
        self.countdown_active = False
        self.send_ws_message({"event": "CANCELLED"})
        self.timer_label.configure(text="CANCELLED", text_color="#aaffaa")
        self.after(3000, self.reset_system)

    def reset_system(self):
        self.countdown_active = False
        self.show_idle_screen()

    def run_ws_client(self):
        from websockets.sync.client import connect
        
        uri = "ws://localhost:8000/ws/rider"
        while True:
            try:
                with connect(uri) as websocket:
                    self.ws = websocket
                    print("Connected to Backend WS")
                    # Change UI state to connected if we want
                    while True:
                        response = websocket.recv()
                        data = json.loads(response)
                        if data.get("event") == "CRASH_DETECTED":
                            self.after(0, self.trigger_emergency)
            except Exception as e:
                print(f"WS Connection error: {e}")
                self.ws = None
                time.sleep(3)

    def send_ws_message(self, message: dict):
        if self.ws:
            try:
                self.ws.send(json.dumps(message))
            except Exception as e:
                print(f"Failed to send message: {e}")

if __name__ == "__main__":
    # CustomTkinter aesthetic config
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    app = RiderApp()
    app.mainloop()
