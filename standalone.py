import os
from threading import Thread
from time import sleep
import subprocess
import sys
def gethostip():
    if sys.platform.startswith('win'):
        # Windows
        result = subprocess.run(['ipconfig'], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if 'IPv4 Address' in line:
                return line.split(':')[-1].strip()
    else:
        # Unix/Linux/Mac
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
        return result.stdout.split()[0]
HOST = gethostip()
PORT = 80
def runserver():
    os.system(f'python manage.py runserver {HOST}:{PORT}')
os.system(f'python manage.py runserver {HOST}:{PORT}')


# def lunchchrome():
#     # ensure the django server is up and running
#     sleep(2)
#     # get ipv4 address
#     os.system(f'start chrome http://{HOST}:{PORT}')
# t1=Thread(target=runserver)

# t2=Thread(target=lunchchrome)

# t1.start()
# sleep(2)
# t2.start()