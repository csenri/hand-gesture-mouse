import os
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"
import cv2
import numpy as np
import time
import math
from collections import deque
import threading
import queue
from threading import Lock, Event
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import pyautogui

import gestures
import utils
import sys

# Ensure Python can find the config file
sys.path.insert(0, '..')
from config import config

# --- MEDIAPIPE SETUP (MODEL PATH ONLY) ---
model_path = r'../models/hand_landmarker.task'
base_options = python.BaseOptions(model_asset_path=model_path)
options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=1)

# --- CAMERA SETUP ---
cap = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_DSHOW) 
time_between_frames = 1.0 / config.TARGET_FPS
prev_time = 0 

# --- HISTORY BUFFER ---
buffer_size = int(config.SECONDS_TO_SAVE * config.TARGET_FPS)
landmark_history = deque(maxlen=buffer_size)

# --- PYAUTOGUI SETUP ---
pyautogui.PAUSE = 0  # Disable the default 0.1s pause to prevent camera freeze
pyautogui.FAILSAFE = False 
screen_width, screen_height = pyautogui.size()

# --- TRACKING VARIABLES ---
last_click_time = 0
prev_scroll_pos = None

# Movement smoothing variables
smoothed_x, smoothed_y = None, None
prev_x, prev_y = None, None

# Drag smoothing and state variables
is_dragging = False
drag_frame_count = 0
drag_smoothed_x, drag_smoothed_y = None, None
drag_prev_x, drag_prev_y = None, None

# --- LERP FUNCTION ---
def lerp(a, b, t):
    return a + (b - a) * t

# --- BACKGROUND MEDIAPIPE DETECTION THREAD ---
frame_queue = queue.Queue(maxsize=2)      # Latest frames to detect (drops old frames)
detection_queue = queue.Queue(maxsize=1)  # Latest detection results
stop_detection_event = Event()             # Signal to stop detection thread
detection_lock = Lock()                    # Thread-safe access to detection

def mediapipe_worker():
    """Background thread that continuously runs MediaPipe detection"""
    detector = vision.HandLandmarker.create_from_options(options)
    
    while not stop_detection_event.is_set():
        try:
            # Wait for a frame to process (timeout prevents blocking on exit)
            frame = frame_queue.get(timeout=0.1)
            
            # Run MediaPipe detection
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            detection_result = detector.detect(mp_image)
            
            # Store result (non-blocking, overwrites old detections)
            try:
                detection_queue.put_nowait(detection_result)
            except queue.Full:
                pass  # Drop old detection if queue is full
                
        except queue.Empty:
            continue

# Start background detection thread as daemon
detection_thread = threading.Thread(target=mediapipe_worker, daemon=True)
detection_thread.start()

