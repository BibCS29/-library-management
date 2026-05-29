import os
import shutil

# Backup old app.py
if os.path.exists('app.py'):
    shutil.copy('app.py', 'app_backup.py')
    os.remove('app.py')

# Rename new app
if os.path.exists('app_new.py'):
    os.rename('app_new.py', 'app.py')

print("Files updated successfully!")
