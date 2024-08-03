import time, threading, os, random, socket, hashlib, ipaddress, logging, requests, json, sys
from datetime import datetime
from sqlalchemy import create_engine, Engine, Connection, CursorResult
from sqlalchemy.sql import text
from core.configuration import Config

class Base:

    CORE_DB_PATH = 'core' + os.sep + 'db' + os.sep              # Le dossier bases de données core
    MODS_DB_PATH = 'mods' + os.sep + 'db' + os.sep              # Le dossier bases de données des modules
    PYTHON_MIN_VERSION = '3.10'                                 # Version min de python
    DB_SCHEMA:list[str] = {
        'admins': 'sys_admins',
        'commandes': 'sys_commandes',
        'logs': 'sys_logs',
        'modules': 'sys_modules'
    }

    DEFENDER_VERSION = ''                                   # MAJOR.MINOR.BATCH
    LATEST_DEFENDER_VERSION = ''                            # Latest Version of Defender in git
    DEFENDER_DB_PATH = 'db' + os.sep                        # Séparateur en fonction de l'OS
    DEFENDER_DB_NAME = 'defender'                           # Le nom de la base de données principale

    def __init__(self, Config: Config) -> None:

        self.Config = Config                                    # Assigner l'objet de configuration
        self.init_log_system()                                  # Demarrer le systeme de log
        self.check_for_new_version()                            # Verifier si une nouvelle version est disponible

        self.running_timers:list[threading.Timer] = []          # Liste des timers en cours
        self.running_threads:list[threading.Thread] = []        # Liste des threads en cours
        self.running_sockets: list[socket.socket] = []          # Les sockets ouvert
        self.periodic_func:dict[object] = {}                    # Liste des fonctions en attentes

        self.lock = threading.RLock()                           # Création du lock

        self.engine, self.cursor = self.db_init()               # Initialisation de la connexion a la base de données
        self.__create_db()                                      # Initialisation de la base de données

        self.db_create_first_admin()                            # Créer un nouvel admin si la base de données est vide

    def __set_current_defender_version(self) -> None:
        """This will put the current version of Defender
        located in version.json
        """

        version_filename = f'.{os.sep}version.json'
        with open(version_filename, 'r') as version_data:
            current_version:dict[str, str] = json.load(version_data)

        self.DEFENDER_VERSION = current_version["version"]

        return None

    def __get_latest_defender_version(self) -> None:
        try:
            token = ''
            json_url = f'https://raw.githubusercontent.com/adator85/IRC_DEFENDER_MODULES/main/version.json'
            headers = {
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3.raw'  # Indique à GitHub que nous voulons le contenu brut du fichier
            }

            if token == '':
                response = requests.get(json_url)
            else:
                response = requests.get(json_url, headers=headers)

            response.raise_for_status()  # Vérifie si la requête a réussi
            json_response:dict = response.json()
            self.LATEST_DEFENDER_VERSION = json_response["version"]

            return None
        except requests.HTTPError as err:
            self.logs.error(f'Github not available to fetch latest version: {err}')
        except:
            self.logs.warning(f'Github not available to fetch latest version')

    def check_for_new_version(self) -> bool:
        try:
            # Assigner la version actuelle de Defender
            self.__set_current_defender_version() 
            # Récuperer la dernier version disponible dans github
            self.__get_latest_defender_version()

            isNewVersion = False
            latest_version = self.LATEST_DEFENDER_VERSION
            current_version = self.DEFENDER_VERSION

            curr_major , curr_minor, curr_patch = current_version.split('.')
            last_major, last_minor, last_patch = latest_version.split('.')

            if int(last_major) > int(curr_major):
                self.logs.info(f'New version available: {current_version} >>> {latest_version}')
                isNewVersion = True
            elif int(last_major) == int(curr_major) and int(last_minor) > int(curr_minor):
                self.logs.info(f'New version available: {current_version} >>> {latest_version}')
                isNewVersion = True
            elif int(last_major) == int(curr_major) and int(last_minor) == int(curr_minor) and int(last_patch) > int(curr_patch):
                self.logs.info(f'New version available: {current_version} >>> {latest_version}')
                isNewVersion = True
            else:
                isNewVersion = False

            return isNewVersion
        except ValueError as ve:
            self.logs.error(f'Impossible to convert in version number : {ve}')

    def get_unixtime(self) -> int:
        """
        Cette fonction retourne un UNIXTIME de type 12365456
        Return: Current time in seconds since the Epoch (int)
        """
        unixtime = int( time.time() )
        return unixtime

    def get_datetime(self) -> str:
        """
        Retourne une date au format string (24-12-2023 20:50:59)
        """
        currentdate = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        return currentdate

    def create_log(self, log_message: str) -> None:
        """Enregiste les logs

        Args:
            string (str): Le message a enregistrer

        Returns:
            None: Aucun retour
        """
        sql_insert = f"INSERT INTO {self.DB_SCHEMA['logs']} (datetime, server_msg) VALUES (:datetime, :server_msg)"
        mes_donnees = {'datetime': str(self.get_datetime()),'server_msg': f'{log_message}'}
        self.db_execute_query(sql_insert, mes_donnees)

        return None

    def init_log_system(self) -> None:
        # Create folder if not available
        logs_directory = f'logs{os.sep}'
        if not os.path.exists(f'{logs_directory}'):
            os.makedirs(logs_directory)

        # Init logs object
        self.logs = logging
        self.logs.basicConfig(level=self.Config.DEBUG_LEVEL,
                              filename='logs/defender.log',
                              encoding='UTF-8',
                              format='%(asctime)s - %(levelname)s - %(filename)s - %(lineno)d - %(funcName)s - %(message)s')

        self.logs.info('#################### STARTING INTERCEPTOR HQ ####################')

        return None

    def log_cmd(self, user_cmd:str, cmd:str) -> None:
        """Enregistre les commandes envoyées par les utilisateurs

        Args:
            cmd (str): la commande a enregistrer
        """
        cmd_list = cmd.split()
        if len(cmd_list) == 3:
            if cmd_list[0].replace('.', '') == 'auth':
                cmd_list[1] = '*******'
                cmd_list[2] = '*******'
                cmd = ' '.join(cmd_list)

        insert_cmd_query = f"INSERT INTO {self.DB_SCHEMA['commandes']} (datetime, user, commande) VALUES (:datetime, :user, :commande)"
        mes_donnees = {'datetime': self.get_datetime(), 'user': user_cmd, 'commande': cmd}
        self.db_execute_query(insert_cmd_query, mes_donnees)

        return False

    def db_isModuleExist(self, module_name:str) -> bool:
        """Teste si un module existe déja dans la base de données

        Args:
            module_name (str): le non du module a chercher dans la base de données

        Returns:
            bool: True si le module existe déja dans la base de données sinon False
        """
        query = f"SELECT id FROM {self.DB_SCHEMA['modules']} WHERE module = :module"
        mes_donnes = {'module': module_name}
        results = self.db_execute_query(query, mes_donnes)

        if results.fetchall():
            return True
        else:
            return False

    def db_record_module(self, user_cmd:str, module_name:str) -> None:
        """Enregistre les modules dans la base de données

        Args:
            cmd (str): le module a enregistrer
        """

        if not self.db_isModuleExist(module_name):
            self.logs.debug(f"Le module {module_name} n'existe pas alors ont le créer")
            insert_cmd_query = f"INSERT INTO {self.DB_SCHEMA['modules']} (datetime, user, module) VALUES (:datetime, :user, :module)"
            mes_donnees = {'datetime': self.get_datetime(), 'user': user_cmd, 'module': module_name}
            self.db_execute_query(insert_cmd_query, mes_donnees)
            # self.db_close_session(self.session)
        else:
            self.logs.debug(f"Le module {module_name} existe déja dans la base de données")

        return False

    def db_delete_module(self, module_name:str) -> None:
        """Supprime les modules de la base de données

        Args:
            cmd (str): le module a enregistrer
        """
        insert_cmd_query = f"DELETE FROM {self.DB_SCHEMA['modules']} WHERE module = :module"
        mes_donnees = {'module': module_name}
        self.db_execute_query(insert_cmd_query, mes_donnees)

        return False

    def db_create_first_admin(self) -> None:

        user = self.db_execute_query(f"SELECT id FROM {self.DB_SCHEMA['admins']}")
        if not user.fetchall():
            admin = self.Config.OWNER
            password = self.crypt_password(self.Config.PASSWORD)

            mes_donnees = {'createdOn': self.get_datetime(), 'user': admin, 'password': password, 'hostname': '*', 'vhost': '*', 'level': 5}
            self.db_execute_query(f"""
                                  INSERT INTO {self.DB_SCHEMA['admins']} 
                                  (createdOn, user, password, hostname, vhost, level) 
                                  VALUES 
                                  (:createdOn, :user, :password, :hostname, :vhost, :level)"""
                                  , mes_donnees)

        return None

    def create_timer(self, time_to_wait: float, func: object, func_args: tuple = ()) -> None:

        try:
            t = threading.Timer(interval=time_to_wait, function=func, args=func_args)
            t.setName(func.__name__)
            t.start()

            self.running_timers.append(t)

            self.logs.debug(f"Timer ID : {str(t.ident)} | Running Threads : {len(threading.enumerate())}")

        except AssertionError as ae:
            self.logs.error(f'Assertion Error -> {ae}')

    def create_thread(self, func:object, func_args: tuple = (), run_once:bool = False) -> None:
        try:
            func_name = func.__name__

            if run_once:
                for thread in self.running_threads:
                    if thread.getName() == func_name:
                        return None

            # if func_name in self.running_threads:
            #     print(f"HeartBeat is running")
            #     return None

            th = threading.Thread(target=func, args=func_args, name=str(func_name), daemon=True)
            th.start()

            self.running_threads.append(th)
            self.logs.debug(f"Thread ID : {str(th.ident)} | Thread name : {th.getName()} | Running Threads : {len(threading.enumerate())}")

        except AssertionError as ae:
            self.logs.error(f'{ae}')

    def garbage_collector_timer(self) -> None:
        """Methode qui supprime les timers qui ont finis leurs job
        """
        try:

            for timer in self.running_timers:
                if not timer.is_alive():
                    timer.cancel()
                    self.running_timers.remove(timer)
                    self.logs.info(f"Timer {str(timer)} removed")
                else:
                    self.logs.debug(f"===> Timer {str(timer)} Still running ...")

        except AssertionError as ae:
            self.logs.error(f'Assertion Error -> {ae}')

    def garbage_collector_thread(self) -> None:
        """Methode qui supprime les threads qui ont finis leurs job
        """
        try:
            for thread in self.running_threads:
                if thread.getName() != 'heartbeat':
                    if not thread.is_alive():
                        self.running_threads.remove(thread)
                        self.logs.debug(f"Thread {str(thread.getName())} {str(thread.native_id)} removed")

            # print(threading.enumerate())
        except AssertionError as ae:
            self.logs.error(f'Assertion Error -> {ae}')

    def garbage_collector_sockets(self) -> None:

        for soc in self.running_sockets:
            while soc.fileno() != -1:
                self.logs.debug(soc.fileno())
                soc.close()

            soc.close()
            self.running_sockets.remove(soc)
            self.logs.debug(f"Socket ==> closed {str(soc.fileno())}")

    def shutdown(self) -> None:
        """Methode qui va préparer l'arrêt complêt du service
        """
        # Nettoyage des timers
        self.logs.debug(f"=======> Checking for Timers to stop")
        for timer in self.running_timers:
            while timer.is_alive():
                self.logs.debug(f"> waiting for {timer.getName()} to close")
                timer.cancel()
                time.sleep(0.2)
            self.running_timers.remove(timer)
            self.logs.debug(f"> Cancelling {timer.getName()} {timer.native_id}")

        self.logs.debug(f"=======> Checking for Threads to stop")
        for thread in self.running_threads:
            if thread.getName() == 'heartbeat' and thread.is_alive():
                self.execute_periodic_action()
                self.logs.debug(f"> Running the last periodic action")
            self.running_threads.remove(thread)
            self.logs.debug(f"> Cancelling {thread.getName()} {thread.native_id}")

        self.logs.debug(f"=======> Checking for Sockets to stop")
        for soc in self.running_sockets:
            soc.close()
            while soc.fileno() != -1:
                soc.close()

            self.running_sockets.remove(soc)
            self.logs.debug(f"> Socket ==> closed {str(soc.fileno())}")

        return None

    def db_init(self) -> tuple[Engine, Connection]:

        db_directory = self.DEFENDER_DB_PATH
        full_path_db = self.DEFENDER_DB_PATH + self.DEFENDER_DB_NAME

        if not os.path.exists(db_directory):
            os.makedirs(db_directory)

        engine = create_engine(f'sqlite:///{full_path_db}.db', echo=False)
        cursor = engine.connect()
        self.logs.info("database connexion has been initiated")
        return engine, cursor

    def __create_db(self) -> None:

        table_logs = f'''CREATE TABLE IF NOT EXISTS {self.DB_SCHEMA['logs']} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            server_msg TEXT
            ) 
        '''

        table_cmds = f'''CREATE TABLE IF NOT EXISTS {self.DB_SCHEMA['commandes']} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            user TEXT,
            commande TEXT
            )
        '''

        table_modules = f'''CREATE TABLE IF NOT EXISTS {self.DB_SCHEMA['modules']} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            user TEXT,
            module TEXT
            )
        '''

        table_admins = f'''CREATE TABLE IF NOT EXISTS {self.DB_SCHEMA['admins']} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            createdOn TEXT,
            user TEXT,
            hostname TEXT,
            vhost TEXT,
            password TEXT,
            level INTEGER
            )
        '''

        self.db_execute_query(table_logs)
        self.db_execute_query(table_cmds)
        self.db_execute_query(table_modules)
        self.db_execute_query(table_admins)

        return None

    def db_execute_query(self, query:str, params:dict = {}) -> CursorResult:

        with self.lock:
            insert_query = text(query)
            if not params:
                response = self.cursor.execute(insert_query)
            else:
                response = self.cursor.execute(insert_query, params)

            self.cursor.commit()

            return response

    def db_close(self) -> None:

        try:
            self.cursor.close()
        except AttributeError as ae:
            self.logs.error(f"Attribute Error : {ae}")

    def crypt_password(self, password:str) -> str:
        """Retourne un mot de passe chiffré en MD5

        Args:
            password (str): Le password en clair

        Returns:
            str: Le password en MD5
        """
        md5_password = hashlib.md5(password.encode()).hexdigest()

        return md5_password

    def int_if_possible(self, value):
        """Convertit la valeur reçue en entier, si possible.
        Sinon elle retourne la valeur initiale.

        Args:
            value (any): la valeur à convertir

        Returns:
            any: Retour un entier, si possible. Sinon la valeur initiale.
        """
        try:
            response = int(value)
            return response
        except ValueError:
            return value
        except TypeError:
            return value

    def is_valid_ip(self, ip_to_control:str) -> bool:

        try:
            if ip_to_control in self.Config.WHITELISTED_IP:
                return False

            ipaddress.ip_address(ip_to_control)
            return True
        except ValueError:
            return False

    def get_random(self, lenght:int) -> str:
        """
        Retourn une chaîne aléatoire en fonction de la longueur spécifiée.
        """
        caracteres = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        randomize = ''.join(random.choice(caracteres) for _ in range(lenght))

        return randomize

    def execute_periodic_action(self) -> None:

        if not self.periodic_func:
            # Run Garbage Collector Timer
            self.garbage_collector_timer()
            self.garbage_collector_thread()
            # self.garbage_collector_sockets()
            return None

        for key, value in self.periodic_func.items():
            obj = value['object']
            method_name = value['method_name']
            param = value['param']
            f = getattr(obj, method_name, None)
            f(*param)

        # Vider le dictionnaire de fonction
        self.periodic_func.clear()
