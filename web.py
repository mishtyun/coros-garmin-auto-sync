import cherrypy

__all__ = ["run_web"]


class run_web(object):
    @cherrypy.expose
    def index(self):
        return "Hello World!"


cherrypy.quickstart(run_web())
