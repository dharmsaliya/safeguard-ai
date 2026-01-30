# SPDX-FileCopyrightText: Copyright (C) ARDUINO SRL (http://www.arduino.cc)
# SPDX-License-Identifier: MPL-2.0

from arduino.app_utils import *
from arduino.app_bricks.web_ui import WebUI
import numpy as np
import time
import os
from collections import deque

# --- STANDARD LIBRARIES ---
import urllib.request
import urllib.parse
import base64
import json

try:
    import ai_edge_litert.interpreter as tflite
except ImportError:
    try:
        import tflite_runtime.interpreter as tflite
    except ImportError:
        import tensorflow.lite.interpreter as tflite

# ==========================================
# 1. CONFIGURATION & KEYS
# ==========================================
TWILIO_SID = "YOUR_TWILIO_SID" 
TWILIO_TOKEN = "YOUR_TWILIO_TOKEN" # 🚨 RESET THIS IN TWILIO CONSOLE
TWILIO_FROM = "YOUR_TWILIO_NUMBER"  
TWILIO_TO = "NUMBER_TO_CALL"       

current_dir = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(current_dir, "fall_model_int8.tflite")

# System State
current_threshold = 0.65 
user_profile = "Uncalibrated"
system_state = "MONITORING"
calibration_start_time = 0
CALIBRATION_DURATION = 15
calibration_buffer = []
last_call_time = 0  # To prevent multiple calls for one fall

raw_buffer = deque(maxlen=200)
prev_acc = None 

logger = Logger("SafeGuard-Final")
web_ui = WebUI()

