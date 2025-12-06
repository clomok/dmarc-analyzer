import os
import time
import socket
import subprocess
import sys

def wait_for_postgres(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while True:
        try:
            s.connect((host, port))
            s.close()
            print("PostgreSQL started")
            break
        except socket.error:
            print("Waiting for PostgreSQL...")
            time.sleep(1)

if __name__ == "__main__":
    # 1. Wait for DB
    wait_for_postgres('db', 5432)

    # 2. Run Migrations
    print("Applying Migrations...")
    subprocess.run(["python", "manage.py", "migrate"], check=True)

    # 3. Create Superuser (Idempotent & Secure)
    print("Checking for Superuser...")
    script = """
import os
from django.contrib.auth import get_user_model
User = get_user_model()
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f"Superuser '{username}' created")
else:
    print(f"Superuser '{username}' already exists")
"""
    # Pass environment variables to the subprocess
    subprocess.run(["python", "manage.py", "shell", "-c", script], check=True)

    # 4. Start Server
    print("Starting Server...")
    subprocess.run(["python", "manage.py", "runserver", "0.0.0.0:8000"])