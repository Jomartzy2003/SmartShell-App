import speech_recognition as sr
import time
import requests

def get_sensor_trigger():
    """
    Mock function representing physical hardware reading.
    In reality, this would read GPIO states from an MPU6050 accelerometer.
    """
    input("\n[Hardware] Press Enter to simulate a physical Crash Sensor trigger... ")
    return True

def handle_crash():
    print("\n" + "="*50)
    print("!!! CRASH SENSOR TRIGGERED !!!")
    print("="*50)
    print("You have 5 seconds to say 'CANCEL' or 'I AM OKAY' to abort.\n")
    
    recognizer = sr.Recognizer()
    
    # We open microphone and listen for up to 5 seconds
    with sr.Microphone() as source:
        # Quick ambient noise adjustment
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        
        try:
            print("[Hardware: Listening...]")
            # timeout=5 means if nobody speaks for 5s, it throws WaitTimeoutError
            # phrase_time_limit=4 means it stops recording after 4s of speech
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=4)
            text = recognizer.recognize_google(audio).lower()
            print(f"[Hardware: Heard] '{text}'")
            
            if "cancel" in text or "okay" in text or "ok" in text:
                print(">>> Cancellation command detected! Aborting backend alert. <<<")
                return # User cancelled, do nothing further.
                
        except sr.WaitTimeoutError:
            print("[Hardware: Result] No speech detected within 5 seconds.")
        except sr.UnknownValueError:
            print("[Hardware: Result] Speech unintelligible (assuming not a cancel).")
        except sr.RequestError as e:
            print(f"[Hardware: Error] Speech recognition service offline - {e}")
            print("[Hardware: Result] Proceeding with alert to be safe.")
        except Exception as e:
            print(f"[Hardware: Error] Exception with microphone: {e}")

    # If the function hasn't returned yet, 5 seconds passed without cancellation!
    print("\n>>> 5 SECOND GRACE PERIOD EXPIRED. DISPATCHING ALERT TO BACKEND! <<<\n")
    
    try:
        # Send HTTP POST to the backend
        # In this workflow, simulate_crash immediately notifies dashboard of an uncancelled crash.
        payload = {
            "rider_id": 1,
            "status": "CRASH_CONFIRMED"
        }
        # In a real setup, replacing localhost with the actual IP/Domain of the FastAPI backend.
        response = requests.post("http://localhost:8000/simulate_crash", json=payload, timeout=5)
        print(f"[Hardware: Backend Response] HTTP {response.status_code}: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"[Hardware: FATAL] Failed to reach backend: {e}")

if __name__ == "__main__":
    print("SmartShell Raspberry Pi Client Initialized.")
    print("Monitoring IMU sensors...")
    while True:
        if get_sensor_trigger():
            handle_crash()
            print("\nResetting sensor loop...")
