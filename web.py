from threading import Lock

import cherrypy

__all__ = ["run_web"]


class SingletonCherryPyApp:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        cherrypy.config.update(
            {
                "server.socket_host": "0.0.0.0",
                "server.socket_port": 8080,
            }
        )

    def run(self):
        cherrypy.quickstart(RootController())


class RootController:
    @cherrypy.expose
    def index(self):
        return "Hello from CherryPy Singleton!"


def run_web():
    app = SingletonCherryPyApp()
    app.run()
