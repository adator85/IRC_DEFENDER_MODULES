import time, threading, os, random, socket, hashlib
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

    def __init__(self, Config: Config) -> None:

        self.Config = Config                                    # Assigner l'objet de configuration

        self.running_timers:list[threading.Timer] = []          # Liste des timers en cours
        self.running_threads:list[threading.Thread] = []        # Liste des threads en cours
        self.running_sockets: list[socket.socket] = []          # Les sockets ouvert
        self.periodic_func:dict[object] = {}                    # Liste des fonctions en attentes

        self.lock = threading.RLock()                           # Création du lock

        self.engine, self.cursor = self.db_init()               # Initialisation de la connexion a la base de données
        self.__create_db()                                      # Initialisation de la base de données

        self.db_create_first_admin()                            # Créer un nouvel admin si la base de données est vide

    def get_unixtime(self)->int:
        """
        Cette fonction retourne un UNIXTIME de type 12365456
        Return: Current time in seconds since the Epoch (int)
        """
        unixtime = int( time.time() )
        return unixtime

    def get_datetime(self)->str:
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

    def log_cmd(self, user_cmd:str, cmd:str) -> None:
        """Enregistre les commandes envoyées par les utilisateurs

        Args:
            cmd (str): la commande a enregistrer
        """
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
            self.__debug(f"Le module {module_name} n'existe pas alors ont le créer")
            insert_cmd_query = f"INSERT INTO {self.DB_SCHEMA['modules']} (datetime, user, module) VALUES (:datetime, :user, :module)"
            mes_donnees = {'datetime': self.get_datetime(), 'user': user_cmd, 'module': module_name}
            self.db_execute_query(insert_cmd_query, mes_donnees)
            # self.db_close_session(self.session)
        else:
            self.__debug(f"Le module {module_name} existe déja dans la base de données")

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

        pass

    def create_timer(self, time_to_wait: float, func: object, func_args: tuple = ()) -> None:

        try:
            t = threading.Timer(interval=time_to_wait, function=func, args=func_args)
            t.setName(func.__name__)
            t.start()

            self.running_timers.append(t)

            self.__debug(f"Timer ID : {str(t.ident)} | Running Threads : {len(threading.enumerate())}")

        except AssertionError as ae:
            self.__debug(f'Assertion Error -> {ae}')

    def create_thread(self, func:object, func_args: tuple = ()) -> None:
        try:
            func_name = func.__name__
            # if func_name in self.running_threads:
            #     print(f"HeartBeat is running")
            #     return None

            th = threading.Thread(target=func, args=func_args, name=str(func_name), daemon=True)
            th.start()

            self.running_threads.append(th)
            self.__debug(f"Thread ID : {str(th.ident)} | Thread name : {th.getName()} | Running Threads : {len(threading.enumerate())}")

        except AssertionError as ae:
            self.__debug(f'Assertion Error -> {ae}')

    def garbage_collector_timer(self) -> None:
        """Methode qui supprime les timers qui ont finis leurs job
        """
        try:
            self.__debug(f"=======> Checking for Timers to stop")
            # print(f"{self.running_timers}")
            for timer in self.running_timers:
                if not timer.is_alive():
                    timer.cancel()
                    self.running_timers.remove(timer)
                    self.__debug(f"Timer {str(timer)} removed")
                else:
                    self.__debug(f"===> Timer {str(timer)} Still running ...")

        except AssertionError as ae:
            print(f'Assertion Error -> {ae}')

    def garbage_collector_thread(self) -> None:
        """Methode qui supprime les threads qui ont finis leurs job
        """
        try:
            self.__debug(f"=======> Checking for Threads to stop")
            for thread in self.running_threads:
                if thread.getName() != 'heartbeat':
                    if not thread.is_alive():
                        self.running_threads.remove(thread)
                        self.__debug(f"Thread {str(thread.getName())} {str(thread.native_id)} removed")

            # print(threading.enumerate())
        except AssertionError as ae:
            self.__debug(f'Assertion Error -> {ae}')

    def garbage_collector_sockets(self) -> None:

        self.__debug(f"=======> Checking for Sockets to stop")
        for soc in self.running_sockets:
            while soc.fileno() != -1:
                self.__debug(soc.fileno())
                soc.close()

            soc.close()
            self.running_sockets.remove(soc)
            self.__debug(f"Socket ==> closed {str(soc.fileno())}")

    def shutdown(self) -> None:
        """Methode qui va préparer l'arrêt complêt du service
        """
        # Nettoyage des timers
        print(f"=======> Checking for Timers to stop")
        for timer in self.running_timers:
            while timer.is_alive():
                print(f"> waiting for {timer.getName()} to close")
                timer.cancel()
                time.sleep(0.2)
            self.running_timers.remove(timer)
            print(f"> Cancelling {timer.getName()} {timer.native_id}")

        print(f"=======> Checking for Threads to stop")
        for thread in self.running_threads:
            if thread.getName() == 'heartbeat' and thread.is_alive():
                self.execute_periodic_action()
                print(f"> Running the last periodic action")
            self.running_threads.remove(thread)
            print(f"> Cancelling {thread.getName()} {thread.native_id}")

        print(f"=======> Checking for Sockets to stop")
        for soc in self.running_sockets:
            soc.close()
            while soc.fileno() != -1:
                soc.close()

            self.running_sockets.remove(soc)
            print(f"> Socket ==> closed {str(soc.fileno())}")

        pass

    def db_init(self) -> tuple[Engine, Connection]:

        db_directory = self.Config.DEFENDER_DB_PATH
        full_path_db = self.Config.DEFENDER_DB_PATH + self.Config.DEFENDER_DB_NAME

        if not os.path.exists(db_directory):
            os.makedirs(db_directory)

        engine = create_engine(f'sqlite:///{full_path_db}.db', echo=False)
        cursor = engine.connect()

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
            self.__debug(f"Attribute Error : {ae}")

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
            self.garbage_collector_sockets()
            return None

        for key, value in self.periodic_func.items():
            obj = value['object']
            method_name = value['method_name']
            param = value['param']
            f = getattr(obj, method_name, None)
            f(*param)

        # Vider le dictionnaire de fonction
        self.periodic_func.clear()

    def __debug(self, debug_msg:str) -> None:

        if self.Config.DEBUG == 1:
            print(f"[{self.get_datetime()}] - {debug_msg}")

        return None