# ==========================================
# 2. EMERGENCY CALL HANDLER
# ==========================================
def _trigger_emergency_call(data):
    global last_call_time
    last_call_time = time.time() # Block further attempts immediately
    logger.info("📞 INITIATING TWILIO CALL...")
    
    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Calls.json"
        
        impact = str(data.get('impact', 'Unknown'))
        temp = str(data.get('temp', 'Unknown'))
        
        # Cleaner TwiML format
        voice_xml = (
            f'<Response>'
            f'<Say voice="alice">Emergency Alert. A fall has been detected. '
            f'Impact force was {impact} G. Skin temperature is {temp} degrees.</Say>'
            f'</Response>'
        )
        
        # Twilio API is extremely picky. 
        # Try 'Twiml' (Capital T) which is the standard for the Calls.json endpoint.
        payload = {
            "To": TWILIO_TO.strip(),
            "From": TWILIO_FROM.strip(),
            "Twiml": voice_xml  # Changed from 'twiml' to 'Twiml'
        }
        
        data_encoded = urllib.parse.urlencode(payload).encode("utf-8")
        
        auth_str = f"{TWILIO_SID}:{TWILIO_TOKEN}"
        b64_auth = base64.b64encode(auth_str.encode()).decode("utf-8")
        
        req = urllib.request.Request(url, data=data_encoded, method="POST")
        req.add_header("Authorization", f"Basic {b64_auth}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        
        with urllib.request.urlopen(req) as response:
            logger.info(f"✅ TWILIO SUCCESS! Status: {response.getcode()}")
            return {"status": "success"}

    except urllib.error.HTTPError as e:
        # This will read the actual error message FROM Twilio
        error_msg = e.read().decode('utf-8')
        logger.error(f"❌ TWILIO REJECTED REQUEST: {error_msg}")
        return {"status": "error", "msg": error_msg}
    except Exception as e:
        logger.error(f"❌ SYSTEM ERROR: {e}")
        return {"status": "error", "msg": str(e)}

# ==========================================
# 3. SENSOR & MODEL LOGIC
# ==========================================
def _get_status():
    elapsed = 0
    if system_state == "CALIBRATING":
        elapsed = time.time() - calibration_start_time
        if elapsed > CALIBRATION_DURATION: elapsed = CALIBRATION_DURATION
    return { "state": system_state, "profile": user_profile, "threshold": round(current_threshold, 2), "progress": int((elapsed / CALIBRATION_DURATION) * 100) }

web_ui.expose_api("GET", "/status", _get_status)

def _start_calibration():
    global system_state, calibration_start_time, calibration_buffer
    system_state = "CALIBRATING"
    calibration_start_time = time.time()
    calibration_buffer = []
    return {"msg": "Started"}

web_ui.expose_api("POST", "/calibrate", _start_calibration)

class FallDetector:
    def __init__(self, model_path):
        try:
            self.interpreter = tflite.Interpreter(model_path=model_path)
            self.interpreter.allocate_tensors()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            self.input_index = self.input_details[0]['index']
            self.output_index = self.output_details[0]['index']
            self.scale, self.zero_point = self.input_details[0]['quantization']
            print("✅ Model Loaded")
        except Exception:
            self.interpreter = None

    def predict(self, input_data):
        if not self.interpreter: return [0.0, 0.0]
        if self.input_details[0]['dtype'] == np.int8:
            input_data = (input_data / self.scale + self.zero_point).astype(np.int8)
        else:
            input_data = input_data.astype(np.float32)

        input_data = np.expand_dims(input_data, axis=0)
        self.interpreter.set_tensor(self.input_index, input_data)
        self.interpreter.invoke()
        output_data = self.interpreter.get_tensor(self.output_index)
        
        if self.output_details[0]['dtype'] == np.int8:
            out_scale, out_zero = self.output_details[0]['quantization']
            output_data = (output_data.astype(np.float32) - out_zero) * out_scale
            
        return output_data[0]

fall_detector = FallDetector(MODEL_PATH)

def process_new_sample(ax, ay, az, gx, gy, gz):
    global prev_acc
    acc_mag = np.sqrt(ax**2 + ay**2 + az**2)
    gyro_mag = np.sqrt(gx**2 + gy**2 + gz**2)
    if prev_acc is None: jerk_x, jerk_y, jerk_z = 0.0, 0.0, 0.0
    else: jerk_x, jerk_y, jerk_z = (ax-prev_acc[0])*100, (ay-prev_acc[1])*100, (az-prev_acc[2])*100
    prev_acc = (ax, ay, az)
    return [ax, ay, az, gx, gy, gz, 0.0, acc_mag, gyro_mag, jerk_x, jerk_y, jerk_z]

def analyze_calibration():
    global current_threshold, user_profile, system_state
    data = np.array(calibration_buffer)
    magnitudes = data[:, 7] 
    activity_score = np.std(magnitudes)
    
    if activity_score < 0.05:
        user_profile = "Sedentary / Frail"
        current_threshold = 0.45
    elif activity_score > 0.30:
        user_profile = "Active / Athletic"
        current_threshold = 0.85
    else:
        user_profile = "Normal Baseline"
        current_threshold = 0.65
        
    system_state = "MONITORING"
    web_ui.send_message('calibration_done', { "profile": user_profile, "threshold": current_threshold })

def get_posture(ax, ay, az):
    abs_x, abs_y, abs_z = abs(ax), abs(ay), abs(az)
    if abs_z > abs_x and abs_z > abs_y:
        return "Lying Face Up" if az > 0 else "Lying Face Down ⚠️"
    elif abs_y > abs_x and abs_y > abs_z:
        return "Upright" if ay > 0 else "Upside Down"
    else:
        return "Lying on Side"

def record_sensor_movement(x, y, z, gx, gy, gz, temp):
    global last_call_time
    try:
        features = process_new_sample(x, y, z, gx, gy, gz)
        raw_buffer.append(features)

        if system_state == "CALIBRATING":
            calibration_buffer.append(features)
            if time.time() - calibration_start_time > CALIBRATION_DURATION: analyze_calibration()
            return

        if len(raw_buffer) % 10 == 0:
             web_ui.send_message('sample', {"t": time.time(), "x": x, "y": y, "z": z})

        if len(raw_buffer) == 200 and len(raw_buffer) % 10 == 0:
            if fall_detector and fall_detector.interpreter:
                preds = fall_detector.predict(np.array(raw_buffer, dtype=np.float32))
                prob_fall = float(preds[1])
                
                status_text = "NORMAL"
                impact_g = 0.0
                posture = "Unknown"

                if prob_fall > current_threshold:
                    status_text = "⚠️ FALL DETECTED ⚠️"
                    buffer_arr = np.array(raw_buffer)
                    impact_g = np.max(buffer_arr[:, 7]) 
                    posture = get_posture(x, y, z)
                    logger.warning(f"FALL! {impact_g:.1f}G | {posture} | {temp:.1f}C")

                    # 🔥 TRIGGER CALL DIRECTLY FROM CODE
                    # Only allow one call every 30 seconds
                    if time.time() - last_call_time > 30:
                        _trigger_emergency_call({'impact': round(impact_g, 1), 'temp': round(temp, 1)})
                        last_call_time = time.time()

                web_ui.send_message('movement', {
                    'status': status_text, 
                    'fall_prob': prob_fall,
                    'threshold': current_threshold,
                    'impact': round(impact_g, 1),
                    'posture': posture,
                    'temp': round(temp, 1)
                })

    except Exception as e:
        logger.error(f"Error: {e}")

Bridge.provide("record_sensor_movement", record_sensor_movement)
App.run()