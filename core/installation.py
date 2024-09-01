from dataclasses import dataclass
from subprocess import check_call, run, CalledProcessError, PIPE
from platform import python_version, python_version_tuple
from sys import exit
import os

class Install:

    @dataclass
    class CoreConfig:
        install_log_file: str
        unix_systemd_folder: str
        service_file_name: str
        service_cmd_executable: list
        service_cmd_daemon_reload: list
        defender_main_executable: str
        python_min_version: str
        python_current_version_tuple: tuple[str, str, str]
        python_current_version: str
        defender_install_folder: str
        venv_folder: str
        venv_cmd_installation: list
        venv_cmd_requirements: list
        venv_pip_executable: str
        venv_python_executable: str

    def __init__(self) -> None:

        self.set_configuration()

        if not self.check_python_version():
            # Tester si c'est la bonne version de python
            exit("Python Version Error")
        else:

            if self.skip_install:
                return None

            print(f'Configuration loaded : {self.config}')

            # Sinon tester les dependances python et les installer avec pip
            if self.do_install():

                self.install_dependencies()

                self.create_service_file()

                self.print_final_message()

        return None

    def set_configuration(self):

        self.skip_install = False
        defender_install_folder = os.getcwd()
        venv_folder = '.pyenv'
        unix_user_home_directory = os.path.expanduser("~")
        unix_systemd_folder = os.path.join(unix_user_home_directory, '.config', 'systemd', 'user')
        defender_main_executable = os.path.join(defender_install_folder, 'main.py')

        self.config = self.CoreConfig(
                install_log_file='install.log',
                unix_systemd_folder=unix_systemd_folder,
                service_file_name='defender.service',
                service_cmd_executable=['systemctl', '--user', 'start', 'defender'],
                service_cmd_daemon_reload=['systemctl', '--user', 'daemon-reload'],
                defender_main_executable=defender_main_executable,
                python_min_version='3.10',
                python_current_version_tuple=python_version_tuple(),
                python_current_version=python_version(),
                defender_install_folder=defender_install_folder,
                venv_folder=venv_folder,
                venv_cmd_installation=['python3', '-m', 'venv', venv_folder],
                venv_cmd_requirements=['sqlalchemy','psutil','requests','faker'],
                venv_pip_executable=f'{os.path.join(defender_install_folder, venv_folder, "bin")}{os.sep}pip',
                venv_python_executable=f'{os.path.join(defender_install_folder, venv_folder, "bin")}{os.sep}python'
            )

        # Exclude Windows OS
        if os.name == 'nt':
            #print('/!\\ Skip installation /!\\')
            self.skip_install = True
        else:
            if self.is_root():
                self.skip_install = True

    def is_root(self) -> bool:

        if os.geteuid() != 0:
            print('User without privileges ==> PASS')
            return False
        elif os.geteuid() == 0:
            print('/!\\ Do not use root to install Defender /!\\')
            exit("Do not use root to install Defender")
            return True

    def do_install(self) -> bool:

        full_service_file_path = os.path.join(self.config.unix_systemd_folder, self.config.service_file_name)

        if not os.path.exists(full_service_file_path):
            print(f'/!\\ Service file does not exist /!\\')
            return True

        # Check if virtual env exist
        if not os.path.exists(f'{os.path.join(self.config.defender_install_folder, self.config.venv_folder)}'):
            self.run_subprocess(self.config.venv_cmd_installation)
            print(f'/!\\ Virtual env does not exist run the install /!\\')
            return True

    def run_subprocess(self, command:list) -> None:

        print(f'> {command}')
        try:
            check_call(command)
            print("The command completed successfully.")
        except CalledProcessError as e:
            print(f"The command failed with the return code: {e.returncode}")
            print(f"Try to install dependencies ...")
            exit(5)

    def check_python_version(self) -> bool:
        """Test si la version de python est autorisée ou non

        Returns:
            bool: True si la version de python est autorisé sinon False
        """
        # Current system version
        sys_major, sys_minor, sys_patch = self.config.python_current_version_tuple

        # min python version required
        python_required_version = self.config.python_min_version.split('.')
        min_major, min_minor = tuple((python_required_version[0], python_required_version[1]))

        if int(sys_major) < int(min_major):
            print(f"## Your python version must be greather than or equal to {self.config.python_current_version} ##")
            return False

        elif (int(sys_major) <= int(min_major)) and (int(sys_minor) < int(min_minor)):
            print(f"## Your python version must be greather than or equal to {self.config.python_current_version} ##")
            return False

        print(f"> Version of python : {self.config.python_current_version} ==> OK")

        return True

    def check_package(self, package_name) -> bool:

        try:
            # Run a command in the virtual environment's Python to check if the package is installed
            run([self.config.venv_python_executable, '-c', f'import {package_name}'], check=True, stdout=PIPE, stderr=PIPE)
            return True
        except CalledProcessError as cpe:
            print(cpe)
            return False

    def install_dependencies(self) -> None:
        """### Verifie les dépendances si elles sont installées
        - Test si les modules sont installés
        - Met a jour pip
        - Install les modules manquants
        """
        do_install = False

        # Check if virtual env exist
        if not os.path.exists(f'{os.path.join(self.config.defender_install_folder, self.config.venv_folder)}'):
            self.run_subprocess(self.config.venv_cmd_installation)
            do_install = True

        for module in self.config.venv_cmd_requirements:
            if not self.check_package(module):
                do_install = True

        if not do_install:
            return None

        print("===> Vider le cache de pip")
        self.run_subprocess([self.config.venv_pip_executable, 'cache', 'purge'])
        
        print("===> Verifier si pip est a jour")
        self.run_subprocess([self.config.venv_python_executable, '-m', 'pip', 'install', '--upgrade', 'pip'])

        if not self.check_package('greenlet'):
            self.run_subprocess([self.config.venv_pip_executable, 'install', '--only-binary', ':all:', 'greenlet'])
            print('====> Module Greenlet installé')

        for module in self.config.venv_cmd_requirements:
            if not self.check_package(module):
                print("### Trying to install missing python packages ###")
                self.run_subprocess([self.config.venv_pip_executable, 'install', module])
                print(f"====> Module {module} installé")
            else:
                print(f"==> {module} already installed")

    def create_service_file(self) -> None:

        full_service_file_path = os.path.join(self.config.unix_systemd_folder, self.config.service_file_name)

        if os.path.exists(full_service_file_path):
            print(f'/!\\ Service file already exist /!\\')
            self.run_subprocess(self.config.service_cmd_executable)
            return None

        contain = f'''[Unit]
Description=Defender IRC Service

[Service]
ExecStart={self.config.venv_python_executable} {self.config.defender_main_executable}
WorkingDirectory={self.config.defender_install_folder}
SyslogIdentifier=Defender
Restart=on-failure

[Install]
WantedBy=default.target
'''
        # Check if user systemd is available (.config/systemd/user/)
        if not os.path.exists(self.config.unix_systemd_folder):
            self.run_subprocess(['mkdir', '-p', self.config.unix_systemd_folder])

            with open(full_service_file_path, 'w+') as servicefile:
                servicefile.write(contain)
                servicefile.close()
                print(f'Service file generated with current configuration')
                print(f'Running Defender IRC Service ...')
                self.run_subprocess(self.config.service_cmd_daemon_reload)
                self.run_subprocess(self.config.service_cmd_executable)

        else:
            with open(full_service_file_path, 'w+') as servicefile:
                servicefile.write(contain)
                servicefile.close()
                print(f'Service file generated with current configuration')
                print(f'Running Defender IRC Service ...')
                self.run_subprocess(self.config.service_cmd_daemon_reload)
                self.run_subprocess(self.config.service_cmd_executable)

    def print_final_message(self) -> None:

        print(f"#"*24)
        print("Installation complete ...")
        print("If the configuration is correct, then you must see your service connected to your irc server")
        print(f"If any issue, you can see the log file for debug {self.config.defender_install_folder}{os.sep}logs{os.sep}defender.log")
        print(f"#"*24)
        exit(1)
