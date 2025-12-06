import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, colorchooser
import logging
import subprocess
import sys
import os
import threading
import webbrowser
from pynput import keyboard
from config_manager import load_config, save_config

logger = logging.getLogger(__name__)

# Set theme
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class Launcher(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("AI Assistant Launcher")
        self.geometry("600x600")
        
        self.config = load_config()
        self.recording_active = False
        self.current_keys = set()
        self.listener = None
        self.preview_process = None
        
        # Check for macOS dependencies
        if sys.platform == "darwin":
            try:
                import objc
                import AppKit
            except ImportError:
                # Use after(100) to ensure window is ready
                self.after(100, lambda: messagebox.showwarning(
                    "Missing Dependency", 
                    "To enable click-through on macOS, please install 'pyobjc-framework-Cocoa'.\n\npip install pyobjc-framework-Cocoa"
                ))
        
        # Grid Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Title
        self.grid_rowconfigure(1, weight=1) # Tabs
        self.grid_rowconfigure(2, weight=0) # Launch Button
        self.grid_rowconfigure(3, weight=0) # Footer
        
        # Title
        self.frame_title = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        self.lbl_title = ctk.CTkLabel(self.frame_title, text="Desktop AI Assistant", font=("Roboto Medium", 24))
        self.lbl_title.pack()
        
        # Tab View
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        self.tab_general = self.tabview.add("General")
        self.tab_overlay = self.tabview.add("Overlay")
        
        self.setup_general_tab()
        self.setup_overlay_tab()
        
        # Launch Button
        self.btn_launch = ctk.CTkButton(self, text="Launch (Hidden Mode)", command=self.on_launch, height=40, font=("Roboto Medium", 16))
        self.btn_launch.grid(row=2, column=0, padx=40, pady=(10, 20), sticky="ew")
        
        # Footer
        self.lbl_footer = ctk.CTkLabel(self, text="Application will run in background. Use Tray Icon to exit.", font=("Roboto", 10), text_color="gray")
        self.lbl_footer.grid(row=3, column=0, pady=(0, 10))

    def setup_general_tab(self):
        self.tab_general.grid_columnconfigure(1, weight=1)
        
        # Trigger Hotkey
        self.lbl_trigger = ctk.CTkLabel(self.tab_general, text="Trigger Hotkey:", font=("Roboto", 14))
        self.lbl_trigger.grid(row=0, column=0, padx=15, pady=20, sticky="w")
        
        self.entry_trigger = ctk.CTkEntry(self.tab_general, placeholder_text="<ctrl>+<alt>+z", width=150)
        self.entry_trigger.insert(0, self.config.get("trigger_hotkey", "<ctrl>+<alt>+z"))
        self.entry_trigger.grid(row=0, column=1, padx=10, pady=20, sticky="ew")
        
        self.btn_record_trigger = ctk.CTkButton(self.tab_general, text="Record", width=80, command=lambda: self.start_recording(self.entry_trigger, self.btn_record_trigger))
        self.btn_record_trigger.grid(row=0, column=2, padx=15, pady=20)

        # Reveal Hotkey
        self.lbl_reveal = ctk.CTkLabel(self.tab_general, text="Reveal Key:", font=("Roboto", 14))
        self.lbl_reveal.grid(row=1, column=0, padx=15, pady=20, sticky="w")
        
        self.entry_reveal = ctk.CTkEntry(self.tab_general, placeholder_text="<alt>", width=150)
        self.entry_reveal.insert(0, self.config.get("reveal_hotkey", "<alt>"))
        self.entry_reveal.grid(row=1, column=1, padx=10, pady=20, sticky="ew")
        
        self.btn_record_reveal = ctk.CTkButton(self.tab_general, text="Record", width=80, command=lambda: self.start_recording(self.entry_reveal, self.btn_record_reveal))
        self.btn_record_reveal.grid(row=1, column=2, padx=15, pady=20)

        # Gemini API Key
        self.lbl_api_key = ctk.CTkLabel(self.tab_general, text="Gemini API Key:", font=("Roboto", 14))
        self.lbl_api_key.grid(row=2, column=0, padx=15, pady=20, sticky="w")

        self.entry_api_key = ctk.CTkEntry(self.tab_general, placeholder_text="Enter API Key", width=150)
        self.entry_api_key.insert(0, self.config.get("gemini_api_key", ""))
        self.entry_api_key.grid(row=2, column=1, padx=10, pady=20, sticky="ew")

        self.btn_get_key = ctk.CTkButton(self.tab_general, text="Get Key", width=60, command=self.open_api_key_url)
        self.btn_get_key.grid(row=2, column=2, padx=(5, 0), pady=20, sticky="w")

        self.btn_paste_key = ctk.CTkButton(self.tab_general, text="Paste", width=50, command=self.paste_api_key)
        self.btn_paste_key.grid(row=2, column=2, padx=(70, 0), pady=20, sticky="w")

        # Explicitly bind Ctrl+V for the entry
        self.entry_api_key.bind("<Control-v>", self.on_paste_event)

        self.btn_test_api = ctk.CTkButton(self.tab_general, text="Test API", width=80, command=self.test_api)
        self.btn_test_api.grid(row=2, column=2, padx=(130, 0), pady=20, sticky="w")

        self.btn_save_key = ctk.CTkButton(self.tab_general, text="Save", width=50, command=self.save_api_key)
        self.btn_save_key.grid(row=2, column=2, padx=(220, 0), pady=20, sticky="w")

        # Gemini Model
        self.lbl_model = ctk.CTkLabel(self.tab_general, text="Gemini Model:", font=("Roboto", 14))
        self.lbl_model.grid(row=3, column=0, padx=15, pady=20, sticky="w")

        self.combo_model = ctk.CTkComboBox(self.tab_general, values=["gemini-2.5-pro", "gemini-2.5-flash"], width=150)
        self.combo_model.set(self.config.get("gemini_model", "gemini-2.5-pro"))
        self.combo_model.grid(row=3, column=1, padx=10, pady=20, sticky="ew")

    def open_api_key_url(self):
        webbrowser.open("https://aistudio.google.com/app/apikey")

    def paste_api_key(self):
        try:
            clipboard_text = self.clipboard_get()
            self.entry_api_key.delete(0, tk.END)
            self.entry_api_key.insert(0, clipboard_text)
        except Exception:
            pass

    def on_paste_event(self, event):
        try:
            clipboard_text = self.clipboard_get()
            self.entry_api_key.delete(0, tk.END)
            self.entry_api_key.insert(0, clipboard_text)
            return "break" # Prevent default behavior if it was interfering
        except Exception:
            pass

    def test_api(self):
        api_key = self.entry_api_key.get().strip()
        if not api_key:
            messagebox.showerror("Error", "Please enter an API Key first.")
            return

        # Save config to ensure key is persisted
        self.save_current_config()
            
        self.btn_test_api.configure(state="disabled", text="Testing...")
        threading.Thread(target=self.run_api_test, args=(api_key,), daemon=True).start()

    def run_api_test(self, api_key):
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model_name = self.combo_model.get()
            model = genai.GenerativeModel(model_name)
            response = model.generate_content("Hello, are you working?")
            
            if response and response.text:
                self.after(0, lambda: self.show_test_result("Success", f"API Key is working!\nModel: {model_name}\nResponse: {response.text}"))
            else:
                self.after(0, lambda: self.show_test_result("Warning", "API Key seems valid but returned empty response."))
        except Exception as e:
            self.after(0, lambda: self.show_test_result("Error", f"API Test Failed:\n{e}"))

    def show_test_result(self, type, message):
        self.btn_test_api.configure(state="normal", text="Test API")
        if type == "Success":
            messagebox.showinfo("Success", message)
        elif type == "Warning":
            messagebox.showwarning("Warning", message)
        else:
            messagebox.showerror("Error", message)

    def save_api_key(self):
        if self.save_current_config():
            messagebox.showinfo("Success", "API Key and Settings saved successfully.")

    def show_api_instructions(self):
        help_window = ctk.CTkToplevel(self)
        help_window.title("How to get Gemini API Key")
        help_window.geometry("400x350")
        
        # Make it modal
        help_window.transient(self)
        help_window.grab_set()
        
        lbl_title = ctk.CTkLabel(help_window, text="Instructions", font=("Roboto Medium", 16))
        lbl_title.pack(pady=(20, 10))
        
        instructions = (
            "1. Click 'Get Key' or go to:\n"
            "   https://aistudio.google.com/app/apikey\n\n"
            "2. Sign in with your Google account.\n\n"
            "3. Click on 'Create API key'.\n\n"
            "4. Select a project or create a new one.\n\n"
            "5. Copy the generated API key.\n\n"
            "6. Paste the key into the 'Gemini API Key'\n"
            "   field in this application.\n\n"
            "7. Click 'Launch' to save."
        )
        
        textbox = ctk.CTkTextbox(help_window, width=350, height=250)
        textbox.pack(pady=10, padx=20)
        textbox.insert("0.0", instructions)
        textbox.configure(state="disabled") # Read-only

    def setup_overlay_tab(self):
        self.tab_overlay.grid_columnconfigure(1, weight=1)
        
        # Position
        ctk.CTkLabel(self.tab_overlay, text="Position:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.combo_position = ctk.CTkComboBox(self.tab_overlay, values=["Top-Right", "Top-Left", "Bottom-Right", "Bottom-Left"])
        self.combo_position.set(self.config.get("overlay_position", "Top-Right"))
        self.combo_position.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        # Offsets
        ctk.CTkLabel(self.tab_overlay, text="Offset X:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.entry_offset_x = ctk.CTkEntry(self.tab_overlay)
        self.entry_offset_x.insert(0, str(self.config.get("overlay_offset_x", 50)))
        self.entry_offset_x.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        ctk.CTkLabel(self.tab_overlay, text="Offset Y:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.entry_offset_y = ctk.CTkEntry(self.tab_overlay)
        self.entry_offset_y.insert(0, str(self.config.get("overlay_offset_y", 20)))
        self.entry_offset_y.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        
        # Opacity
        ctk.CTkLabel(self.tab_overlay, text="Opacity:").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        self.slider_opacity = ctk.CTkSlider(self.tab_overlay, from_=0.1, to=1.0, number_of_steps=9)
        self.slider_opacity.set(self.config.get("overlay_opacity", 0.8))
        self.slider_opacity.grid(row=3, column=1, padx=10, pady=10, sticky="ew")
        
        # Size
        ctk.CTkLabel(self.tab_overlay, text="Indicator Size:").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.slider_size = ctk.CTkSlider(self.tab_overlay, from_=5, to=30, number_of_steps=25)
        self.slider_size.set(self.config.get("overlay_size", 12))
        self.slider_size.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
        
        # Text Color (Color Picker)
        ctk.CTkLabel(self.tab_overlay, text="Text Color:").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        
        self.color_frame = ctk.CTkFrame(self.tab_overlay, fg_color="transparent")
        self.color_frame.grid(row=5, column=1, padx=10, pady=5, sticky="ew")
        
        self.current_color = self.config.get("overlay_text_color", "#00FF00")
        
        self.lbl_color_preview = ctk.CTkLabel(self.color_frame, text="   ", fg_color=self.current_color, width=30, corner_radius=5)
        self.lbl_color_preview.pack(side="left", padx=5)
        
        self.btn_pick_color = ctk.CTkButton(self.color_frame, text="Pick Color", width=100, command=self.pick_color)
        self.btn_pick_color.pack(side="left", padx=5)

        # Preview Button
        self.btn_preview = ctk.CTkButton(self.tab_overlay, text="Show Preview", command=self.toggle_preview, fg_color="gray")
        self.btn_preview.grid(row=6, column=0, columnspan=2, padx=10, pady=20)

    def pick_color(self):
        color = colorchooser.askcolor(initialcolor=self.current_color)
        if color[1]: # color is ((r,g,b), hex)
            self.current_color = color[1]
            self.lbl_color_preview.configure(fg_color=self.current_color)
            # Update preview if active? Maybe later.

    def toggle_preview(self):
        if self.preview_process and self.preview_process.poll() is None:
            # Close preview
            self.preview_process.terminate()
            self.preview_process = None
            self.btn_preview.configure(text="Show Preview", fg_color="gray")
        else:
            # Save temp config for preview
            self.save_current_config()
            
            # Launch overlay
            if getattr(sys, 'frozen', False):
                # Running as compiled EXE
                self.preview_process = subprocess.Popen([sys.executable, "--preview"], cwd=os.path.dirname(sys.executable))
            else:
                if sys.platform == "win32":
                    python_executable = sys.executable.replace("python.exe", "pythonw.exe")
                    if not os.path.exists(python_executable):
                        python_executable = sys.executable
                else:
                    python_executable = sys.executable
                    
                overlay_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "overlay.py")
                self.preview_process = subprocess.Popen([python_executable, overlay_script], cwd=os.path.dirname(overlay_script))
            
            self.btn_preview.configure(text="Close Preview", fg_color="#3B8ED0") # Standard blue

    def start_recording(self, entry_widget, btn_widget):
        if self.recording_active:
            return
            
        self.recording_active = True
        self.current_keys = set()
        
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, "Press keys...")
        btn_widget.configure(text="Stop", state="disabled")
        self.focus()
        
        self.listener = keyboard.Listener(
            on_press=lambda k: self.on_key_press(k, entry_widget),
            on_release=lambda k: self.on_key_release(k, btn_widget)
        )
        self.listener.start()

    def format_key(self, key):
        if hasattr(key, 'char') and key.char:
            return key.char.lower()
        name = str(key).replace('Key.', '')
        if '_l' in name or '_r' in name:
            name = name.rsplit('_', 1)[0]
        return f"<{name}>"

    def get_hotkey_string(self):
        keys = list(self.current_keys)
        keys.sort(key=lambda k: (0 if 'ctrl' in k else 1 if 'alt' in k else 2 if 'shift' in k else 3 if 'cmd' in k else 4))
        return "+".join(keys)

    def on_key_press(self, key, entry_widget):
        key_str = self.format_key(key)
        self.current_keys.add(key_str)
        hotkey_str = self.get_hotkey_string()
        self.after(0, lambda: self.update_entry(entry_widget, hotkey_str))

    def on_key_release(self, key, btn_widget):
        self.recording_active = False
        self.listener.stop()
        self.after(0, lambda: btn_widget.configure(text="Record", state="normal"))

    def update_entry(self, entry, text):
        entry.delete(0, tk.END)
        entry.insert(0, text)

    def save_current_config(self):
        try:
            new_trigger = self.entry_trigger.get().strip()
            new_reveal = self.entry_reveal.get().strip()
            
            if not new_trigger or not new_reveal:
                # messagebox.showerror("Error", "Hotkeys cannot be empty") # Don't show error on preview save
                return False
                
            self.config["trigger_hotkey"] = new_trigger
            self.config["reveal_hotkey"] = new_reveal
            self.config["gemini_api_key"] = self.entry_api_key.get().strip()
            self.config["gemini_model"] = self.combo_model.get()
            
            # Save Overlay Settings
            self.config["overlay_position"] = self.combo_position.get()
            self.config["overlay_offset_x"] = int(self.entry_offset_x.get())
            self.config["overlay_offset_y"] = int(self.entry_offset_y.get())
            self.config["overlay_opacity"] = float(self.slider_opacity.get())
            self.config["overlay_size"] = int(self.slider_size.get())
            self.config["overlay_text_color"] = self.current_color
            
            save_config(self.config)
            return True
        except ValueError:
            messagebox.showerror("Error", "Invalid input for numeric fields")
            return False

    def on_launch(self):
        if self.save_current_config():
            # Close preview if open
            if self.preview_process and self.preview_process.poll() is None:
                self.preview_process.terminate()
                
            # Launch main.py
            if getattr(sys, 'frozen', False):
                # Running as compiled EXE
                subprocess.Popen([sys.executable, "--worker"], cwd=os.path.dirname(sys.executable))
            else:
                # Running as script
                if sys.platform == "win32":
                    python_executable = sys.executable.replace("python.exe", "pythonw.exe")
                    if not os.path.exists(python_executable):
                        python_executable = sys.executable
                else:
                    python_executable = sys.executable
                
                main_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
                subprocess.Popen([python_executable, main_script], cwd=os.path.dirname(main_script))
            
            self.destroy()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        # Terminate preview process if running
        if self.preview_process and self.preview_process.poll() is None:
            self.preview_process.terminate()
        
        # Stop listener if running
        if self.recording_active:
            self.listener.stop()
            
        self.destroy()

    def run(self):
        self.mainloop()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if "--worker" in sys.argv:
            import main
            main.main()
        elif "--preview" in sys.argv:
            import overlay
            overlay.main()
        else:
            app = Launcher()
            app.run()
    else:
        app = Launcher()
        app.run()
