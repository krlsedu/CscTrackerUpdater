import logging
import os
import shutil
import subprocess

from csctracker_py_core.models.emuns.config import Config
from csctracker_py_core.repository.remote_repository import RemoteRepository
from csctracker_py_core.utils.configs import Configs
from git import Repo


class UpdaterService:
    def __init__(self, remote_repository: RemoteRepository):
        self.logger = logging.getLogger()
        self.remote_repository = remote_repository

        self.username = Configs.get_env_variable(Config.GITHUB_USER)
        self.password = Configs.get_env_variable(Config.GITHUB_PASS)
        pass

    def update(self, lib_name, version, headers=None):
        self.logger.info(f"Updating {lib_name}")
        try:
            apps_att = self.remote_repository.get_object("libraries",
                                                         data={"library": lib_name},
                                                         headers=headers)
            for app_att in apps_att:
                self.logger.info(f"Updating {app_att['app_att']}")
                att_ = app_att['app_att']
                repo_url = app_att['repo_url']
                cred_repo_url = repo_url.replace("https://", f"https://{self.username}:{self.password}@")
                folder_ = f"static/{att_}"
                if os.path.exists(folder_):
                    shutil.rmtree(folder_)
                Repo.clone_from(cred_repo_url, folder_)
                self.edit_file(f"{folder_}/requirements.txt", version, lib_name)
                self.commit_changes(folder_, f"Update {lib_name} to {version}")
                changes = self.push_changes(folder_)
                if changes["status"] == "ok":
                    self.logger.info(f"Updated {app_att['app_att']} successfully.")
                    app_att['version'] = version
                    self.remote_repository.update("libraries", ['id'], app_att, headers)
                return changes
        except Exception as e:
            self.logger.error(e)
            return {"status": "error"}

    def edit_file(self, file_path, version, lib_name):
        try:
            with open(file_path, 'r') as file:
                lines = file.readlines()

            # Replace the line if it starts with lib_name
            lines = [f"{lib_name}=={version}\n" if line.startswith(lib_name) else line for line in lines]

            # Open the file in write mode and write lines
            with open(file_path, 'w') as file:
                file.write("".join(lines))
            self.logger.info("File edited successfully.")
        except Exception as e:
            self.logger.exception(f"An error occurred while editing the file: {str(e)}")

    def commit_changes(self, repo_dir, commit_message):
        try:
            repo = Repo(repo_dir)
            repo.git.add(update=True)
            repo.index.commit(commit_message)
            self.logger.info("Changes committed successfully.")
        except Exception as e:
            self.logger.exception(f"An error occurred while committing the changes: {str(e)}")

    def push_changes(self, repo_dir, remote_name="origin", branch="master"):
        try:
            os.environ['GIT_ASKPASS'] = 'echo'
            os.environ['GIT_USERNAME'] = self.username
            os.environ['GIT_PASSWORD'] = self.password

            cmd = f'git push {remote_name} {branch}'

            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=repo_dir)

            output, errors = p.communicate()

            if p.returncode:
                self.logger.info(f"Push failed: {errors.strip()}")

                return {"status": "ok"}
            else:
                self.logger.info(f"Push successful: {output.strip()}")
        except Exception as e:
            self.logger.exception(f"An error occurred while pushing the changes: {str(e)}")

        return {"status": "error"}
