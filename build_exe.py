import PyInstaller.__main__
import os
import sys
import subprocess

def install_dependencies():
    print("Installing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def build():
    # Auto-install dependencies first
    install_dependencies()

    # Define the main script
    main_script = "gui_launcher.py"
    
    # Define the output name
    app_name = "AI_Assistant"
    
    # Common arguments
    args = [
        main_script,
        "--onefile",
        "--noconsole",
        "--name", app_name,
        "--clean",
    ]
    
    if sys.platform == "darwin":
        # macOS specific arguments
        import platform
        arch = platform.machine()
        args.extend([
            "--target-arch", arch, # Explicitly build for the current architecture (arm64 or x86_64)
            "--argv-emulation", # Better compatibility for opening files/URLs
        ])
        print(f"Building {app_name} for macOS ({arch})...")
    else:
        print(f"Building {app_name} for Windows...")
    
    PyInstaller.__main__.run(args)
    
    if sys.platform == "darwin":
        print(f"Build complete. Check the 'dist' folder for {app_name}.app")
    else:
        print(f"Build complete. Check the 'dist' folder for {app_name}.exe")

if __name__ == "__main__":
    build()

