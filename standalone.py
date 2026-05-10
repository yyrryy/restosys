from asyncio import sleep
import os
import socket


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


HOST = get_local_ip()
PORT = 80


def runserver():
    from restosys.settings import USE_SQLITE

    if USE_SQLITE:
        os.system(f'python manage.py runserver {HOST}:{PORT}')
    else:
        os.system('python manage.py collectstatic --noinput')
        os.system(f'python -m waitress --listen={HOST}:{PORT} restosys.wsgi:application')


if __name__ == '__main__':
    runserver()
    sleep(2)  # Wait a moment to ensure the server is up
    # open edge after the server is up, edge not chrome



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
