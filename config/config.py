# Configuration file for hand gesture mouse application

# --- CAMERA & TARGET SETUP ---
# Camera index: 0 for primary camera, 1 for secondary camera
CAMERA_INDEX = 0
TARGET_HAND = "Right"

# --- PERFORMANCE ---
# Target frames per second
TARGET_FPS = 30
SECONDS_TO_SAVE = 1
SHOW_VISUALIZATION = True

# --- GESTURE THRESHOLDS ---
MULTIPLIER_DISTANCE = 0.3
CLICK_COOLDOWN = 0.05

# --- MOUSE MOVEMENT & SMOOTHING ---
MOUSE_SENSITIVITY = 1.5
SMOOTH_TIME = 0.25      # LERP smoothing (lower is smoother but slower)
DEADZONE = 1.0          # Deadzone in pixels to prevent jitter
SCROLL_SENSITIVITY = 3000

# --- DRAG SETTINGS ---
DRAG_ACTIVATION_FRAMES = 4

# --- GESTURES DEFINITION ---
GESTURES = {
    "left_click": {
        "touching": ["thumb", "index"],
        "away": ["all_others"]
    },
    "right_click": {
        "touching": ["thumb", "pinky"],
        "away": ["all_others"]
    },
    "mouse_move": {
        "touching": ["thumb", "middle"],
        "away": ["all_others"] 
    },
    "scroll": {
        "touching": ["thumb", "ring"],
        "away": ["all_others"]
    },
    "drag": {
        "touching": ["thumb", "ring", "middle"],
        "away": ["all_others"]
    }
}