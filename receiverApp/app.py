# Patch spyne.util.six to use system six
import os
import sys
import six
import six.moves.collections_abc
import http.cookies
import six.moves.urllib

import six.moves.urllib.parse
import six.moves.urllib.error
import six.moves.urllib.request

sys.modules['spyne.util.six'] = six
sys.modules['spyne.util.six.moves'] = six.moves
sys.modules['spyne.util.six.moves.collections_abc'] = six.moves.collections_abc
sys.modules['spyne.util.six.moves.http_cookies'] = http.cookies
sys.modules['spyne.util.six.moves.urllib'] = six.moves.urllib
sys.modules['spyne.util.six.moves.urllib.parse'] = six.moves.urllib.parse
sys.modules['spyne.util.six.moves.urllib.error'] = six.moves.urllib.error
sys.modules['spyne.util.six.moves.urllib.request'] = six.moves.urllib.request

if not hasattr(six, 'get_function_name'):
    six.get_function_name = lambda func: func.__name__





# Patch cgi for Python 3.13+
if 'cgi' not in sys.modules:
    import types
    import email.message
    cgi_module = types.ModuleType('cgi')
    
    def parse_header(line):
        m = email.message.Message()
        m['Content-Type'] = line
        params = m.get_params()
        if params is None:
            return m.get_content_type(), {}
        return m.get_content_type(), {k: v for k, v in params}
    
    cgi_module.parse_header = parse_header
    sys.modules['cgi'] = cgi_module



from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from spyne.application import Application
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from soap_service import QBWebConnectorSvc
from state_manager import StateManager
from pydantic import BaseModel
import uvicorn
import uuid

app = FastAPI(title="QBWC Receiver")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB
StateManager()

# Spyne App
soap_app = Application(
    [QBWebConnectorSvc],
    tns='http://developer.intuit.com/',
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11(),
)

wsgi_app = WsgiApplication(soap_app)

@app.post("/wsdl")
async def wsdl(request: Request):
    """
    Handle SOAP requests.
    We read the body and pass it to the WSGI app.
    """
    # Spyne WSGI app expects a WSGI environment.
    # We can use Starlette's WSGI adapter or just simple wrap for this specific path.
    # However, simpler to just run uvicorn with a specific setup or adapt manually.
    # A manual adaptation:
    environ = request.scope
    environ['wsgi.input'] = request.stream()
    
    # But wait, FastAPI is async, WSGI is sync.
    # A standard pattern for FastAPI + Spyne is a bit tricky.
    # The clean implementation:
    # Read body, call wsgi_app with a mock start_response.
    
    body = await request.body()
    
    response_data = []
    
    def start_response(status, headers, exc_info=None):
        pass # We ignore headers for this simple impl, or parse them if needed
    
    # We need to construct a proper WSGI environ
    # Minimal environ
    env = {
        'REQUEST_METHOD': request.method,
        'SCRIPT_NAME': '',
        'PATH_INFO': '/wsdl',
        'QUERY_STRING': request.url.query,
        'SERVER_NAME': 'localhost',
        'SERVER_PORT': '8000',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.version': (1,0),
        'wsgi.url_scheme': 'http',
        'wsgi.input':  _BytesIO(body),
        'wsgi.errors': _BytesIO(b''),
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
        'CONTENT_TYPE': request.headers.get('content-type', ''),
        'CONTENT_LENGTH': request.headers.get('content-length', '0'),
    }
    
    from fastapi import Response
    try:
        # Simple Custom WSGI run
        result = wsgi_app(env, start_response)
        # result is an iterable of bytes
        return Response(content=b"".join(result), media_type="text/xml")
    except Exception:
        import traceback
        traceback.print_exc()
        raise

import io
class _BytesIO(io.BytesIO):
    def readline(self, *args, **kwargs):
        return super().readline(*args, **kwargs)

# REST API Helpers
class TaskRequest(BaseModel):
    username: str = "admin"
    request_xml: str

@app.post("/queue_task")
def queue_task(task: TaskRequest):
    state = StateManager()
    task_id = state.queue_task_for_user(task.username, task.request_xml)
    return {"status": "queued", "task_id": task_id}

@app.get("/task_result/{task_id}")
def get_task_result(task_id: int):
    state = StateManager()
    conn = state.get_db()
    c = conn.cursor()
    c.execute("SELECT response_xml, status FROM tasks WHERE id = ?", (task_id,))
    row = c.fetchone()
    conn.close()
    if row and row['status'] == 'done':
        return {"result": row['response_xml'], "status": "done"}
    elif row:
        return {"result": None, "status": row['status']}
    return {"result": None, "status": "not_found"}

@app.get("/generate_qwc")
def generate_qwc(app_name: str = None, app_desc: str = "FastAPI QBWC"):
    if not app_name:
        app_name = os.getenv("QB_APP_NAME", "MyQBWCApp")
    """
    Generates a .qwc file.
    """
    owner_id = str(uuid.uuid4())
    file_id = str(uuid.uuid4())
    import socket
    hostname = socket.gethostname()
    try:
        ip_address = socket.gethostbyname(hostname)
    except:
        ip_address = "localhost"
    
    # Allow overriding via query param if auto-detection is wrong (e.g. multiple NICs)
    # But for now, let's try to use the detected IP.
    # Ideally we could use request.base_url but that might be localhost if accessed from localhost.
    
    url = f"http://{ip_address}:8000/wsdl"
    
    qwc = f"""<?xml version="1.0"?>
<QBWCXML>
   <AppName>{app_name}</AppName>
   <AppID></AppID>
   <AppURL>{url}</AppURL>
   <AppDescription>{app_desc}</AppDescription>
   <AppSupport>{url}</AppSupport>
   <UserName>admin</UserName>
   <OwnerID>{{{owner_id}}}</OwnerID>
   <FileID>{{{file_id}}}</FileID>
   <QBType>QBFS</QBType>
   <Style>Document</Style>
   <Scheduler>
      <RunEveryNSeconds>60</RunEveryNSeconds>
   </Scheduler>
</QBWCXML>"""
    from fastapi.responses import Response
    return Response(content=qwc, media_type="text/xml", headers={"Content-Disposition": "attachment; filename=app.qwc"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
