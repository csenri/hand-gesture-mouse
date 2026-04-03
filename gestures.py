import math
import time

_was_clicking = False
_last_click_time = 0
# ==========================================
# UTILITY FUNCTIONS
# Basic math and geometry operations used by the gesture detectors.
# ==========================================

def get_distance(point1, point2):
    """
    Calculates the Euclidean distance between two MediaPipe landmarks.
    Both points must have 'x' and 'y' attributes.
    """
    return math.sqrt((point1.x - point2.x)**2 + (point1.y - point2.y)**2)

def get_area_hand(latest_landmark):
    """
    Calculate the area that the hand is occupying in the image and normalize it
    """

# ==========================================
# GESTURE DETECTION FUNCTIONS
# Add new functions here in the future (e.g., detect_swipe, detect_scroll).
# ==========================================

def detect_click_gesture(history_buffer):

    if len(history_buffer)==0:
        return False
    
    fing_pos = history_buffer[-1]

    thumb  = fing_pos[4]
    index  = fing_pos[8]
    middle = fing_pos[12]
    ring   = fing_pos[16]
    pinky  = fing_pos[20]

    thumb_index = get_distance(thumb,index)
    thumb_middle     = get_distance(thumb,middle)
    thumb_ring       = get_distance(thumb,ring)
    thumb_pinky      = get_distance(thumb,pinky)

    click_thereshold = 0.04
    if (thumb_index<click_thereshold) and (thumb_middle>click_thereshold) and (thumb_ring>click_thereshold) and (thumb_pinky>click_thereshold):
        return True
    return False

def detect_single_double_click(history_buffer):
    """
    Analyzes the buffer and returns "SINGLE", "DOUBLE", or None.
    Manages its own timing and state memory.
    """
    # Tell Python we want to modify the variables defined outside this function
    global _was_clicking, _last_click_time
    
    # 1. Check the raw physical gesture
    is_clicking = detect_click_gesture(history_buffer)
    
    click_result = None
    current_time = time.time()
    double_click_delay = 0.9
    
    # 2. Edge Triggering Logic
    if is_clicking and not _was_clicking:
        time_since_last_click = current_time - _last_click_time
        
        if time_since_last_click <= double_click_delay:
            click_result = 2
            _last_click_time = 0 # Reset timer
        else:
            click_result = 1
            _last_click_time = current_time
            
    # 3. Update the memory for the next frame
    _was_clicking = is_clicking
    
    return click_result

def detect_left_click_gesture(history_buffer):

    if len(history_buffer)==0:
        return False
    
    fing_pos = history_buffer[-1]

    thumb  = fing_pos[4]
    index  = fing_pos[8]
    middle = fing_pos[12]
    ring   = fing_pos[16]
    pinky  = fing_pos[20]

    thumb_index = get_distance(thumb,index)
    thumb_middle     = get_distance(thumb,middle)
    thumb_ring       = get_distance(thumb,ring)
    thumb_pinky      = get_distance(thumb,pinky)

    click_thereshold = 0.04
    if (thumb_ring<click_thereshold) and (thumb_middle>click_thereshold) and (thumb_index>click_thereshold) and (thumb_pinky>click_thereshold):
        return True
    return False



def detect_mouse_move_gesture(history_buffer):
    """
    Detects if the thumb and middle finger are pinching.
    Returns the (x, y) normalized coordinates if active, otherwise Returns None.
    """
    if len(history_buffer) == 0:
        return None
        
    fing_pos = history_buffer[-1]
    
    thumb = fing_pos[4]
    index = fing_pos[8]
    middle = fing_pos[12]
    
    # Calculate distance between thumb and middle finger
    thumb_middle_dist = get_distance(thumb, middle)
    
    # Ensure index finger is NOT touching to avoid accidental left clicks while moving
    thumb_index_dist = get_distance(thumb, index)
    
    touch_threshold = 0.04
    
    # If thumb and middle are touching, and index is far away
    if (thumb_middle_dist < touch_threshold) and (thumb_index_dist > touch_threshold):
        # Calculate the center point between the thumb and middle finger
        center_x = (thumb.x + middle.x) / 2.0
        center_y = (thumb.y + middle.y) / 2.0
        
        return (center_x, center_y)
        
    return None