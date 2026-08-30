import subprocess
import time
import signal
import sys
import socket
local_port = 80
remote_port = 5055
remote_user = "grillade"
remote_host = "167.71.77.64"

RESTART_DELAY = 5
process = None
running = True

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
def start_ssh_tunnel():
    global process
    cmd = [
        "ssh",
        "-N",  # no remote command
        "-R", f"{remote_port}:{ip}:{local_port}",
        "-o", "ServerAliveInterval=10",  # send keepalive every 10s
        "-o", "ServerAliveCountMax=3",   # disconnect if 3 keepalives fail
        f"{remote_user}@{remote_host}"
    ]

    print("Starting SSH reverse tunnel...")
    process = subprocess.Popen(cmd)
    print(f"Tunnel established: {remote_host}:{remote_port} -> {ip}:{local_port}")


def stop_tunnel():
    global process
    if process and process.poll() is None:
        print("Stopping SSH tunnel...")
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()

def stop_tunnel():
    """Stop the SSH tunnel if running."""
    global process
    if process and process.poll() is None:
        print("[INFO] Stopping SSH tunnel...")
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        process = None

def handle_exit(signum, frame):
    global running
    print("Shutting down tunnel manager...")
    running = False
    stop_tunnel()
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def is_tunnel_alive():
    """Check if the remote port is reachable (tunnel alive)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        s.connect((remote_host, remote_port))
        return True
    except:
        return False
    finally:
        s.close()

def main():
    global process

    while running:
        if process is None or process.poll() is not None or not is_tunnel_alive():
            if process:
                print("[WARN] Tunnel lost or SSH exited, restarting...")
                stop_tunnel()
            start_ssh_tunnel()
        time.sleep(RESTART_DELAY)


if __name__ == "__main__":
    main()
