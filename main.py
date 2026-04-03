import os
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"
import cv2
import numpy as np
import time
import math
from collections import deque
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import pyautogui

import gestures
import utils

# path to the model that we are using
model_path = r'C:\Users\Enrico\Desktop\personal projects\hand mouse\models\hand_landmarker.task'
# declare the model that we are using
base_options = python.BaseOptions(model_asset_path=model_path)
# options to apply for model
options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=1)
# create model
detector = vision.HandLandmarker.create_from_options(options)

# to capture the video from the camera
cap = cv2.VideoCapture(1, cv2.CAP_DSHOW) 

# setting of framerate
target_fps = 30
time_between_frames = 1.0 / target_fps
prev_time = 0 

# seconds of History 
seconds_to_save = 1
buffer_size = int(seconds_to_save * target_fps)
landmark_history = deque(maxlen=buffer_size)

# --- TIMERS AND COOLDOWNS ---
gesture_cooldown = 0.1
last_move_time = 0

# --- RELATIVE MOUSE MOVEMENT SETUP ---
# Variable to store the hand's position in the previous frame
prev_hand_pos = None
# Multiplier to adjust the cursor speed (1.0 is default, higher is faster)
mouse_sensitivity = 1.5 

pyautogui.FAILSAFE = False 
screen_width, screen_height = pyautogui.size()

while cap.isOpened():
    ret, frame = cap.read() 
    if not ret:
        continue

    current_time = time.time()
    
    if (current_time - prev_time) > time_between_frames:
        prev_time = current_time 

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        detection_result = detector.detect(mp_image)

        if detection_result.hand_landmarks:
            landmark_history.append(detection_result.hand_landmarks[0])

            # --- CLICK LOGIC ---
            type_click = gestures.detect_single_double_click(landmark_history)
            if type_click != None:
                if type_click == 1:
                    print('SINGLE CLICK!')
                    pyautogui.click()
                elif type_click == 2:
                    print('DOUBLE CLICK!')
                    pyautogui.doubleClick()


            # --- LEFT CLICK ---
            is_left_click = gestures.detect_left_click_gesture(landmark_history)
            if is_left_click:
                print("LEFT CLICK!")
                pyautogui.click(button='right')

            if type_click != None:
                if type_click == 1:
                    print('SINGLE CLICK!')
                    pyautogui.click()
                elif type_click == 2:
                    print('DOUBLE CLICK!')
                    pyautogui.doubleClick()

            # --- RELATIVE MOUSE MOVEMENT LOGIC ---
            if (current_time - last_move_time) > gesture_cooldown:
                mouse_pos = gestures.detect_mouse_move_gesture(landmark_history)
                
                if mouse_pos != None:
                    norm_x, norm_y = mouse_pos
                    
                    # If we already have a previous position, calculate the shift
                    if prev_hand_pos != None:
                        # Calculate the difference (delta) between current and previous frame
                        # Note: delta_x is inverted (-) to mirror the camera feed properly
                        delta_x = -(norm_x - prev_hand_pos[0])
                        delta_y = (norm_y - prev_hand_pos[1])
                        
                        # Convert the normalized delta into actual screen pixel shifts
                        shift_x = int(delta_x * screen_width * mouse_sensitivity)
                        shift_y = int(delta_y * screen_height * mouse_sensitivity)
                        
                        # Shift the mouse relative to its CURRENT position on the screen
                        pyautogui.move(shift_x, shift_y, _pause=False)
                    
                    # Update the anchor position for the next frame
                    prev_hand_pos = (norm_x, norm_y)
                    last_move_time = current_time
                else:
                    # If the fingers are released (gesture stopped), reset the anchor
                    # This prevents the mouse from jumping when you start a new pinch
                    prev_hand_pos = None
        else:
            # If the hand leaves the screen entirely, reset the anchor
            prev_hand_pos = None
        
        # for debug purposes visualize the hand
        try:
            annotated_image = utils.draw_landmarks_on_image(mp_image.numpy_view(), detection_result)
            bgr_annotated_image = cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR)
            cv2.imshow('frame', bgr_annotated_image)
        except NameError:
            cv2.imshow('frame', frame)
            
    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()