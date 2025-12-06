import threading
import queue
from pynput import keyboard
import time
import logging
import pystray
from PIL import Image, ImageDraw
import sys
import os

from screen_capture import capture_screen
from ai_client import get_answer
from overlay import Overlay
from config_manager import load_config

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Global state
tray_icon = None
app = None
hotkey_listener = None
key_listener = None
should_exit = False

def create_image():
    # Generate an image for the tray icon
    width = 64
    height = 64
    color1 = "black"
    color2 = "white"
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
    dc.rectangle((0, height // 2, width // 2, height), fill=color2)
    return image

def on_quit(icon, item):
    global should_exit
    should_exit = True
    icon.stop()
    logger.info("Exit requested via Tray.")
    
    # Stop listeners
    if hotkey_listener:
        hotkey_listener.stop()
    if key_listener:
        key_listener.stop()
        
    # Stop UI
    if app:
        ui_queue.put(("exit", None))

def setup_tray():
    global tray_icon
    image = create_image()
    menu = pystray.Menu(pystray.MenuItem('Exit', on_quit))
    tray_icon = pystray.Icon("AI Assistant", image, "Desktop AI Assistant", menu)
    tray_icon.run()

def on_activate():
    logger.info("Hotkey pressed! Triggering capture...")
    ui_queue.put(("status", "LOADING"))
    threading.Thread(target=process_request).start()

def process_request():
    try:
        logger.debug("Starting screen capture...")
        img_bytes = capture_screen()
        logger.debug("Screen capture finished.")
        
        logger.debug("Sending request to AI...")
        answer = get_answer(img_bytes)
        logger.info(f"AI Response received: {answer}")
        
        ui_queue.put(("answer", answer))
    except Exception as e:
        logger.error(f"Error during processing: {e}", exc_info=True)
        ui_queue.put(("answer", "Err"))

ui_queue = queue.Queue()

# Global state for keys
current_pressed_keys = set()
required_reveal_keys = set()

def get_key_name(key):
    if hasattr(key, 'char') and key.char:
        return key.char.lower()
    
    name = str(key).replace('Key.', '')
    if '_l' in name or '_r' in name:
        name = name.rsplit('_', 1)[0] # remove _l or _r
    
    return f"<{name}>"

def on_key_press(key):
    global current_pressed_keys, required_reveal_keys
    key_name = get_key_name(key)
    current_pressed_keys.add(key_name)
    
    if required_reveal_keys and required_reveal_keys.issubset(current_pressed_keys):
        ui_queue.put(("alt", True))

def on_key_release(key):
    global current_pressed_keys, required_reveal_keys
    key_name = get_key_name(key)
    if key_name in current_pressed_keys:
        current_pressed_keys.remove(key_name)
    
    if required_reveal_keys and not required_reveal_keys.issubset(current_pressed_keys):
        ui_queue.put(("alt", False))

def main():
    global app, hotkey_listener, key_listener, config
    
    # Load Config
    config = load_config()
    trigger_hotkey = config.get("trigger_hotkey", "<ctrl>+<alt>+z")
    
    # Parse reveal keys
    global required_reveal_keys
    reveal_hotkey_str = config.get("reveal_hotkey", "<alt>")
    required_reveal_keys = set(k.strip() for k in reveal_hotkey_str.split('+'))
    
    logger.info(f"Loaded config. Trigger: {trigger_hotkey}, Reveal: {required_reveal_keys}")

    # Initialize Overlay
    logger.info("Initializing Overlay...")
    app = Overlay()
    app.listen_to_queue(ui_queue)

    # Setup Global Hotkey
    try:
        hotkey_listener = keyboard.GlobalHotKeys({
            trigger_hotkey: on_activate
        })
        hotkey_listener.start()
    except Exception as e:
        logger.error(f"Failed to bind hotkey '{trigger_hotkey}': {e}")

    # Setup Key Listener for Reveal
    key_listener = keyboard.Listener(on_press=on_key_press, on_release=on_key_release)
    key_listener.start()
    
    # Start Tray Icon in separate thread
    tray_thread = threading.Thread(target=setup_tray, daemon=True)
    tray_thread.start()
    
    logger.info("Desktop AI Assistant started in background.")
    
    # Run UI loop
    try:
        app.run()
    except KeyboardInterrupt:
        logger.info("Application stopped by user.")
    finally:
        if hotkey_listener: hotkey_listener.stop()
        if key_listener: key_listener.stop()
        if tray_icon: tray_icon.stop()

if __name__ == "__main__":
    main()