# --- MAIN LOOP ---
while cap.isOpened():
    ret, frame = cap.read() 
    if not ret:
        continue
        
    current_time = time.time()
    
    if (current_time - prev_time) > time_between_frames:
        prev_time = current_time 

        # Send frame to detection thread (non-blocking)
        try:
            frame_queue.put_nowait(frame)
        except queue.Full:
            pass  # Skip if detector is still busy
        
        # Get latest detection result (non-blocking, use previous if none available)
        detection_result = None
        try:
            while True:
                detection_result = detection_queue.get_nowait()
        except queue.Empty:
            pass  # Use previous detection result if none available yet

        if detection_result and detection_result.hand_landmarks:
            valid_hand_found = False
            
            for idx in range(len(detection_result.hand_landmarks)):
                detected_hand_side = detection_result.handedness[idx][0].category_name
                
                if config.TARGET_HAND == "Both" or detected_hand_side == config.TARGET_HAND:
                    correct_hand_landmarks = detection_result.hand_landmarks[idx]
                    landmark_history.append(correct_hand_landmarks)
                    valid_hand_found = True
                    break 
            
            if valid_hand_found:
                
                # --- 1. DRAG LOGIC (Highest Priority) ---
                drag_pos = gestures.detect_drag_gesture(landmark_history)
                
                if drag_pos != None:
                    drag_frame_count += 1
                    
                    if drag_frame_count >= config.DRAG_ACTIVATION_FRAMES:
                        norm_x, norm_y = drag_pos
                        target_x = norm_x * screen_width
                        target_y = norm_y * screen_height
                        
                        if not is_dragging:
                            print("DRAG STARTED!")
                            pyautogui.mouseDown(button='left')
                            is_dragging = True
                            
                            drag_smoothed_x, drag_smoothed_y = target_x, target_y
                            drag_prev_x, drag_prev_y = target_x, target_y
                        
                        drag_smoothed_x = lerp(drag_smoothed_x, target_x, config.SMOOTH_TIME)
                        drag_smoothed_y = lerp(drag_smoothed_y, target_y, config.SMOOTH_TIME)
                        
                        dx = -(drag_smoothed_x - drag_prev_x) * config.MOUSE_SENSITIVITY
                        dy = (drag_smoothed_y - drag_prev_y) * config.MOUSE_SENSITIVITY
                        
                        magnitude = math.sqrt(pow(abs(dx), 2) + pow(abs(dy), 2))
                        
                        if magnitude > config.DEADZONE:
                            pyautogui.move(int(dx), int(dy), _pause=False)
                            
                        drag_prev_x, drag_prev_y = drag_smoothed_x, drag_smoothed_y
                else:
                    drag_frame_count = 0
                    if is_dragging:
                        print("DRAG STOPPED!")
                        pyautogui.mouseUp(button='left')
                        is_dragging = False
                        
                    drag_smoothed_x, drag_smoothed_y = None, None
                    drag_prev_x, drag_prev_y = None, None

                # --- 2. CLICK LOGIC ---
                if not is_dragging:
                    type_click = gestures.detect_single_double_click(landmark_history)
                    is_right_click = gestures.detect_left_click_gesture(landmark_history)
                    
                    if type_click != None:
                        if type_click == 1:
                            if (current_time - last_click_time) > config.CLICK_COOLDOWN:
                                print('SINGLE CLICK!')
                                pyautogui.click()
                                last_click_time = current_time
                        elif type_click == 2:
                            print('DOUBLE CLICK!')
                            pyautogui.doubleClick()
                            last_click_time = current_time

                    if is_right_click:
                        if (current_time - last_click_time) > config.CLICK_COOLDOWN:
                            print("RIGHT CLICK!")
                            pyautogui.click(button='right')
                            last_click_time = current_time

                # --- 3. RELATIVE MOUSE MOVEMENT LOGIC ---
                if not is_dragging:
                    mouse_pos = gestures.detect_mouse_move_gesture(landmark_history)
                            
                    if mouse_pos != None:
                        norm_x, norm_y = mouse_pos
                        target_x = norm_x * screen_width
                        target_y = norm_y * screen_height
                        
                        if smoothed_x is None:
                            smoothed_x, smoothed_y = target_x, target_y
                            prev_x, prev_y = target_x, target_y
                            
                        smoothed_x = lerp(smoothed_x, target_x, config.SMOOTH_TIME)
                        smoothed_y = lerp(smoothed_y, target_y, config.SMOOTH_TIME)
                        
                        dx = -(smoothed_x - prev_x) * config.MOUSE_SENSITIVITY
                        dy = (smoothed_y - prev_y) * config.MOUSE_SENSITIVITY
                        
                        magnitude = math.sqrt(pow(abs(dx), 2) + pow(abs(dy), 2))
                        
                        if magnitude > config.DEADZONE:
                            pyautogui.move(int(dx), int(dy), _pause=False)
                            
                        prev_x, prev_y = smoothed_x, smoothed_y
                    else:
                        smoothed_x, smoothed_y = None, None
                        prev_x, prev_y = None, None
                else:
                    smoothed_x, smoothed_y = None, None
                    prev_x, prev_y = None, None
                
                # --- 4. SCROLL LOGIC ---
                scroll_pos = gestures.detect_scroll(landmark_history)
                
                if scroll_pos != None:
                    norm_x, norm_y = scroll_pos
                    
                    if prev_scroll_pos != None:
                        delta_y = norm_y - prev_scroll_pos[1]
                        scroll_amount = int(-delta_y * config.SCROLL_SENSITIVITY)
                        
                        if abs(scroll_amount) > 10:
                            pyautogui.scroll(scroll_amount)
                    
                    prev_scroll_pos = (norm_x, norm_y)
                else:
                    prev_scroll_pos = None
                    
            else:
                smoothed_x, smoothed_y = None, None
                prev_x, prev_y = None, None
                prev_scroll_pos = None
                drag_smoothed_x, drag_smoothed_y = None, None
                drag_prev_x, drag_prev_y = None, None
                
                if is_dragging:
                    pyautogui.mouseUp(button='left')
                    is_dragging = False
                    
                landmark_history.clear()
        else:
            smoothed_x, smoothed_y = None, None
            prev_x, prev_y = None, None
            prev_scroll_pos = None
            drag_smoothed_x, drag_smoothed_y = None, None
            drag_prev_x, drag_prev_y = None, None
            
            if is_dragging:
                pyautogui.mouseUp(button='left')
                is_dragging = False
                
            landmark_history.clear()
        
        if config.SHOW_VISUALIZATION:
            try:
                # Recreate mp_image for visualization only
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                annotated_image = utils.draw_landmarks_on_image(mp_image.numpy_view(), detection_result)
                bgr_annotated_image = cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR)
                cv2.imshow('frame', bgr_annotated_image)
            except (NameError, AttributeError, TypeError):
                cv2.imshow('frame', frame)
            
    if cv2.waitKey(1) == ord('q'):
        break

# --- CLEANUP ---
stop_detection_event.set()  # Signal detection thread to stop
detection_thread.join(timeout=2)  # Wait for thread to finish
cap.release()
cv2.destroyAllWindows()