from .models import Config
def getserverip():
    serverip = None
    conf = Config.objects.first()
    if conf:
        serverip = conf.serverip
    return serverip