from importlib.util import find_spec
from subprocess import check_call, run, CalledProcessError
from platform import python_version
from sys import exit
import os

class Install:

    def __init__(self) -> None:
        self.PYTHON_MIN_VERSION = '3.10'

        self.venv_folder_name = '.pyenv'
        self.cmd_venv_command = ['python3', '-m', 'venv', self.venv_folder_name]
        self.module_to_install = ['sqlalchemy','psutil','requests']

        if not self.checkPythonVersion():
            # Tester si c'est la bonne version de python
            exit("Python Version Error")
        else:
            # Sinon tester les dependances python et les installer avec pip
            self.checkDependencies()

        return None

    def checkPythonVersion(self) -> bool:
        """Test si la version de python est autorisée ou non

        Returns:
            bool: True si la version de python est autorisé sinon False
        """
        python_required_version = self.PYTHON_MIN_VERSION.split('.')
        python_current_version = python_version().split('.')

        if int(python_current_version[0]) < int(python_required_version[0]):
            print(f"## Your python version must be greather than or equal to {self.PYTHON_MIN_VERSION} ##")
            return False
        elif int(python_current_version[1]) < int(python_required_version[1]):
            print(f"### Your python version must be greather than or equal to {self.PYTHON_MIN_VERSION} ###")
            return False

        print(f"===> Version of python : {python_version()} ==> OK")

        return True

    def run_subprocess(self, command:list) -> None:

        print(command)
        try:
            check_call(command)
            print("La commande s'est terminée avec succès.")
        except CalledProcessError as e:
            print(f"La commande a échoué avec le code de retour :{e.returncode}")
            print(f"Try to install dependencies ...")
            exit(5)

    def checkDependencies(self) -> None:
        """### Verifie les dépendances si elles sont installées
        - Test si les modules sont installés
        - Met a jour pip
        - Install les modules manquants
        """
        do_install = False

        # Check if virtual env exist
        if not os.path.exists(f'{self.venv_folder_name}'):
            self.run_subprocess(self.cmd_venv_command)
            do_install = True

        for module in self.module_to_install:
            if find_spec(module) is None:
                do_install = True

        if not do_install:
            return None

        print("===> Vider le cache de pip")
        check_call(['pip','cache','purge'])
        
        print("===> Verifier si pip est a jour")
        check_call(['python', '-m', 'pip', 'install', '--upgrade', 'pip'])

        if find_spec('greenlet') is None:
            check_call(['pip','install', '--only-binary', ':all:', 'greenlet'])
            print('====> Module Greenlet installé')

        for module in self.module_to_install:
            if find_spec(module) is None:
                print("### Trying to install missing python packages ###")
                check_call(['pip','install', module])
                print(f"====> Module {module} installé")
            else:
                print(f"==> {module} already installed")

        print(f"#"*12)
        print("Installation complete ...")
        print("You must change environment using the command below")
        print(f"source {self.venv_folder_name}{os.sep}bin{os.sep}activate")
        print(f"#"*12)
        exit(1)