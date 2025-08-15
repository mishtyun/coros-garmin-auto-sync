import cherrypy

__all__ = ["run_web"]


class RootController:
    @cherrypy.expose
    def index(self):
        return "Hello from CherryPy!"


def run_web():
    if cherrypy.engine.state == cherrypy.engine.states.STARTED:
        return

    cherrypy.config.update(
        {
            "server.socket_host": "0.0.0.0",
            "server.socket_port": 8080,
            "engine.autoreload.on": False,
        }
    )

    cherrypy.tree.mount(RootController(), "/")
    cherrypy.engine.start()
