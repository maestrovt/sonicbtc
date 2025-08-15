from datetime import datetime

def log(msg):
    print(f"[{datetime.now().strftime('%M:%S')}] {msg}")
