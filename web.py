import cherrypy

__all__ = ["run_web"]


class run_web(object):
    @cherrypy.expose
    def index(self):
        return "Hello World!"


cherrypy.config.update(
    {
        "server.socket_host": "0.0.0.0",
        "server.socket_port": 8000,
    }
)
cherrypy.quickstart(run_web(), "/")
