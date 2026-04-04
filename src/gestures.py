import math
import time
import sys
sys.path.insert(0, '..')
from config import config

_was_clicking = False
_last_click_time = 0

# Dictionary to map finger names to their MediaPipe landmark indices
FINGER_MAP = {
    "thumb": 4,
    "index": 8,
    "middle": 12,
    "ring": 16,
    "pinky": 20,
}

# ==========================================
# UTILITY FUNCTIONS
# ==========================================

def get_distance(point1, point2):
    """
    Calculates the Euclidean distance between two MediaPipe landmarks.
    """
    return math.sqrt((point1.x - point2.x)**2 + (point1.y - point2.y)**2)

def get_dynamic_threshold(hand_landmarks, multiplier=config.MULTIPLIER_DISTANCE):
    """
    Calculates a dynamic threshold based on the size of the hand in the frame.
    """
    wrist = hand_landmarks[0]
    middle_mcp = hand_landmarks[9] 
    
    palm_size = get_distance(wrist, middle_mcp)
    return palm_size * multiplier

def is_gesture_active(fing_pos, gesture_config, threshold):
    """
    Generic function to check if a configured gesture is currently active.
    It supports any combination of fingers and the "all_others" keyword.
    """
    touching_names = gesture_config.get("touching", [])
    away_names = gesture_config.get("away", [])
    
    # A gesture needs at least two fingers to touch
    if len(touching_names) < 2:
        return False
        
    # Use the first finger in the 'touching' list as the reference point
    ref_finger_name = touching_names[0]
    ref_point = fing_pos[FINGER_MAP[ref_finger_name]]
    
    # 1. Check if ALL fingers in 'touching' are close to the reference finger
    for i in range(1, len(touching_names)):
        finger_point = fing_pos[FINGER_MAP[touching_names[i]]]
        if get_distance(ref_point, finger_point) > threshold:
            return False # One of the required fingers is too far
            
    # 2. Resolve the "all_others" keyword
    if "all_others" in away_names:
        # Generate a list of all fingers that are NOT in the 'touching' list
        actual_away_names = [f for f in FINGER_MAP.keys() if f not in touching_names]
    else:
        actual_away_names = away_names
        
    # 3. Check if the 'away' fingers are safely far from the reference finger
    for finger_name in actual_away_names:
        # Safeguard: prevent checking a finger against itself if config is wrong
        if finger_name in touching_names:
            continue
            
        finger_point = fing_pos[FINGER_MAP[finger_name]]
        if get_distance(ref_point, finger_point) < threshold:
            return False # A finger that should be away is too close
            
    return True

# ==========================================
# GESTURE DETECTION FUNCTIONS
# ==========================================

def detect_click_gesture(history_buffer):
    if len(history_buffer) == 0:
        return False
    
    fing_pos = history_buffer[-1]
    click_threshold = get_dynamic_threshold(fing_pos)
    
    return is_gesture_active(fing_pos, config.GESTURES["left_click"], click_threshold)

def detect_single_double_click(history_buffer):
    """
    Analyzes the buffer and returns 1 (SINGLE), 2 (DOUBLE), or None.
    Manages its own timing and state memory.
    """
    global _was_clicking, _last_click_time
    
    is_clicking = detect_click_gesture(history_buffer)
    
    click_result = None
    current_time = time.time()
    double_click_delay = 0.9
    
    if is_clicking and not _was_clicking:
        time_since_last_click = current_time - _last_click_time
        
        if time_since_last_click <= double_click_delay:
            click_result = 2
            _last_click_time = 0 
        else:
            click_result = 1
            _last_click_time = current_time
            
    _was_clicking = is_clicking
    
    return click_result

def detect_left_click_gesture(history_buffer):
    """
    This function detects the right-click action based on the config.
    """
    if len(history_buffer) == 0:
        return False
    
    fing_pos = history_buffer[-1]
    click_threshold = get_dynamic_threshold(fing_pos)
    
    return is_gesture_active(fing_pos, config.GESTURES["right_click"], click_threshold)

def detect_mouse_move_gesture(history_buffer):
    """
    Returns the (x, y) normalized coordinates of the primary touching finger.
    """
    if len(history_buffer) == 0:
        return None
        
    fing_pos = history_buffer[-1]
    touch_threshold = get_dynamic_threshold(fing_pos)
    
    if is_gesture_active(fing_pos, config.GESTURES["mouse_move"], touch_threshold):
        # Dynamically get the first finger involved in the movement gesture
        primary_finger = config.GESTURES["mouse_move"]["touching"][0]
        finger_point = fing_pos[FINGER_MAP[primary_finger]]
        return (finger_point.x, finger_point.y)
        
    return None

def detect_drag_gesture(history_buffer):
    """
    Detects if the drag gesture is active based on the config.
    Returns the (x, y) normalized coordinates of the primary touching finger, 
    otherwise returns None.
    """
    if len(history_buffer) == 0:
        return None
        
    fing_pos = history_buffer[-1]
    touch_threshold = get_dynamic_threshold(fing_pos)

    # Read the drag logic dynamically from config
    if is_gesture_active(fing_pos, config.GESTURES["drag"], touch_threshold):
        # Dynamically get the first finger involved in the drag gesture
        primary_finger = config.GESTURES["drag"]["touching"][0]
        finger_point = fing_pos[FINGER_MAP[primary_finger]]
        return (finger_point.x, finger_point.y)
        
    return None

def detect_scroll(history_buffer):
    """
    Returns the (x, y) normalized coordinates of the primary scrolling finger.
    """
    if len(history_buffer) == 0:
        return None
        
    fing_pos = history_buffer[-1]
    touch_threshold = get_dynamic_threshold(fing_pos)

    if is_gesture_active(fing_pos, config.GESTURES["scroll"], touch_threshold):
        # Dynamically get the first finger involved in the scroll gesture
        primary_finger = config.GESTURES["scroll"]["touching"][0]
        finger_point = fing_pos[FINGER_MAP[primary_finger]]
        return (finger_point.x, finger_point.y)
        
    return None