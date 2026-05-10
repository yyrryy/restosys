import os
from socket import socket
from time import sleep
def gethostip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        ip="localhost"
        s.close() 
    return ip
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