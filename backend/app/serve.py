"""Run the API the way the Fly machine does: python -m app.serve

Like `uvicorn app.main:app --proxy-headers`, but the server object is handed
to app.idle, so an idle stop ends the process with exit code 0 and the
machine stays stopped until the next request.
"""

import os

import uvicorn

from app import idle

config = uvicorn.Config("app.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), proxy_headers=True)
server = uvicorn.Server(config)
idle.stop = lambda: setattr(server, "should_exit", True)

if __name__ == "__main__":
    server.run()
