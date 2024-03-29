from csctracker_py_core.starter import Starter

from services.updater_service import UpdaterService

starter = Starter()
app = starter.get_app()
http_repository = starter.get_http_repository()

updater_service = UpdaterService(starter.get_remote_repository(), starter.get_http_repository())


@app.route('/<library_name>/<version>', methods=['POST'])
def update_services(library_name, version):
    return updater_service.update(library_name, version, http_repository.get_headers()), 200, {
        'Content-Type': 'application/json'}


starter.start()
