#!/usr/bin/env python
# coding: utf-8
# Author：Shen Yi
# Date ：2021-04-14 22:03

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

from django.urls import path
from channels.generic.websocket import WebsocketConsumer, AsyncWebsocketConsumer
import time
import subprocess
import threading
from django.conf import settings


stop_thread = False


def tailf(f_log, send):
    output = subprocess.Popen(f"tail -f -n 100 {f_log}", stdout=subprocess.PIPE, shell=True)

    global stop_thread
    while not stop_thread:
        line = output.stdout.readline().decode("utf-8")
        if line:
            send(line.strip())
        time.sleep(0.1)
    output.kill()


class ViewLogs(WebsocketConsumer):
    """实时查看log日志"""

    def connect(self):
        global stop_thread
        stop_thread = False
        f_log = self.scope["query_string"].decode("utf-8").replace("file=", "").replace("lianjie", "/")
        f_log = f"{settings.DIR_TMP_PLOT}/{f_log}"
        self.thread = threading.Thread(target=tailf, args=(f_log, self.send,))
        self.thread.start()
        self.accept()

    def disconnect(self, close_code):
        global stop_thread
        stop_thread = True
        print("stop")

    def receive(self, text_data=None, bytes_data=None):
        pass


application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter(
            [path('view_log_channel/', ViewLogs)]
        )
    ),
})
