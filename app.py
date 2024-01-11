import threading

from csctracker_py_core.starter import Starter
from csctracker_py_core.utils.request_info import RequestInfo

from services.updater_service import UpdaterService
from csctracker_py_core.utils.interceptor import g
starter = Starter()
app = starter.get_app()
http_repository = starter.get_http_repository()

updater_service = UpdaterService(starter.get_remote_repository())


@app.route('/<library_name>/<version>')
def hello_world(library_name, version):  # put application's code here
    thead = threading.current_thread()
    g.correlation_id = f"updater_{library_name}-{version}_{RequestInfo.get_request_id()}"
    thead.__setattr__('correlation_id', g.correlation_id)
    return updater_service.update(library_name, version, http_repository.get_headers()), 200, {
        'Content-Type': 'application/json'}


starter.start()
