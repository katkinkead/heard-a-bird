"""Loopback-only setup client. Durable credentials never enter URLs or output."""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
import webbrowser

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

class SetupClient:
    def __init__(self, config, port=8765):
        if isinstance(port,bool) or not isinstance(port,int) or not 1 <= port <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        self.config = config
        self.base = "http://127.0.0.1:" + str(port)
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def request(self, path, data=None):
        if not path.startswith("/api/admin/") or "?" in path or "#" in path:
            raise ValueError("Use a local administrator route")
        request = Request(self.base+path,
                          data=json.dumps(data,allow_nan=False).encode() if data is not None else None,
                          headers={"Content-Type":"application/json", "Authorization":"Bearer "+self.config.secrets["admin_token"]})
        try:
            with self.opener.open(request,timeout=12) as response:
                raw = response.read(2*1024*1024+1)
                if len(raw)>2*1024*1024: raise ValueError("Setup response exceeded its limit")
                return json.loads(raw)
        except HTTPError as exc:
            # Do not echo remote/proxy bodies or the Authorization header.
            if exc.code in (401,403):
                raise RuntimeError("The running server belongs to a different data folder or this session is not local. Use its existing installation; do not replace credentials.") from None
            raise RuntimeError("Setup action was rejected (HTTP %s). Read status and the local diagnostic packet before retrying." % exc.code) from None
        except (URLError,TimeoutError,OSError):
            raise RuntimeError("The local helper is not responding. Check the bootstrap result and the private supervisor log.") from None

    def open_guide(self):
        result = self.request("/api/admin/setup-ticket", {})
        # Fragment is consumed once in the guide and removed immediately. It is
        # not sent in request URLs, referrers, diagnostics or command output.
        opened = webbrowser.open(self.base+"/guide/index.html#ticket="+result["ticket"])
        return {"opened":bool(opened), "guide":self.base+"/guide/index.html"}
