from subprocess import check_call, run, CalledProcessError, PIPE
from platform import python_version, python_version_tuple, system
from sys import exit
import os, logging, shutil

try:
    import pwd
except ModuleNotFoundError as err:
    print(err)

class Install:

    def __init__(self) -> None:

        # Python required version
        self.python_min_version                 = '3.10'
        self.log_file                           = 'install.log'
        self.ServiceName                        = 'Defender'
        self.venv_name                          = '.pyenv'
        self.venv_dependencies: list[str]       = ['sqlalchemy','psutil','requests']
        self.install_folder                     = os.getcwd()
        self.osname                             = os.name
        self.system_name                        = system()
        self.cmd_linux_requirements: list[str]  = ['apt', 'install', '-y', 'python3', 'python3-pip', 'python3-venv']
        self.venv_pip_full_path                 = os.path.join(self.venv_name, f'bin{os.sep}pip')
        self.venv_python_full_path              = os.path.join(self.venv_name, f'bin{os.sep}python')
        self.systemd_folder                     = '/etc/systemd/system/'

        # Init log system
        self.init_log_system()

        # Exclude Windows OS
        if self.osname == 'nt':
            print('/!\\ Windows OS is not supported by this automatic installation /!\\')
            self.Logs.critical('/!\\ Windows OS is not supported by this automatic install /!\\')
            print(self.system_name)
            exit(5)

        if not self.is_root():
            exit(5)

        # Get the current user
        self.system_username: str = input(f'What is the user ro run defender with ? [{os.getlogin()}] : ')
        if str(self.system_username).strip() == '':
            self.system_username = os.getlogin()

        self.get_user_information(self.system_username)

        self.Logs.debug(f'The user selected is: {self.system_username}')
        self.Logs.debug(f'Operating system: {self.osname}')

        # Install linux dependencies
        self.install_linux_dependencies()

        # Check python version
        self.check_python_version()

        # Create systemd service file
        self.create_service_file()

        # Check if Env Exist | install environment | Install python dependencies
        self.check_venv()

        # Create and start service
        if self.osname != 'nt':
            self.run_subprocess(['systemctl','daemon-reload'])
            self.run_subprocess(['systemctl','start', self.ServiceName])
            self.run_subprocess(['systemctl','status', self.ServiceName])

        # Clean the Installation
        self.clean_installation()

        return None

    def is_installed(self) -> bool:

        is_installed = False

        # Check logs folder
        if os.path.exists('logs'):
            is_installed = True

        # Check db folder
        if os.path.exists('db'):
            is_installed = True

        return is_installed

    def is_root(self) -> bool:

        if os.geteuid() != 0:
            print('/!\\ user must run install.py as root /!\\')
            self.Logs.critical('/!\\ user must run install.py as root /!\\')
            return False
        elif os.geteuid() == 0:
            return True

    def get_user_information(self, system_user: str) -> None:

        try:
            username: tuple = pwd.getpwnam(system_user)
            self.system_uid = username.pw_uid
            self.system_gid = username.pw_gid
            return None

        except KeyError as ke:
            self.Logs.critical(f"This user [{system_user}] doesn't exist: {ke}")
            print(f"This user [{system_user}] doesn't exist: {ke}")
            exit(5)

    def init_log_system(self) -> None:

        # Init logs object
        self.Logs = logging
        self.Logs.basicConfig(level=logging.DEBUG,
                              filename=self.log_file,
                              encoding='UTF-8',
                              format='%(asctime)s - %(levelname)s - %(filename)s - %(lineno)d - %(funcName)s - %(message)s')

        self.Logs.debug('#################### STARTING INSTALLATION ####################')

        return None

    def clean_installation(self) -> None:

        # Chown the Python Env to non user privilege
        self.run_subprocess(['chown','-R', f'{self.system_username}:{self.system_username}', 
                        f'{os.path.join(self.install_folder, self.venv_name)}'
                        ]
                    )

        # Chown the installation log file
        self.run_subprocess(['chown','-R', f'{self.system_username}:{self.system_username}', 
                        f'{os.path.join(self.install_folder, self.log_file)}'
                        ]
                    )
        return None

    def run_subprocess(self, command:list) -> None:

        try:
            run_command = check_call(command)
            self.Logs.debug(f'{command} - {run_command}')
            print(f'{command} - {run_command}')

        except CalledProcessError as e:
            print(f"Command failed :{e.returncode}")
            self.Logs.critical(f"Command failed :{e.returncode}")
            exit(5)

    def check_python_version(self) -> bool:
        """Test si la version de python est autorisée ou non

        Returns:
            bool: True si la version de python est autorisé sinon False
        """

        self.Logs.debug(f'The current python version is: {python_version()}')

        # Current system version
        sys_major, sys_minor, sys_patch = python_version_tuple()

        # min python version required
        python_required_version = self.PYTHON_MIN_VERSION.split('.')
        min_major, min_minor = tuple((python_required_version[0], python_required_version[1]))

        if int(sys_major) < int(min_major):
            print(f"## Your python version must be greather than or equal to {self.PYTHON_MIN_VERSION} ##")
            self.Logs.critical(f'Your python version must be greather than or equal to {self.python_min_version}')
            return False

        elif (int(sys_major) <= int(min_major)) and (int(sys_minor) < int(min_minor)):
            print(f"## Your python version must be greather than or equal to {self.PYTHON_MIN_VERSION} ##")
            self.Logs.critical(f'Your python version must be greather than or equal to {self.python_min_version}')
            return False

        print(f"===> Version of python : {python_version()} ==> OK")
        self.Logs.debug(f'Version of python : {python_version()} ==> OK')

        return True

    def check_packages(self, package_name) -> bool:

        try:
            # Run a command in the virtual environment's Python to check if the package is installed
            run([self.venv_python_full_path, '-c', f'import {package_name}'], check=True, stdout=PIPE, stderr=PIPE)
            return True
        except CalledProcessError:
            return False

    def check_venv(self) -> bool:

        if os.path.exists(self.venv_name):

            # Installer les dependances
            self.install_dependencies()
            return True
        else:
            self.run_subprocess(['python3', '-m', 'venv', self.venv_name])
            self.Logs.debug(f'Python Virtual env installed {self.venv_name}')
            print(f'Python Virtual env installed {self.venv_name}')

            self.install_dependencies()
            return False

    def create_service_file(self) -> None:

        if self.systemd_folder is None:
            # If Windows, do not install systemd
            return None

        if os.path.exists(f'{self.systemd_folder}{os.sep}{self.ServiceName}.service'):
            print(f'/!\\ Service already created in the system /!\\')
            self.Logs.warning('/!\\ Service already created in the system /!\\')
            print(f'The service file will be regenerated')
            self.Logs.warning('The service file will be regenerated')
            

        contain = f'''[Unit]
Description={self.ServiceName} IRC Service

[Service]
User={self.system_username}
ExecStart={os.path.join(self.install_folder, self.venv_python_full_path)} {os.path.join(self.install_folder, 'main.py')}
WorkingDirectory={self.install_folder}
SyslogIdentifier={self.ServiceName}
Restart=on-failure

[Install]
WantedBy=multi-user.target
'''

        with open(f'{self.ServiceName}.service.generated', 'w+') as servicefile:
            servicefile.write(contain)
            servicefile.close()
            print('Service file generated with current configuration')
            self.Logs.debug('Service file generated with current configuration')

            source = f'{self.install_folder}{os.sep}{self.ServiceName}.service.generated'
            self.run_subprocess(['chown','-R', f'{self.system_username}:{self.system_username}', source])
            destination = f'{self.systemd_folder}'
            shutil.copy(source, destination)
            os.rename(f'{self.systemd_folder}{os.sep}{self.ServiceName}.service.generated', f'{self.systemd_folder}{os.sep}{self.ServiceName}.service')
            print(f'Service file moved to systemd folder {self.systemd_folder}')
            self.Logs.debug(f'Service file moved to systemd folder {self.systemd_folder}')

    def install_linux_dependencies(self) -> None:

        self.run_subprocess(self.cmd_linux_requirements)

        return None

    def install_dependencies(self) -> None:

        try:
            self.run_subprocess([self.venv_pip_full_path, 'cache', 'purge'])
            self.run_subprocess([self.venv_python_full_path, '-m', 'pip', 'install', '--upgrade', 'pip'])

            if self.check_packages('greenlet') is None:
                self.run_subprocess(
                    [self.venv_pip_full_path, 'install', '--only-binary', ':all:', 'greenlet']
                    )

            for module in self.venv_dependencies:
                if not self.check_packages(module):
                    ### Trying to install missing python packages ###
                    self.run_subprocess([self.venv_pip_full_path, 'install', module])
                else:
                    self.Logs.debug(f'{module} already installed')
                    print(f"==> {module} already installed")

        except CalledProcessError as cpe:
            self.Logs.critical(f'{cpe}')

Install()