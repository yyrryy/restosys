import os
from threading import Thread
from time import sleep
import socket
import subprocess
from waitress import serve
from restosys.wsgi import application  # Replace with your project name

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except:
        ip = 'localhost'
    finally:
        s.close()
    return ip

ip = get_local_ip()
local_port = 80       # Local port for Waitress
remote_port = 8081      # Port on remote server
remote_user = "boxer"
remote_host = "167.71.77.64"

def runserver():
    # Serve your Django app with Waitress
    serve(application, host="0.0.0.0", port=local_port)

def start_ssh_tunnel():
    sleep(2)  # Give Waitress a moment to start
    # Run SSH reverse tunnel in background
    cmd = [
        "ssh",
        "-fN",  # Run in background, no remote command
        "-R", f"{remote_port}:{ip}:{local_port}",
        f"{remote_user}@{remote_host}"
    ]
    print("Starting SSH reverse tunnel...")
    subprocess.Popen(cmd)
    print(f"Tunnel established: {remote_host}:{remote_port} -> {ip}:{local_port}")

def launch_chrome():
    sleep(4)  # Give Waitress a bit more time
    os.system(f'start chrome http://{ip}:{local_port}')

# Start server, SSH tunnel, and optional Chrome in parallel
t_server = Thread(target=runserver)
# t_ssh = Thread(target=start_ssh_tunnel)
t_chrome = Thread(target=launch_chrome)

t_server.start()
# t_ssh.start()
t_chrome.start()
