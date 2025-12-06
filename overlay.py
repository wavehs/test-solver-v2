import tkinter as tk
import ctypes
import queue
import logging
import math
import sys
from config_manager import load_config

# Conditional import for macOS
if sys.platform == "darwin":
    try:
        import objc
        import AppKit
    except ImportError:
        pass # Handle in code


logger = logging.getLogger(__name__)

class Overlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw() # Hide initially
        
        self.config = load_config()

        # Window setup
        self.root.overrideredirect(True) # No borders
        self.root.attributes("-topmost", True) # Always on top
        
        # Apply Opacity
        self.opacity = self.config.get("overlay_opacity", 0.8)
        
        if sys.platform == "win32":
            self.root.attributes("-transparentcolor", "white") # White will be transparent
            self.bg_color = "white"
            self.root.attributes("-alpha", self.opacity)
        elif sys.platform == "darwin":
            # macOS transparency
            self.root.wait_visibility(self.root)
            self.root.attributes("-alpha", self.opacity)
            self.root.attributes("-transparent", True)
            self.root.config(bg='systemTransparent')
        elif sys.platform == "darwin":
            # macOS transparency
            # On macOS, we need to wait for visibility before setting attributes sometimes,
            # but for transparency 'systemTransparent' is key.
            self.root.wait_visibility(self.root)
            self.root.attributes("-alpha", self.opacity)
            self.root.attributes("-transparent", True)
            self.root.config(bg='systemTransparent')
            self.bg_color = "systemTransparent"
            
            # Ensure the window is borderless and floating
            self.root.overrideredirect(True)

        else:
            # Linux/Other - fallback
            self.root.attributes("-alpha", self.opacity)
            self.bg_color = "white"
        
        # Frame to hold everything
        self.frame = tk.Frame(self.root, bg=self.bg_color)
        self.frame.pack()

        # Size Settings
        self.size = self.config.get("overlay_size", 12)
        
        # Canvas for Status Indicator (Circle)
        self.canvas = tk.Canvas(self.frame, width=self.size, height=self.size, bg=self.bg_color, highlightthickness=0)
        self.canvas.pack(side="right", anchor="n")
        
        # Draw circle based on size
        padding = 1
        self.indicator = self.canvas.create_oval(padding, padding, self.size-padding, self.size-padding, fill="gray", outline="")

        # Label for text (Hidden by default)
        font_size = self.config.get("overlay_font_size", 12)
        text_color = self.config.get("overlay_text_color", "#00FF00")
        
        self.label = tk.Label(self.frame, text="", font=("Arial", font_size, "bold"), fg=text_color, bg=self.bg_color, justify="left")
        # We don't pack the label immediately, we'll pack/unpack it based on Alt key

        self.current_answer = None
        self.status = "IDLE" # IDLE, LOADING, READY
        self.is_alt_pressed = False
        self.loading_angle = 0
        self.animation_job = None

        # Initial Position
        self.update_position()
        self.root.deiconify()
        self.set_click_through()
        
        logger.debug("Overlay initialized with Status Indicator.")

    def update_position(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        position_mode = self.config.get("overlay_position", "Top-Right")
        offset_x = self.config.get("overlay_offset_x", 50)
        offset_y = self.config.get("overlay_offset_y", 20)
        
        width = self.frame.winfo_reqwidth()
        height = self.frame.winfo_reqheight()
        
        x_pos = 0
        y_pos = 0
        
        if position_mode == "Top-Right":
            x_pos = screen_width - width - offset_x
            y_pos = offset_y
        elif position_mode == "Top-Left":
            x_pos = offset_x
            y_pos = offset_y
        elif position_mode == "Bottom-Right":
            x_pos = screen_width - width - offset_x
            y_pos = screen_height - height - offset_y
        elif position_mode == "Bottom-Left":
            x_pos = offset_x
            y_pos = screen_height - height - offset_y
            
        self.root.geometry(f"+{int(x_pos)}+{int(y_pos)}")

    def set_status(self, status):
        self.status = status
        logger.debug(f"Status changed to: {status}")
        
        if status == "IDLE":
            self.canvas.itemconfig(self.indicator, fill="gray")
            self.stop_loading_animation()
            self.current_answer = None
            self.hide_text()
            
        elif status == "LOADING":
            self.start_loading_animation()
            self.hide_text()
            
        elif status == "READY":
            self.stop_loading_animation()
            self.canvas.itemconfig(self.indicator, fill="#00FF00") # Green
            # Text is ready but hidden until Alt is pressed

    def set_answer(self, text):
        self.current_answer = text
        self.label.config(text=text)
        self.set_status("READY")

    def toggle_text_visibility(self):
        if self.status == "READY" and self.is_alt_pressed:
            self.show_text()
        else:
            self.hide_text()

    def show_text(self):
        # Show label to the left of the indicator
        self.label.pack(side="right", padx=10)
        # Adjust window size/position to fit text
        self.root.update_idletasks()
        self.update_position()

    def hide_text(self):
        self.label.pack_forget()
        # Reset position to just the circle
        self.update_position()

    def start_loading_animation(self):
        if self.animation_job:
            return
        self.animate_loading()

    def stop_loading_animation(self):
        if self.animation_job:
            self.root.after_cancel(self.animation_job)
            self.animation_job = None

    def animate_loading(self):
        # Simple color pulsing or rotating effect
        colors = ["#CCCCCC", "#AAAAAA", "#888888", "#666666", "#888888", "#AAAAAA"]
        color = colors[int(self.loading_angle) % len(colors)]
        self.canvas.itemconfig(self.indicator, fill=color)
        self.loading_angle += 0.5
        self.animation_job = self.root.after(100, self.animate_loading)

    def set_alt_pressed(self, pressed):
        if self.is_alt_pressed != pressed:
            self.is_alt_pressed = pressed
            self.toggle_text_visibility()

    def set_click_through(self):
        if sys.platform == "win32":
            try:
                hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
                style = ctypes.windll.user32.GetWindowLongW(hwnd, -20) # GWL_EXSTYLE
                style = style | 0x80000 | 0x20 # WS_EX_LAYERED | WS_EX_TRANSPARENT
                ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)
            except Exception as e:
                logger.error(f"Could not set click-through: {e}")
        elif sys.platform == "darwin":
            try:
                if 'AppKit' in sys.modules and 'objc' in sys.modules:
                    # Get the NSView from Tkinter's window ID
                    # winfo_id() returns the pointer to the NSView on macOS
                    ns_view_ptr = self.root.winfo_id()
                    ns_view = objc.objc_object(c_void_p=ns_view_ptr)
                    ns_window = ns_view.window()
                    
                    # Set ignoresMouseEvents to True (click-through)
                    ns_window.setIgnoresMouseEvents_(True)
                    
                    # Ensure it stays on top (NSFloatingWindowLevel = 3, NSStatusWindowLevel = 25)
                    # attributes("-topmost") usually sets it to NSFloatingWindowLevel
                    # We can enforce it if needed, but let's stick to the basics first.
                    logger.debug("macOS click-through enabled.")
                else:
                    logger.warning("pyobjc-framework-Cocoa not installed. Click-through disabled.")
            except Exception as e:
                logger.error(f"Could not set click-through on macOS: {e}")


    def listen_to_queue(self, q):
        try:
            while True:
                action, data = q.get_nowait()
                if action == "status":
                    self.set_status(data)
                elif action == "answer":
                    self.set_answer(data)
                elif action == "alt":
                    self.set_alt_pressed(data)
                elif action == "exit":
                    self.root.quit()
        except queue.Empty:
            pass
        finally:
            self.root.after(50, self.listen_to_queue, q)

    def run(self):
        self.root.mainloop()

def main():
    app = Overlay()
    # For preview, show some dummy text
    app.set_answer("Preview Text")
    app.run()

if __name__ == "__main__":
    main()
