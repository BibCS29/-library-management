#!/usr/bin/env python3
import os
import shutil

app_path = 'app.py'
app_new_path = 'app_new.py'

# Remove old app.py
if os.path.exists(app_path):
    os.remove(app_path)
    print(f"Removed {app_path}")

# Copy new app
if os.path.exists(app_new_path):
    shutil.copy(app_new_path, app_path)
    print(f"Copied {app_new_path} to {app_path}")
    os.remove(app_new_path)
    print(f"Removed {app_new_path}")
    print("Setup complete!")
else:
    print(f"Error: {app_new_path} not found")
