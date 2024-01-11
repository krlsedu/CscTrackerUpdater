import logging
import os
import shutil
import stat
import subprocess

from csctracker_py_core.models.emuns.config import Config
from csctracker_py_core.repository.http_repository import HttpRepository
from csctracker_py_core.repository.remote_repository import RemoteRepository
from csctracker_py_core.utils.configs import Configs
from git import Repo


def del_rw(action, name, exc):
    os.chmod(name, stat.S_IWRITE)
    os.remove(name)


class UpdaterService:
    def __init__(self, remote_repository: RemoteRepository, http_repository: HttpRepository):
        self.logger = logging.getLogger()
        self.remote_repository = remote_repository
        self.http_repository = http_repository

        self.username = Configs.get_env_variable(Config.GITHUB_USER)
        self.password = Configs.get_env_variable(Config.GITHUB_PASS)
        pass

    def update(self, lib_name, version, headers=None):
        self.logger.info(f"Updating {lib_name}")
        returns_ = []
        try:
            args_ = {}
            args = self.http_repository.get_args()
            for key in args.keys():
                args_[key] = args[key]
            args_['library'] = lib_name
            if 'period' in args_.keys():
                args_['period'] = f"library_version <> {version}"
            apps_att = self.remote_repository.get_objects("libraries",
                                                          data=args_,
                                                          headers=headers)
            apps_att.sort(key=lambda x: (x['app_att'] == 'CscTrackerUpdater', x['app_att']))
            for app_att in apps_att:
                try:
                    self.logger.info(f"Updating {app_att['app_att']}")
                    att_ = app_att['app_att']
                    repo_url = app_att['repo_url']
                    cred_repo_url = repo_url.replace("https://", f"https://{self.username}:{self.password}@")
                    folder_ = f"static/{att_}"
                    if os.path.exists(folder_):
                        shutil.rmtree(folder_, onerror=del_rw)
                    Repo.clone_from(cred_repo_url, folder_)
                    if self.edit_file(f"{folder_}/requirements.txt", version, lib_name):
                        self.commit_changes(folder_, f"Update {lib_name} to {version}")
                        changes = self.push_changes(folder_)
                        if changes["status"] == "ok":
                            self.logger.info(f"Updated {app_att['app_att']} successfully.")
                            app_att['library_version'] = version
                            self.remote_repository.update("libraries", ['id'], app_att, headers)
                        if os.path.exists(folder_):
                            shutil.rmtree(folder_, onerror=del_rw)
                        changes['app_att'] = app_att['app_att']
                        changes['library_version'] = version
                        changes['lib_name'] = lib_name
                        returns_.append(changes)
                    else:
                        self.logger.info(f"Library {lib_name} is already up to date.")
                        returns_.append({
                            "status": "ok",
                            'app_att': app_att['app_att'],
                            'library_version': version,
                            'lib_name': lib_name
                        })
                        if os.path.exists(folder_):
                            shutil.rmtree(folder_, onerror=del_rw)

                except Exception as e:
                    self.logger.error(e)
                    error_ = {
                        "status": "error",
                        'app_att': app_att['app_att'],
                        'library_version': version,
                        'lib_name': lib_name,
                        'error': str(e)
                    }
                    returns_.append(error_)
                    if os.path.exists(folder_):
                        shutil.rmtree(folder_, onerror=del_rw)
        except Exception as e:
            self.logger.error(e)
            returns_.append({"status": "error"})
        return returns_

    def edit_file(self, file_path, version, lib_name):
        try:
            with open(file_path, 'r') as file:
                lines = file.readlines()

            new_lines = []
            is_same = True

            for line in lines:
                new_line = f"{lib_name}=={version}\n" if (line.startswith(f"{lib_name}=") or line == lib_name) else line

                if line != new_line:
                    is_same = False

                new_lines.append(new_line)

            if is_same:
                self.logger.info("File is already up to date.")
                return False

            with open(file_path, 'w') as file:
                file.write("".join(new_lines))

            self.logger.info("File edited successfully.")
            return True
        except Exception as e:
            msg_ = f"An error occurred while editing the file: {str(e)}"
            self.logger.error(msg_)
            raise Exception(msg_)

    def commit_changes(self, repo_dir, commit_message):
        try:
            repo = Repo(repo_dir)
            repo.git.add(update=True)
            repo.index.commit(commit_message)
            self.logger.info("Changes committed successfully.")
        except Exception as e:
            msg_ = f"An error occurred while committing the changes: {str(e)}"
            self.logger.error(msg_)
            raise Exception(msg_)

    def push_changes(self, repo_dir, remote_name="origin", branch="master"):
        try:
            os.environ['GIT_ASKPASS'] = 'echo'
            os.environ['GIT_USERNAME'] = self.username
            os.environ['GIT_PASSWORD'] = self.password

            cmd = f'git push {remote_name} {branch}'

            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=repo_dir)

            output, errors = p.communicate()
            p.wait()

            if p.returncode:
                raise f"Push failed: {errors.strip()}"
            else:
                self.logger.info(f"Push successful: {output.strip()}")
                return {"status": "ok"}
        except Exception as e:
            msg_ = f"An error occurred while pushing the changes: {str(e)}"
            self.logger.error(msg_)
            raise Exception(msg_)
