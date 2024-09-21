from dataclasses import dataclass, fields, field
from datetime import datetime
from typing import Union
import re, socket, psutil, requests, json, time
from sys import exit
from core.irc import Irc
from core.Model import User

#   Le module crée devra réspecter quelques conditions
#       1. Le nom de la classe devra toujours s'appeler comme le module. Exemple => nom de class Defender | nom du module mod_defender
#       2. la methode __init__ devra toujours avoir les parametres suivant (self, irc:object)
#           1 . Créer la variable Irc dans le module
#           2 . Récuperer la configuration dans une variable
#           3 . Définir et enregistrer les nouvelles commandes
#           4 . Créer vos tables, en utilisant toujours le nom des votre classe en minuscule ==> defender_votre-table
#       3. Methode suivantes:
#           cmd(self, data:list)
#           _hcmds(self, user:str, cmd: list)
#           unload(self)

class Defender():

    @dataclass
    class ModConfModel:
        reputation: int
        reputation_timer: int
        reputation_seuil: int
        reputation_score_after_release: int
        reputation_ban_all_chan: int
        reputation_sg: int
        local_scan: int
        psutil_scan: int
        abuseipdb_scan: int
        freeipapi_scan: int
        cloudfilt_scan: int
        flood: int
        flood_message: int
        flood_time: int
        flood_timer: int

    @dataclass
    class ReputationModel:
        uid: str
        nickname: str
        username: str
        hostname: str
        realname: str
        umodes: str
        vhost: str
        ip: str
        score: int
        isWebirc: bool
        isWebsocket: bool
        secret_code: str
        connected_datetime: str
        updated_datetime: str

    UID_REPUTATION_DB: list[ReputationModel] = []

    def __init__(self, ircInstance:Irc) -> None:

        # Module name (Mandatory)
        self.module_name = 'mod_' + str(self.__class__.__name__).lower()

        # Add Irc Object to the module (Mandatory)
        self.Irc = ircInstance

        # Add Global Configuration to the module (Mandatory)
        self.Config = ircInstance.Config

        # Add Base object to the module (Mandatory)
        self.Base = ircInstance.Base

        # Add logs object to the module (Mandatory)
        self.Logs = ircInstance.Base.logs

        # Add User object to the module (Mandatory)
        self.User = ircInstance.User

        # Add Channel object to the module (Mandatory)
        self.Channel = ircInstance.Channel

        # Create module commands (Mandatory)
        self.commands_level = {
            0: ['code'],
            1: ['info'],
            2: ['owner', 'deowner', 'op', 'deop', 'halfop', 'dehalfop', 'voice', 'devoice', 'ban', 'unban','kick', 'kickban'],
            3: ['reputation','proxy_scan', 'flood', 'status', 'timer','show_reputation', 'sentinel']
        }

        # Init the module (Mandatory)
        self.__init_module()

        # Log the module
        self.Logs.debug(f'Module {self.module_name} loaded ...')

    def __init_module(self) -> None:

        # Insert module commands into the core one (Mandatory)
        self.__set_commands(self.commands_level)

        # Create you own tables if needed (Mandatory)
        self.__create_tables()

        # Load module configuration (Mandatory)
        self.__load_module_configuration()
        # End of mandatory methods you can start your customization #

        # # Rejoindre les salons
        # self.join_saved_channels()

        self.timeout = self.Config.API_TIMEOUT

        # Listes qui vont contenir les ip a scanner avec les différentes API
        self.abuseipdb_UserModel: list[User.UserModel] = []
        self.freeipapi_UserModel: list[User.UserModel] = []
        self.cloudfilt_UserModel: list[User.UserModel] = []
        self.psutil_UserModel: list[User.UserModel]    = []
        self.localscan_UserModel: list[User.UserModel] = []

        # Variables qui indique que les threads sont en cours d'éxecutions
        self.abuseipdb_isRunning:bool       = True
        self.freeipapi_isRunning:bool       = True
        self.cloudfilt_isRunning:bool       = True
        self.psutil_isRunning:bool          = True
        self.localscan_isRunning:bool       = True
        self.reputationTimer_isRunning:bool = True

        # Variable qui va contenir les users
        self.flood_system = {}

        # Contient les premieres informations de connexion
        self.reputation_first_connexion = {'ip': '', 'score': -1}

        # Laisser vide si aucune clé
        self.abuseipdb_key = '13c34603fee4d2941a2c443cc5c77fd750757ca2a2c1b304bd0f418aff80c24be12651d1a3cfe674'
        self.cloudfilt_key = 'r1gEtjtfgRQjtNBDMxsg'

        # Démarrer les threads pour démarrer les api
        self.Base.create_thread(func=self.thread_freeipapi_scan)
        self.Base.create_thread(func=self.thread_cloudfilt_scan)
        self.Base.create_thread(func=self.thread_abuseipdb_scan)
        self.Base.create_thread(func=self.thread_local_scan)
        self.Base.create_thread(func=self.thread_psutil_scan)
        self.Base.create_thread(func=self.thread_reputation_timer)

        if self.ModConfig.reputation == 1:
            self.Irc.send2socket(f":{self.Config.SERVICE_ID} SAMODE {self.Config.SALON_JAIL} +{self.Config.SERVICE_UMODES} {self.Config.SERVICE_NICKNAME}")

        return None

    def __set_commands(self, commands:dict[int, list[str]]) -> None:
        """### Rajoute les commandes du module au programme principal

        Args:
            commands (list): Liste des commandes du module
        """
        for level, com in commands.items():
            for c in commands[level]:
                if not c in self.Irc.commands:
                    self.Irc.commands_level[level].append(c)
                    self.Irc.commands.append(c)

        return None

    def __create_tables(self) -> None:
        """Methode qui va créer la base de donnée si elle n'existe pas.
           Une Session unique pour cette classe sera crée, qui sera utilisé dans cette classe / module
        Args:
            database_name (str): Nom de la base de données ( pas d'espace dans le nom )

        Returns:
            None: Aucun retour n'es attendu
        """

        table_channel = '''CREATE TABLE IF NOT EXISTS def_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            channel TEXT
            ) 
        '''

        table_config = '''CREATE TABLE IF NOT EXISTS def_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            parameter TEXT,
            value TEXT
            ) 
        '''

        table_trusted = '''CREATE TABLE IF NOT EXISTS def_trusted (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            user TEXT,
            host TEXT,
            vhost TEXT
            )
        '''

        # self.Base.db_execute_query(table_channel)
        # self.Base.db_execute_query(table_config)
        # self.Base.db_execute_query(table_trusted)
        return None

    def __load_module_configuration(self) -> None:
        """### Load Module Configuration
        """
        try:
            # Variable qui va contenir les options de configuration du module Defender
            self.ModConfig = self.ModConfModel(
                reputation=0, reputation_timer=1, reputation_seuil=26, reputation_score_after_release=27, 
                reputation_ban_all_chan=0,reputation_sg=1,
                local_scan=0, psutil_scan=0, abuseipdb_scan=0, freeipapi_scan=0, cloudfilt_scan=0,
                flood=0, flood_message=5, flood_time=1, flood_timer=20
                )

            # Sync the configuration with core configuration (Mandatory)
            self.Base.db_sync_core_config(self.module_name, self.ModConfig)

            return None

        except TypeError as te:
            self.Logs.critical(te)

    def __update_configuration(self, param_key: str, param_value: str):

        self.Base.db_update_core_config(self.module_name, self.ModConfig, param_key, param_value)

    def unload(self) -> None:
        """Cette methode sera executée a chaque désactivation ou 
        rechargement de module
        """
        self.abuseipdb_UserModel: list[User.UserModel] = []
        self.freeipapi_UserModel: list[User.UserModel] = []
        self.cloudfilt_UserModel: list[User.UserModel] = []
        self.psutil_UserModel: list[User.UserModel]    = []
        self.localscan_UserModel: list[User.UserModel] = []

        self.abuseipdb_isRunning:bool = False
        self.freeipapi_isRunning:bool = False
        self.cloudfilt_isRunning:bool = False
        self.psutil_isRunning:bool    = False
        self.localscan_isRunning:bool = False
        self.reputationTimer_isRunning:bool = False
        return None

    def add_defender_channel(self, channel:str) -> bool:
        """Cette fonction ajoute les salons de join de Defender

        Args:
            channel (str): le salon à enregistrer.
        """
        mes_donnees = {'channel': channel}
        response = self.Base.db_execute_query("SELECT id FROM def_channels WHERE channel = :channel", mes_donnees)
        
        isChannelExist = response.fetchone()

        if isChannelExist is None:
            mes_donnees = {'datetime': self.Base.get_datetime(), 'channel': channel}
            insert = self.Base.db_execute_query(f"INSERT INTO def_channels (datetime, channel) VALUES (:datetime, :channel)", mes_donnees)
            return True
        else:
            return False

    def delete_defender_channel(self, channel:str) -> bool:
        """Cette fonction supprime les salons de join de Defender

        Args:
            channel (str): le salon à enregistrer.
        """
        mes_donnes = {'channel': channel}
        response = self.Base.db_execute_query("DELETE FROM def_channels WHERE channel = :channel", mes_donnes)
        
        affected_row = response.rowcount

        if affected_row > 0:
            return True
        else:
            return False

    def reputation_insert(self, reputationModel: ReputationModel) -> bool:

        response = False

        # Check if the user already exist
        for reputation in self.UID_REPUTATION_DB:
            if reputation.uid == reputationModel.uid:
                return response

        self.UID_REPUTATION_DB.append(reputationModel)
        self.Logs.debug(f'Reputation inserted: {reputationModel}')
        response = True

        return response

    def reputation_delete(self, uidornickname:str) -> bool:

        response = False

        for record in self.UID_REPUTATION_DB:
            if record.uid == uidornickname:
                self.UID_REPUTATION_DB.remove(record)
                response = True
                self.Logs.debug(f'UID ({record.uid}) has been deleted')
            elif record.nickname == uidornickname:
                self.UID_REPUTATION_DB.remove(record)
                response = True
                self.Logs.debug(f'Nickname ({record.nickname}) has been deleted')

        if not response:
            self.Logs.critical(f'The UID {uidornickname} was not deleted')

        return response

    def reputation_check(self, uidornickname: str) -> bool:
        """Check if the uid exist in the dataclass

        Args:
            uidornickname (str): UID or nickname of the user

        Returns:
            bool: True if the user exist in the reputation dataclass
        """
        response = False

        for reputation in self.UID_REPUTATION_DB:
            if reputation.uid == uidornickname:
                response = True
            elif reputation.nickname == uidornickname:
                response = True

        return response

    def reputation_get_Reputation(self, uidornickname: str) -> Union[ReputationModel, None]:
        """Get a user reputation object with all information

        Args:
            uidornickname (str): The UID or Nickname of the suspected user

        Returns:
            ReputationModel or None: Return the Reputation Model or None if the user doesn't exist
        """

        Reputation_user = None
        for reputation in self.UID_REPUTATION_DB:
            if reputation.uid == uidornickname:
                Reputation_user = reputation
            elif reputation.nickname == uidornickname:
                Reputation_user = reputation
        
        return Reputation_user

    def insert_db_trusted(self, uid: str, nickname:str) -> None:

        uid = self.User.get_uid(uid)
        nickname = self.User.get_nickname(nickname)

        query = "SELECT id FROM def_trusted WHERE user = ?"
        exec_query = self.Base.db_execute_query(query, {"user": nickname})
        response = exec_query.fetchone()

        if not response is None:
            q_insert = "INSERT INTO def_trusted (datetime, user, host, vhost) VALUES (?, ?, ?, ?)"
            mes_donnees = {'datetime': self.Base.get_datetime(), 'user': nickname, 'host': '*', 'vhost': '*'}
            exec_query = self.Base.db_execute_query(q_insert, mes_donnees)
            pass

    def join_saved_channels(self) -> None:

        result = self.Base.db_execute_query("SELECT id, channel FROM def_channels")
        channels = result.fetchall()
        jail_chan = self.Config.SALON_JAIL
        jail_chan_mode = self.Config.SALON_JAIL_MODES
        service_id = self.Config.SERVICE_ID
        dumodes = self.Config.SERVICE_UMODES
        dnickname = self.Config.SERVICE_NICKNAME

        unixtime = self.Base.get_unixtime()

        for channel in channels:
            id, chan = channel
            self.Irc.send2socket(f":{self.Config.SERVEUR_ID} SJOIN {unixtime} {chan} + :{self.Config.SERVICE_ID}")
            if chan == jail_chan:
                self.Irc.send2socket(f":{service_id} SAMODE {jail_chan} +{dumodes} {dnickname}")
                self.Irc.send2socket(f":{service_id} MODE {jail_chan} +{jail_chan_mode}")

        return None

    def get_user_uptime_in_minutes(self, uidornickname:str) -> float:
        """Retourne depuis quand l'utilisateur est connecté (en secondes ).

        Args:
            uid (str): le uid ou le nickname de l'utilisateur

        Returns:
            int: Temps de connexion de l'utilisateur en secondes 
        """

        get_user = self.User.get_User(uidornickname)
        if get_user is None:
            return 0

        # Convertir la date enregistrée dans UID_DB en un objet {datetime}
        connected_time_string = get_user.connexion_datetime
        if type(connected_time_string) == datetime:
            connected_time = connected_time_string
        else:
            connected_time = datetime.strptime(connected_time_string, "%Y-%m-%d %H:%M:%S.%f")

        # Quelle heure est-il ?
        current_datetime = datetime.now()

        uptime = current_datetime - connected_time
        convert_to_minutes = uptime.seconds / 60
        uptime_minutes = round(number=convert_to_minutes, ndigits=2)

        return uptime_minutes

    def system_reputation(self, uid:str)-> None:
        # Reputation security
        # - Activation ou désactivation du système --> OK
        # - Le user sera en mesure de changer la limite de la réputation --> OK
        # - Defender devra envoyer l'utilisateur sur un salon défini dans la configuration, {jail_chan}
        # - Defender devra bloquer cet utilisateur sur le salon qui sera en mode (+m)
        # - Defender devra envoyer un message du type "Merci de taper cette comande /msg {nomdudefender} {un code généré aléatoirement}
        # - Defender devra reconnaître le code
        # - Defender devra libérer l'utilisateur et l'envoyer vers un salon défini dans la configuration {welcome_chan}
        # - Defender devra intégrer une liste d'IDs (pseudo/host) exemptés de 'Reputation security' malgré un score de rép. faible et un pseudo non enregistré.
        try:

            get_reputation = self.reputation_get_Reputation(uid)

            if get_reputation is None:
                self.Logs.error(f'UID {uid} has not been found')
                return False

            salon_logs = self.Config.SERVICE_CHANLOG
            salon_jail = self.Config.SALON_JAIL

            code = get_reputation.secret_code
            jailed_nickname = get_reputation.nickname
            jailed_score = get_reputation.score

            color_red = self.Config.CONFIG_COLOR['rouge']
            color_black = self.Config.CONFIG_COLOR['noire']
            color_bold = self.Config.CONFIG_COLOR['gras']
            service_id = self.Config.SERVICE_ID
            service_prefix = self.Config.SERVICE_PREFIX
            reputation_ban_all_chan = self.ModConfig.reputation_ban_all_chan

            if not get_reputation.isWebirc:
                # Si le user ne vient pas de webIrc

                self.Irc.send2socket(f":{service_id} SAJOIN {jailed_nickname} {salon_jail}")
                self.Irc.send2socket(f":{service_id} PRIVMSG {salon_logs} :[{color_red} REPUTATION {color_black}] : Connexion de {jailed_nickname} ({jailed_score}) ==> {salon_jail}")
                self.Irc.send2socket(f":{service_id} NOTICE {jailed_nickname} :[{color_red} {jailed_nickname} {color_black}] : Merci de tapez la commande suivante {color_bold}{service_prefix}code {code}{color_bold}")
                if reputation_ban_all_chan == 1:
                    for chan in self.Channel.UID_CHANNEL_DB:
                        if chan.name != salon_jail:
                            self.Irc.send2socket(f":{service_id} MODE {chan.name} +b {jailed_nickname}!*@*")
                            self.Irc.send2socket(f":{service_id} KICK {chan.name} {jailed_nickname}")

                self.Logs.info(f"system_reputation : {jailed_nickname} à été capturé par le système de réputation")
                # self.Irc.create_ping_timer(int(self.ModConfig.reputation_timer) * 60, 'Defender', 'system_reputation_timer')
                # self.Base.create_timer(int(self.ModConfig.reputation_timer) * 60, self.system_reputation_timer)
            else:
                self.Logs.info(f"system_reputation : {jailed_nickname} à été supprimé du système de réputation car connecté via WebIrc ou il est dans la 'Trusted list'")
                self.reputation_delete(uid)

        except IndexError as e:
            self.Logs.error(f"system_reputation : {str(e)}")

    def system_reputation_timer(self) -> None:
        try:
            reputation_flag = self.ModConfig.reputation
            reputation_timer = self.ModConfig.reputation_timer
            reputation_seuil = self.ModConfig.reputation_seuil
            ban_all_chan = self.ModConfig.reputation_ban_all_chan
            service_id = self.Config.SERVICE_ID
            dchanlog = self.Config.SERVICE_CHANLOG
            color_red = self.Config.CONFIG_COLOR['rouge']
            color_black = self.Config.CONFIG_COLOR['noire']
            salon_jail = self.Config.SALON_JAIL

            if reputation_flag == 0:
                return None
            elif reputation_timer == 0:
                return None

            uid_to_clean = []

            for user in self.UID_REPUTATION_DB:
                if not user.isWebirc: # Si il ne vient pas de WebIRC
                    if self.get_user_uptime_in_minutes(user.uid) >= reputation_timer and int(user.score) <= int(reputation_seuil):
                        self.Irc.send2socket(f":{service_id} PRIVMSG {dchanlog} :[{color_red} REPUTATION {color_black}] : Action sur {user.nickname} aprés {str(reputation_timer)} minutes d'inactivité")
                        self.Irc.send2socket(f":{service_id} KILL {user.nickname} After {str(reputation_timer)} minutes of inactivity you should reconnect and type the password code ")
                        self.Irc.send2socket(f":{self.Config.SERVEUR_LINK} REPUTATION {user.ip} 0")

                        self.Logs.info(f"Nickname: {user.nickname} KILLED after {str(reputation_timer)} minutes of inactivity")
                        uid_to_clean.append(user.uid)

            for uid in uid_to_clean:
                # Suppression des éléments dans {UID_DB} et {REPUTATION_DB}
                for chan in self.Channel.UID_CHANNEL_DB:
                    if chan.name != salon_jail and ban_all_chan == 1:
                        get_user_reputation = self.reputation_get_Reputation(uid)
                        self.Irc.send2socket(f":{service_id} MODE {chan.name} -b {get_user_reputation.nickname}!*@*")

                # Lorsqu'un utilisateur quitte, il doit être supprimé de {UID_DB}.
                self.Channel.delete_user_from_all_channel(uid)
                self.reputation_delete(uid)
                self.User.delete(uid)

        except AssertionError as ae:
            self.Logs.error(f'Assertion Error -> {ae}')

    def thread_reputation_timer(self) -> None:
        try:
            while self.reputationTimer_isRunning:
                self.system_reputation_timer()
                time.sleep(5)

            return None
        except ValueError as ve:
            self.Irc.Base.logs.error(f"thread_reputation_timer Error : {ve}")

    def _execute_flood_action(self, action:str, channel:str) -> None:
        """DO NOT EXECUTE THIS FUNCTION WITHOUT THREADING

        Args:
            action (str): _description_
            timer (int): _description_
            nickname (str): _description_
            channel (str): _description_

        Returns:
            _type_: _description_
        """
        service_id = self.Config.SERVICE_ID
        match action:
            case 'mode-m':
                # Action -m sur le salon
                self.Irc.send2socket(f":{service_id} MODE {channel} -m")
            case _:
                pass
        
        return None

    def flood(self, detected_user:str, channel:str) -> None:

        if self.ModConfig.flood == 0:
            return None

        if not '#' in channel:
            return None

        flood_time = self.ModConfig.flood_time
        flood_message = self.ModConfig.flood_message
        flood_timer = self.ModConfig.flood_timer
        service_id = self.Config.SERVICE_ID
        dnickname = self.Config.SERVICE_NICKNAME
        color_red = self.Config.CONFIG_COLOR['rouge']
        color_bold = self.Config.CONFIG_COLOR['gras']
        
        get_detected_uid = self.User.get_uid(detected_user)
        get_detected_nickname = self.User.get_nickname(detected_user)
        
        unixtime = self.Base.get_unixtime()
        get_diff_secondes = 0

        if not get_detected_uid in self.flood_system:
            self.flood_system[get_detected_uid] = {
                    'nbr_msg': 0,
                    'first_msg_time': unixtime
                }

        self.flood_system[get_detected_uid]['nbr_msg'] += 1
        get_diff_secondes = unixtime - self.flood_system[get_detected_uid]['first_msg_time']
        if get_diff_secondes > flood_time:
            self.flood_system[get_detected_uid]['first_msg_time'] = unixtime
            self.flood_system[get_detected_uid]['nbr_msg'] = 0
            get_diff_secondes = unixtime - self.flood_system[get_detected_uid]['first_msg_time']
        
        elif self.flood_system[get_detected_uid]['nbr_msg'] > flood_message:
            self.Irc.Base.logs.info('system de flood detecté')
            self.Irc.send2socket(f':{dnickname} PRIVMSG {channel} : {color_red} {color_bold} Flood detected. Apply the +m mode (Ô_o)')
            self.Irc.send2socket(f":{service_id} MODE {channel} +m")
            self.Irc.Base.logs.info(f'FLOOD Détecté sur {get_detected_nickname} mode +m appliqué sur le salon {channel}')
            self.flood_system[get_detected_uid]['nbr_msg'] = 0
            self.flood_system[get_detected_uid]['first_msg_time'] = unixtime

            self.Base.create_timer(flood_timer, self._execute_flood_action, ('mode-m', channel))

    def run_db_action_timer(self, wait_for: float = 0) -> None:

        query = "SELECT parameter FROM def_config"
        res = self.Base.db_execute_query(query)
        service_id = self.Config.SERVICE_ID
        dchanlog = self.Config.SERVICE_CHANLOG

        for param in res.fetchall():
            if param[0] == 'reputation':
                self.Irc.send2socket(f":{service_id} PRIVMSG {dchanlog} : ===> {param[0]}")
            else:
                self.Irc.send2socket(f":{service_id} PRIVMSG {dchanlog} : {param[0]}")
                # print(f":{service_id} PRIVMSG {dchanlog} : {param[0]}")

        # self.Base.garbage_collector_timer()

        return None

    def scan_ports(self, userModel: User.UserModel) -> None:
        """local_scan

        Args:
            userModel (UserModel): _description_
        """
        User = userModel
        remote_ip = User.remote_ip
        username = User.username
        hostname = User.hostname
        nickname = User.nickname
        fullname = f'{nickname}!{username}@{hostname}'

        if remote_ip in self.Config.WHITELISTED_IP:
            return None

        for port in self.Config.PORTS_TO_SCAN:
            try:
                newSocket = ''
                newSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM or socket.SOCK_NONBLOCK)
                newSocket.settimeout(0.5)

                connection = (remote_ip, self.Base.int_if_possible(port))
                newSocket.connect(connection)

                self.Irc.send2socket(f":{self.Config.SERVICE_NICKNAME} PRIVMSG {self.Config.SERVICE_CHANLOG} :[ {self.Config.CONFIG_COLOR['rouge']}PROXY_SCAN{self.Config.CONFIG_COLOR['noire']} ] {fullname} ({remote_ip}) :     Port [{str(port)}] ouvert sur l'adresse ip [{remote_ip}]")
                # print(f"=======> Le port {str(port)} est ouvert !!")
                self.Base.running_sockets.append(newSocket)
                # print(newSocket)
                newSocket.shutdown(socket.SHUT_RDWR)
                newSocket.close()

            except (socket.timeout, ConnectionRefusedError):
                self.Logs.info(f"Le port {remote_ip}:{str(port)} est fermé")
            except AttributeError as ae:
                self.Logs.warning(f"AttributeError ({remote_ip}): {ae}")
            except socket.gaierror as err:
                self.Logs.warning(f"Address Info Error ({remote_ip}): {err}")
            finally:
                # newSocket.shutdown(socket.SHUT_RDWR)
                newSocket.close()
                self.Logs.info('=======> Fermeture de la socket')

    def thread_local_scan(self) -> None:
        try:
            while self.localscan_isRunning:

                list_to_remove:list = []
                for user in self.localscan_UserModel:
                    self.scan_ports(user)
                    list_to_remove.append(user)
                    time.sleep(1)

                for user_model in list_to_remove:
                    self.localscan_UserModel.remove(user_model)

                time.sleep(1)

            return None
        except ValueError as ve:
            self.Logs.warning(f"thread_local_scan Error : {ve}")

    def get_ports_connexion(self, userModel: User.UserModel) -> list[int]:
        """psutil_scan for Linux (should be run on the same location as the unrealircd server)

        Args:
            userModel (UserModel): The User Model Object

        Returns:
            list[int]: list of ports
        """
        try:
            User = userModel
            remote_ip = User.remote_ip
            username = User.username
            hostname = User.hostname
            nickname = User.nickname

            if remote_ip in self.Config.WHITELISTED_IP:
                return None

            connections = psutil.net_connections(kind='inet')
            fullname = f'{nickname}!{username}@{hostname}'

            matching_ports = [conn.raddr.port for conn in connections if conn.raddr and conn.raddr.ip == remote_ip]
            self.Logs.info(f"Connexion of {fullname} ({remote_ip}) using ports : {str(matching_ports)}")

            if matching_ports:
                self.Irc.send2socket(f":{self.Config.SERVICE_NICKNAME} PRIVMSG {self.Config.SERVICE_CHANLOG} :[ {self.Config.CONFIG_COLOR['rouge']}PSUTIL_SCAN{self.Config.CONFIG_COLOR['noire']} ] {fullname} ({remote_ip}) : is using ports {matching_ports}")

            return matching_ports

        except psutil.AccessDenied as ad:
            self.Logs.critical(f'psutil_scan: Permission error: {ad}')

    def thread_psutil_scan(self) -> None:
        try:
            
            while self.psutil_isRunning:

                list_to_remove:list = []
                for user in self.psutil_UserModel:
                    self.get_ports_connexion(user)
                    list_to_remove.append(user)
                    time.sleep(1)

                for user_model in list_to_remove:
                    self.psutil_UserModel.remove(user_model)

                time.sleep(1)

            return None
        except ValueError as ve:
            self.Logs.warning(f"thread_psutil_scan Error : {ve}")

    def abuseipdb_scan(self, userModel: User.UserModel) -> Union[dict[str, any], None]:
        """Analyse l'ip avec AbuseIpDB
           Cette methode devra etre lancer toujours via un thread ou un timer.
        Args:
            userModel (UserModel): l'objet User qui contient l'ip

        Returns:
            dict[str, any] | None: les informations du provider
            keys : 'score', 'country', 'isTor', 'totalReports'
        """
        User = userModel
        remote_ip = User.remote_ip
        username = User.username
        hostname = User.hostname
        nickname = User.nickname

        if remote_ip in self.Config.WHITELISTED_IP:
            return None
        if self.ModConfig.abuseipdb_scan == 0:
            return None

        if self.abuseipdb_key == '':
            return None

        url = 'https://api.abuseipdb.com/api/v2/check'
        querystring = {
            'ipAddress': remote_ip,
            'maxAgeInDays': '90'
        }

        headers = {
            'Accept': 'application/json',
            'Key': self.abuseipdb_key
        }

        try:
            response = requests.request(method='GET', url=url, headers=headers, params=querystring, timeout=self.timeout)

            # Formatted output
            decodedResponse = json.loads(response.text)

            if not 'data' in decodedResponse:
                return None

            result = {
                'score': decodedResponse['data']['abuseConfidenceScore'],
                'country': decodedResponse['data']['countryCode'],
                'isTor': decodedResponse['data']['isTor'],
                'totalReports': decodedResponse['data']['totalReports']
            }

            service_id = self.Config.SERVICE_ID
            service_chanlog = self.Config.SERVICE_CHANLOG
            color_red = self.Config.CONFIG_COLOR['rouge']
            color_black = self.Config.CONFIG_COLOR['noire']

            # pseudo!ident@host
            fullname = f'{nickname}!{username}@{hostname}'

            self.Irc.send2socket(f":{service_id} PRIVMSG {service_chanlog} :[ {color_red}ABUSEIPDB_SCAN{color_black} ] : Connexion de {fullname} ({remote_ip}) ==> Score: {str(result['score'])} | Country : {result['country']} | Tor : {str(result['isTor'])} | Total Reports : {str(result['totalReports'])}")

            if result['isTor']:
                self.Irc.send2socket(f":{service_id} GLINE +*@{remote_ip} {self.Config.GLINE_DURATION} This server do not allow Tor connexions {str(result['isTor'])} - Detected by Abuseipdb")
            elif result['score'] >= 95:
                self.Irc.send2socket(f":{service_id} GLINE +*@{remote_ip} {self.Config.GLINE_DURATION} You were banned from this server because your abuse score is = {str(result['score'])} - Detected by Abuseipdb")

            response.close()

            return result
        except KeyError as ke:
            self.Logs.error(f"AbuseIpDb KeyError : {ke}")
        except requests.ReadTimeout as rt:
            self.Logs.error(f"AbuseIpDb Timeout : {rt}")
        except requests.ConnectionError as ce:
            self.Logs.error(f"AbuseIpDb Connection Error : {ce}")
        except Exception as err:
            self.Logs.error(f"General Error Abuseipdb : {err}")

    def thread_abuseipdb_scan(self) -> None:
        try:

            while self.abuseipdb_isRunning:

                list_to_remove: list = []
                for user in self.abuseipdb_UserModel:
                    self.abuseipdb_scan(user)
                    list_to_remove.append(user)
                    time.sleep(1)

                for user_model in list_to_remove:
                    self.abuseipdb_UserModel.remove(user_model)

                time.sleep(1)

            return None
        except ValueError as ve:
                self.Logs.error(f"thread_abuseipdb_scan Error : {ve}")

    def freeipapi_scan(self, userModel: User.UserModel) -> Union[dict[str, any], None]:
        """Analyse l'ip avec Freeipapi
           Cette methode devra etre lancer toujours via un thread ou un timer.
        Args:
            remote_ip (_type_): l'ip a analyser

        Returns:
            dict[str, any] | None: les informations du provider
            keys : 'countryCode', 'isProxy'
        """
        User = userModel
        remote_ip = User.remote_ip
        username = User.username
        hostname = User.hostname
        nickname = User.nickname

        if remote_ip in self.Config.WHITELISTED_IP:
            return None
        if self.ModConfig.freeipapi_scan == 0:
            return None

        service_id = self.Config.SERVICE_ID
        service_chanlog = self.Config.SERVICE_CHANLOG
        color_red = self.Config.CONFIG_COLOR['rouge']
        color_black = self.Config.CONFIG_COLOR['noire']

        url = f'https://freeipapi.com/api/json/{remote_ip}'

        headers = {
            'Accept': 'application/json',
        }

        try:
            response = requests.request(method='GET', url=url, headers=headers, timeout=self.timeout)

            # Formatted output
            decodedResponse = json.loads(response.text)

            status_code = response.status_code
            if status_code == 429:
                self.Logs.warning(f'Too Many Requests - The rate limit for the API has been exceeded.')
                return None
            elif status_code != 200:
                self.Logs.warning(f'status code = {str(status_code)}')
                return None

            result = {
                'countryCode': decodedResponse['countryCode'] if 'countryCode' in decodedResponse else None,
                'isProxy': decodedResponse['isProxy'] if 'isProxy' in decodedResponse else None
            }

            # pseudo!ident@host
            fullname = f'{nickname}!{username}@{hostname}'

            self.Irc.send2socket(f":{service_id} PRIVMSG {service_chanlog} :[ {color_red}FREEIPAPI_SCAN{color_black} ] : Connexion de {fullname} ({remote_ip}) ==> Proxy: {str(result['isProxy'])} | Country : {str(result['countryCode'])}")

            if result['isProxy']:
                self.Irc.send2socket(f":{service_id} GLINE +*@{remote_ip} {self.Config.GLINE_DURATION} This server do not allow proxy connexions {str(result['isProxy'])} - detected by freeipapi")
            response.close()

            return result
        except KeyError as ke:
            self.Logs.error(f"FREEIPAPI_SCAN KeyError : {ke}")
        except Exception as err:
            self.Logs.error(f"General Error Freeipapi : {err}")

    def thread_freeipapi_scan(self) -> None:
        try:

            while self.freeipapi_isRunning:

                list_to_remove: list[User.UserModel] = []
                for user in self.freeipapi_UserModel:
                    self.freeipapi_scan(user)
                    list_to_remove.append(user)
                    time.sleep(1)

                for user_model in list_to_remove:
                    self.freeipapi_UserModel.remove(user_model)

                time.sleep(1)

            return None
        except ValueError as ve:
            self.Logs.error(f"thread_freeipapi_scan Error : {ve}")

    def cloudfilt_scan(self, userModel: User.UserModel) -> Union[dict[str, any], None]:
        """Analyse l'ip avec cloudfilt
           Cette methode devra etre lancer toujours via un thread ou un timer.
        Args:
            remote_ip (_type_): l'ip a analyser

        Returns:
            dict[str, any] | None: les informations du provider
            keys : 'countryCode', 'isProxy'
        """
        User = userModel
        remote_ip = User.remote_ip
        username = User.username
        hostname = User.hostname
        nickname = User.nickname

        if remote_ip in self.Config.WHITELISTED_IP:
            return None
        if self.ModConfig.cloudfilt_scan == 0:
            return None
        if self.cloudfilt_key == '':
            return None

        service_id = self.Config.SERVICE_ID
        service_chanlog = self.Config.SERVICE_CHANLOG
        color_red = self.Config.CONFIG_COLOR['rouge']
        color_black = self.Config.CONFIG_COLOR['noire']

        url = f"https://developers18334.cloudfilt.com/"

        data = {
            'ip': remote_ip,
            'key': self.cloudfilt_key
        }

        try:
            response = requests.post(url=url, data=data)
            # Formatted output
            decodedResponse = json.loads(response.text)
            status_code = response.status_code
            if status_code != 200:
                self.Logs.warning(f'Error connecting to cloudfilt API | Code: {str(status_code)}')
                return None

            result = {
                'countryiso': decodedResponse['countryiso'] if 'countryiso' in decodedResponse else None,
                'listed': decodedResponse['listed'] if 'listed' in decodedResponse else None,
                'listed_by': decodedResponse['listed_by'] if 'listed_by' in decodedResponse else None,
                'host': decodedResponse['host'] if 'host' in decodedResponse else None
            }

            # pseudo!ident@host
            fullname = f'{nickname}!{username}@{hostname}'

            self.Irc.send2socket(f":{service_id} PRIVMSG {service_chanlog} :[ {color_red}CLOUDFILT_SCAN{color_black} ] : Connexion de {fullname} ({remote_ip}) ==> Host: {str(result['host'])} | country: {str(result['countryiso'])} | listed: {str(result['listed'])} | listed by : {str(result['listed_by'])}")

            if result['listed']:
                self.Irc.send2socket(f":{service_id} GLINE +*@{remote_ip} {self.Config.GLINE_DURATION} You connexion is listed as dangerous {str(result['listed'])} {str(result['listed_by'])} - detected by cloudfilt")

            response.close()

            return result
        except KeyError as ke:
            self.Logs.error(f"CLOUDFILT_SCAN KeyError : {ke}")
        return None

    def thread_cloudfilt_scan(self) -> None:
        try:

            while self.cloudfilt_isRunning:

                list_to_remove:list = []
                for user in self.cloudfilt_UserModel:
                    self.cloudfilt_scan(user)
                    list_to_remove.append(user)
                    time.sleep(1)

                for user_model in list_to_remove:
                    self.cloudfilt_UserModel.remove(user_model)

                time.sleep(1)

            return None
        except ValueError as ve:
            self.Logs.error(f"Thread_cloudfilt_scan Error : {ve}")

    def cmd(self, data: list) -> None:

        service_id = self.Config.SERVICE_ID                 # Defender serveur id
        cmd = list(data).copy()

        if len(cmd) < 2:
            return None

        match cmd[1]:

            case 'EOS':
                if self.Irc.INIT == 0:
                    self.Irc.send2socket(f":{service_id} SAMODE {self.Config.SALON_JAIL} +{self.Config.SERVICE_UMODES} {self.Config.SERVICE_NICKNAME}")

            case 'REPUTATION':
                # :001 REPUTATION 91.168.141.239 118
                try:
                    self.reputation_first_connexion['ip'] = cmd[2]
                    self.reputation_first_connexion['score'] = cmd[3]
                    if str(cmd[3]).find('*') != -1:
                        # If the reputation changed, we do not need to scan the IP
                        return None

                    if not self.Base.is_valid_ip(cmd[2]):
                        return None

                    # Possibilité de déclancher les bans a ce niveau.
                except IndexError as ie:
                    self.Logs.error(f'cmd reputation: index error: {ie}')

        match cmd[2]:

            case 'PRIVMSG':
                cmd.pop(0)
                user_trigger = str(cmd[0]).replace(':','')
                channel = cmd[2]
                find_nickname = self.User.get_nickname(user_trigger)
                self.flood(find_nickname, channel)

            case 'UID':
                # If Init then do nothing
                if self.Irc.INIT == 1:
                    return None

                # Supprimer la premiere valeur et finir le code normalement
                cmd.pop(0)

                # Get User information
                _User = self.User.get_User(str(cmd[7]))

                # If user is not service or IrcOp then scan them
                if not re.match(fr'^.*[S|o?].*$', _User.umodes):
                    self.abuseipdb_UserModel.append(_User) if self.ModConfig.abuseipdb_scan == 1 and not _User.remote_ip in self.Config.WHITELISTED_IP else None
                    self.freeipapi_UserModel.append(_User) if self.ModConfig.freeipapi_scan == 1 and not _User.remote_ip in self.Config.WHITELISTED_IP else None
                    self.cloudfilt_UserModel.append(_User) if self.ModConfig.cloudfilt_scan == 1 and not _User.remote_ip in self.Config.WHITELISTED_IP else None
                    self.psutil_UserModel.append(_User) if self.ModConfig.psutil_scan == 1 and not _User.remote_ip in self.Config.WHITELISTED_IP else None
                    self.localscan_UserModel.append(_User) if self.ModConfig.local_scan == 1 and not _User.remote_ip in self.Config.WHITELISTED_IP else None

                if _User is None:
                    self.Logs.critical(f'This UID: [{cmd[7]}] is not available please check why')
                    return None

                reputation_flag = self.ModConfig.reputation
                reputation_seuil = self.ModConfig.reputation_seuil

                if self.Irc.INIT == 0:
                    # Si le user n'es pas un service ni un IrcOP
                    if not re.match(fr'^.*[S|o?].*$', _User.umodes):
                        if reputation_flag == 1 and _User.score_connexion <= reputation_seuil:
                            currentDateTime = self.Base.get_datetime()
                            self.reputation_insert(
                                self.ReputationModel(
                                    uid=_User.uid, nickname=_User.nickname, username=_User.username, realname=_User.realname, 
                                    hostname=_User.hostname, umodes=_User.umodes, vhost=_User.vhost, ip=_User.remote_ip, score=_User.score_connexion,
                                    secret_code=self.Base.get_random(8), isWebirc=_User.isWebirc, isWebsocket=_User.isWebsocket, connected_datetime=currentDateTime,
                                    updated_datetime=currentDateTime
                                )
                            )
                            # self.Irc.send2socket(f":{service_id} WHOIS {nickname}")
                            if self.reputation_check(_User.uid):
                                if reputation_flag == 1 and _User.score_connexion <= reputation_seuil:
                                    self.system_reputation(_User.uid)
                                    self.Logs.info('Démarrer le systeme de reputation')

            case 'SJOIN':
                # ['@msgid=F9B7JeHL5pj9nN57cJ5pEr;time=2023-12-28T20:47:24.305Z', ':001', 'SJOIN', '1702138958', '#welcome', ':0015L1AHL']
                try:
                    cmd.pop(0)
                    parsed_chan = cmd[3]

                    if self.ModConfig.reputation == 1:
                        parsed_UID = cmd[4]
                        pattern = fr'^:[@|%|\+|~|\*]*'
                        parsed_UID = re.sub(pattern, '', parsed_UID)

                        get_reputation = self.reputation_get_Reputation(parsed_UID)

                        self.Irc.send2socket(f":{service_id} MODE {parsed_chan} +b ~security-group:unknown-users")
                        self.Irc.send2socket(f":{service_id} MODE {parsed_chan} +eee ~security-group:webirc-users ~security-group:known-users ~security-group:websocket-users")

                        if not get_reputation is None:
                            isWebirc = get_reputation.isWebirc

                            if not isWebirc:
                                if parsed_chan != self.Config.SALON_JAIL:
                                    self.Irc.send2socket(f":{service_id} SAPART {get_reputation.nickname} {parsed_chan}")

                            if self.ModConfig.reputation_ban_all_chan == 1 and not isWebirc:
                                if parsed_chan != self.Config.SALON_JAIL:
                                    self.Irc.send2socket(f":{service_id} MODE {parsed_chan} +b {get_reputation.nickname}!*@*")
                                    self.Irc.send2socket(f":{service_id} KICK {parsed_chan} {get_reputation.nickname}")

                        self.Logs.debug(f'SJOIN parsed_uid : {parsed_UID}')
                except KeyError as ke:
                    self.Logs.error(f"key error SJOIN : {ke}")

            case 'SLOG':
                # self.Base.scan_ports(cmd[7])
                cmd.pop(0)

                if not self.Base.is_valid_ip(cmd[7]):
                    return None

                # if self.ModConfig.local_scan == 1 and not cmd[7] in self.Config.WHITELISTED_IP:
                #     self.localscan_remote_ip.append(cmd[7])

                # if self.ModConfig.psutil_scan == 1 and not cmd[7] in self.Config.WHITELISTED_IP:
                #     self.psutil_remote_ip.append(cmd[7])

                # if self.ModConfig.abuseipdb_scan == 1 and not cmd[7] in self.Config.WHITELISTED_IP:
                #     self.abuseipdb_remote_ip.append(cmd[7])

                # if self.ModConfig.freeipapi_scan == 1 and not cmd[7] in self.Config.WHITELISTED_IP:
                #     self.freeipapi_remote_ip.append(cmd[7])

                # if self.ModConfig.cloudfilt_scan == 1 and not cmd[7] in self.Config.WHITELISTED_IP:
                #     self.cloudfilt_remote_ip.append(cmd[7])

            case 'NICK':
                # :0010BS24L NICK [NEWNICK] 1697917711
                # Changement de nickname
                try:
                    cmd.pop(0)
                    uid = str(cmd[0]).replace(':','')
                    get_Reputation = self.reputation_get_Reputation(uid)
                    jail_salon = self.Config.SALON_JAIL
                    service_id = self.Config.SERVICE_ID

                    if get_Reputation is None:
                        self.Logs.debug(f'This UID: {uid} is not listed in the reputation dataclass')
                        return None

                    # Update the new nickname
                    oldnick = get_Reputation.nickname
                    newnickname = cmd[2]
                    get_Reputation.nickname = newnickname

                    # If ban in all channel is ON then unban old nickname an ban the new nickname
                    if self.ModConfig.reputation_ban_all_chan == 1:
                        for chan in self.Channel.UID_CHANNEL_DB:
                            if chan.name != jail_salon:
                                self.Irc.send2socket(f":{service_id} MODE {chan.name} -b {oldnick}!*@*")
                                self.Irc.send2socket(f":{service_id} MODE {chan.name} +b {newnickname}!*@*")

                except KeyError as ke:
                    self.Logs.error(f'cmd - NICK - KeyError: {ke}')

            case 'QUIT':
                # :001N1WD7L QUIT :Quit: free_znc_1
                cmd.pop(0)
                ban_all_chan = self.Base.int_if_possible(self.ModConfig.reputation_ban_all_chan)
                user_id = str(cmd[0]).replace(':','')
                final_UID = user_id

                jail_salon = self.Config.SALON_JAIL
                service_id = self.Config.SERVICE_ID

                get_user_reputation = self.reputation_get_Reputation(final_UID)

                if not get_user_reputation is None:
                    final_nickname = get_user_reputation.nickname
                    for chan in self.Channel.UID_CHANNEL_DB:
                        if chan.name != jail_salon and ban_all_chan == 1:
                            self.Irc.send2socket(f":{service_id} MODE {chan.name} -b {final_nickname}!*@*")
                    self.reputation_delete(final_UID)

    def _hcmds(self, user:str, channel: any, cmd: list, fullcmd: list = []) -> None:

        command = str(cmd[0]).lower()
        fromuser = user
        fromchannel = channel if self.Base.Is_Channel(channel) else None
        channel = fromchannel

        dnickname = self.Config.SERVICE_NICKNAME            # Defender nickname
        dchanlog = self.Config.SERVICE_CHANLOG              # Defender chan log
        dumodes = self.Config.SERVICE_UMODES                # Les modes de Defender
        service_id = self.Config.SERVICE_ID                 # Defender serveur id
        jail_chan = self.Config.SALON_JAIL                  # Salon pot de miel
        jail_chan_mode = self.Config.SALON_JAIL_MODES       # Mode du salon "pot de miel"

        match command:

            case 'timer':
                try:
                    timer_sent = self.Base.int_if_possible(cmd[1])
                    timer_sent = int(timer_sent)
                    self.Base.create_timer(timer_sent, self.run_db_action_timer)

                except TypeError as te:
                    self.Logs.error(f"Type Error -> {te}")
                except ValueError as ve:
                    self.Logs.error(f"Value Error -> {ve}")

            case 'show_reputation':

                if not self.UID_REPUTATION_DB:
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : No one is suspected')

                for suspect in self.UID_REPUTATION_DB:
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Uid: {suspect.uid} | Nickname: {suspect.nickname} | Reputation: {suspect.score} | Secret code: {suspect.secret_code} | Connected on: {suspect.connected_datetime}')

            case 'code':
                try:
                    release_code = cmd[1]
                    jailed_nickname = self.User.get_nickname(fromuser)
                    jailed_UID = self.User.get_uid(fromuser)
                    get_reputation = self.reputation_get_Reputation(jailed_UID)

                    if get_reputation is None:
                        self.Irc.send2socket(f":{dnickname} NOTICE {fromuser} : No code is requested ...")
                        return False

                    jailed_IP = get_reputation.ip
                    jailed_salon = self.Config.SALON_JAIL
                    reputation_seuil = self.ModConfig.reputation_seuil
                    welcome_salon = self.Config.SALON_LIBERER

                    self.Logs.debug(f"IP de {jailed_nickname} : {jailed_IP}")
                    link = self.Config.SERVEUR_LINK
                    color_green = self.Config.CONFIG_COLOR['verte']
                    color_black = self.Config.CONFIG_COLOR['noire']

                    if release_code == get_reputation.secret_code:
                        self.Irc.send2socket(f':{dnickname} PRIVMSG {jailed_salon} : Bon mot de passe. Allez du vent !')

                        if self.ModConfig.reputation_ban_all_chan == 1:
                            for chan in self.Channel.UID_CHANNEL_DB:
                                if chan.name != jailed_salon:
                                    self.Irc.send2socket(f":{service_id} MODE {chan.name} -b {jailed_nickname}!*@*")

                        self.reputation_delete(jailed_UID)
                        self.Logs.debug(f'{jailed_UID} - {jailed_nickname} removed from REPUTATION_DB')
                        self.Irc.send2socket(f":{service_id} SAPART {jailed_nickname} {jailed_salon}")
                        self.Irc.send2socket(f":{service_id} SAJOIN {jailed_nickname} {welcome_salon}")
                        self.Irc.send2socket(f":{link} REPUTATION {jailed_IP} {self.ModConfig.reputation_score_after_release}")
                        self.User.get_User(jailed_UID).score_connexion = reputation_seuil + 1
                        self.Irc.send2socket(f":{service_id} PRIVMSG {jailed_nickname} :[{color_green} MOT DE PASS CORRECT {color_black}] : You have now the right to enjoy the network !")

                    else:
                        self.Irc.send2socket(f':{dnickname} PRIVMSG {jailed_salon} : Mauvais password')
                        self.Irc.send2socket(f":{service_id} PRIVMSG {jailed_nickname} :[{color_green} MAUVAIS PASSWORD {color_black}]")

                except IndexError:
                    self.Logs.error('_hcmd code: out of index')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} code [code]')
                except KeyError as ke:
                    self.Logs.error(f'_hcmd code: KeyError {ke}')
                    # self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} code [code]')

            case 'reputation':
                # .reputation [on/off] --> activate or deactivate reputation system
                # .reputation set banallchan [on/off] --> activate or deactivate ban in all channel
                # .reputation set limit [xxxx] --> change the reputation threshold
                # .reputation [arg1] [arg2] [arg3]
                try:
                    len_cmd = len(cmd)
                    activation = str(cmd[1]).lower()

                    # Nous sommes dans l'activation ON / OFF
                    if len_cmd == 2:
                        key = 'reputation'
                        if activation == 'on':

                            if self.ModConfig.reputation == 1:
                                self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['verte']}REPUTATION{self.Config.CONFIG_COLOR['noire']} ] : Already activated")
                                return False

                            # self.update_db_configuration('reputation', 1)
                            self.__update_configuration(key, 1)

                            self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['verte']}REPUTATION{self.Config.CONFIG_COLOR['noire']} ] : Activated by {fromuser}")
                            self.Irc.send2socket(f":{service_id} JOIN {jail_chan}")
                            self.Irc.send2socket(f":{service_id} SAMODE {jail_chan} +{dumodes} {dnickname}")
                            self.Irc.send2socket(f":{service_id} MODE {jail_chan} +{jail_chan_mode}")

                            if self.ModConfig.reputation_sg == 1:
                                for chan in self.Channel.UID_CHANNEL_DB:
                                    if chan.name != jail_chan:
                                        self.Irc.send2socket(f":{service_id} MODE {chan.name} +b ~security-group:unknown-users")
                                        self.Irc.send2socket(f":{service_id} MODE {chan.name} +eee ~security-group:webirc-users ~security-group:known-users ~security-group:websocket-users")

                            self.Base.db_query_channel('add', self.module_name, jail_chan)

                        if activation == 'off':

                            if self.ModConfig.reputation == 0:
                                self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['verte']}REPUTATION{self.Config.CONFIG_COLOR['noire']} ] : Already deactivated")
                                return False

                            self.__update_configuration(key, 0)

                            self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['rouge']}REPUTATION{self.Config.CONFIG_COLOR['noire']} ] : Deactivated by {fromuser}")
                            self.Irc.send2socket(f":{service_id} SAMODE {jail_chan} -{dumodes} {dnickname}")
                            self.Irc.send2socket(f":{service_id} MODE {jail_chan} -sS")
                            self.Irc.send2socket(f":{service_id} PART {jail_chan}")

                            for chan in self.Channel.UID_CHANNEL_DB:
                                if chan.name != jail_chan:
                                    self.Irc.send2socket(f":{service_id} MODE {chan.name} -b ~security-group:unknown-users")
                                    self.Irc.send2socket(f":{service_id} MODE {chan.name} -e ~security-group:webirc-users")
                                    self.Irc.send2socket(f":{service_id} MODE {chan.name} -e ~security-group:known-users")
                                    self.Irc.send2socket(f":{service_id} MODE {chan.name} -e ~security-group:websocket-users")

                            self.Base.db_query_channel('del', self.module_name, jail_chan)

                    if len_cmd == 4:
                        get_set = str(cmd[1]).lower()

                        if get_set != 'set':
                            raise IndexError('Showing help')

                        get_options = str(cmd[2]).lower()

                        match get_options:

                            case 'banallchan':
                                key = 'reputation_ban_all_chan'
                                get_value = str(cmd[3]).lower()
                                if get_value == 'on':

                                    if self.ModConfig.reputation_ban_all_chan == 1:
                                        self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['rouge']}BAN ON ALL CHANS{self.Config.CONFIG_COLOR['noire']} ] : Already activated")
                                        return False

                                    # self.update_db_configuration(key, 1)
                                    self.__update_configuration(key, 1)

                                    self.Irc.send2socket(f':{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR["verte"]}BAN ON ALL CHANS{self.Config.CONFIG_COLOR["noire"]} ] : Activated by {fromuser}')

                                elif get_value == 'off':
                                    if self.ModConfig.reputation_ban_all_chan == 0:
                                        self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['rouge']}BAN ON ALL CHANS{self.Config.CONFIG_COLOR['noire']} ] : Already deactivated")
                                        return False

                                    # self.update_db_configuration(key, 0)
                                    self.__update_configuration(key, 0)

                                    self.Irc.send2socket(f':{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR["verte"]}BAN ON ALL CHANS{self.Config.CONFIG_COLOR["noire"]} ] : Deactivated by {fromuser}')

                            case 'limit':
                                reputation_seuil = int(cmd[3])
                                key = 'reputation_seuil'

                                # self.update_db_configuration(key, reputation_seuil)
                                self.__update_configuration(key, reputation_seuil)

                                self.Irc.send2socket(f':{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR["verte"]}REPUTATION SEUIL{self.Config.CONFIG_COLOR["noire"]} ] : Limit set to {str(reputation_seuil)} by {fromuser}')
                                self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Reputation set to {reputation_seuil}')

                            case 'timer':
                                reputation_timer = int(cmd[3])
                                key = 'reputation_timer'
                                self.__update_configuration(key, reputation_timer)

                                self.Irc.send2socket(f':{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR["verte"]}REPUTATION TIMER{self.Config.CONFIG_COLOR["noire"]} ] : Timer set to {str(reputation_timer)} minute(s) by {fromuser}')
                                self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Reputation set to {reputation_timer}')

                            case 'score_after_release':
                                reputation_score_after_release = int(cmd[3])
                                key = 'reputation_score_after_release'
                                self.__update_configuration(key, reputation_score_after_release)

                                self.Irc.send2socket(f':{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR["verte"]}REPUTATION SCORE AFTER RELEASE{self.Config.CONFIG_COLOR["noire"]} ] : Reputation score after release set to {str(reputation_score_after_release)} by {fromuser}')
                                self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Reputation score after release set to {reputation_score_after_release}')

                            case 'security_group':
                                reputation_sg = int(cmd[3])
                                key = 'reputation_sg'
                                self.__update_configuration(key, reputation_sg)

                                self.Irc.send2socket(f':{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR["verte"]}REPUTATION SECURITY-GROUP{self.Config.CONFIG_COLOR["noire"]} ] : Reputation Security-group set to {str(reputation_sg)} by {fromuser}')
                                self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Reputation score after release set to {reputation_sg}')

                            case _:
                                self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :Right command : /msg {dnickname} reputation [ON/OFF]')
                                self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :Right command : /msg {dnickname} reputation set banallchan [ON/OFF]')
                                self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :Right command : /msg {dnickname} reputation set limit [1234]')
                                self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :Right command : /msg {dnickname} reputation set score_after_release [1234]')
                                self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :Right command : /msg {dnickname} reputation set timer [1234]')
                                self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :Right command : /msg {dnickname} reputation set action [kill|None]')

                except IndexError as ie:
                    self.Logs.warning(f'{ie}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} reputation [ON/OFF]')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} reputation set banallchan [ON/OFF]')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} reputation set limit [1234]')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} reputation set score_after_release [1234]')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} reputation set timer [1234]')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} reputation set action [kill|None]')

                except ValueError as ve:
                    self.Logs.warning(f'{ve}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : La valeur devrait etre un entier >= 0')

            case 'proxy_scan':

                # .proxy_scan set local_scan on/off          --> Va activer le scan des ports
                # .proxy_scan set psutil_scan on/off         --> Active les informations de connexion a la machine locale
                # .proxy_scan set abuseipdb_scan on/off      --> Active le scan via l'api abuseipdb
                len_cmd = len(cmd)
                color_green = self.Config.CONFIG_COLOR['verte']
                color_red = self.Config.CONFIG_COLOR['rouge']
                color_black = self.Config.CONFIG_COLOR['noire']

                if len_cmd == 4:
                    set_key = str(cmd[1]).lower()

                    if set_key != 'set':
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} proxy_scan set local_scan [ON/OFF]')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} proxy_scan set psutil_scan [ON/OFF]')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} proxy_scan set abuseipdb_scan [ON/OFF]')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} proxy_scan set freeipapi_scan [ON/OFF]')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} proxy_scan set cloudfilt_scan [ON/OFF]')

                    option = str(cmd[2]).lower() # => local_scan, psutil_scan, abuseipdb_scan
                    action = str(cmd[3]).lower() # => on / off

                    match option:
                        case 'local_scan':
                            if action == 'on':
                                if self.ModConfig.local_scan == 1:
                                    self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Already activated")
                                    return None

                                self.__update_configuration(option, 1)

                                self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Activated by {fromuser}")
                            elif action == 'off':
                                if self.ModConfig.local_scan == 0:
                                    self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Already Deactivated")
                                    return None

                                self.__update_configuration(option, 0)

                                self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Deactivated by {fromuser}")

                        case 'psutil_scan':
                            if action == 'on':
                                if self.ModConfig.psutil_scan == 1:
                                    self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Already activated")
                                    return None

                                self.__update_configuration(option, 1)

                                self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Activated by {fromuser}")
                            elif action == 'off':
                                if self.ModConfig.psutil_scan == 0:
                                    self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Already Deactivated")
                                    return None

                                self.__update_configuration(option, 0)

                                self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Deactivated by {fromuser}")

                        case 'abuseipdb_scan':
                            if action == 'on':
                                if self.ModConfig.abuseipdb_scan == 1:
                                    self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Already activated")
                                    return None

                                self.__update_configuration(option, 1)

                                self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Activated by {fromuser}")
                            elif action == 'off':
                                if self.ModConfig.abuseipdb_scan == 0:
                                    self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Already Deactivated")
                                    return None

                                self.__update_configuration(option, 0)

                                self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Deactivated by {fromuser}")

                        case 'freeipapi_scan':
                            if action == 'on':
                                if self.ModConfig.freeipapi_scan == 1:
                                    self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Already activated")
                                    return None

                                self.__update_configuration(option, 1)

                                self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Activated by {fromuser}")
                            elif action == 'off':
                                if self.ModConfig.freeipapi_scan == 0:
                                    self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Already Deactivated")
                                    return None

                                self.__update_configuration(option, 0)

                                self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Deactivated by {fromuser}")

                        case 'cloudfilt_scan':
                            if action == 'on':
                                if self.ModConfig.cloudfilt_scan == 1:
                                    self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Already activated")
                                    return None

                                self.__update_configuration(option, 1)

                                self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Activated by {fromuser}")
                            elif action == 'off':
                                if self.ModConfig.cloudfilt_scan == 0:
                                    self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Already Deactivated")
                                    return None

                                self.__update_configuration(option, 0)

                                self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Deactivated by {fromuser}")

                        case _:
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} proxy_scan set local_scan [ON/OFF]')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} proxy_scan set psutil_scan [ON/OFF]')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} proxy_scan set abuseipdb_scan [ON/OFF]')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} proxy_scan set freeipapi_scan [ON/OFF]')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} proxy_scan set cloudfilt_scan [ON/OFF]')
                else:
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} proxy_scan set local_scan [ON/OFF]')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} proxy_scan set psutil_scan [ON/OFF]')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} proxy_scan set abuseipdb_scan [ON/OFF]')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} proxy_scan set freeipapi_scan [ON/OFF]')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} proxy_scan set cloudfilt_scan [ON/OFF]')

            case 'flood':
                # .flood on/off
                # .flood set flood_message 5
                # .flood set flood_time 1
                # .flood set flood_timer 20
                try:
                    len_cmd = len(cmd)

                    if len_cmd == 2:
                        activation = str(cmd[1]).lower()
                        key = 'flood'
                        if activation == 'on':
                            if self.ModConfig.flood == 1:
                                self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['verte']}FLOOD{self.Config.CONFIG_COLOR['noire']} ] : Already activated")
                                return False

                            self.__update_configuration(key, 1)

                            self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['verte']}FLOOD{self.Config.CONFIG_COLOR['noire']} ] : Activated by {fromuser}")

                        if activation == 'off':
                            if self.ModConfig.flood == 0:
                                self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['rouge']}FLOOD{self.Config.CONFIG_COLOR['noire']} ] : Already Deactivated")
                                return False

                            self.__update_configuration(key, 0)

                            self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['verte']}FLOOD{self.Config.CONFIG_COLOR['noire']} ] : Deactivated by {fromuser}")

                    if len_cmd == 4:
                        set_key = str(cmd[2]).lower()

                        if str(cmd[1]).lower() == 'set':
                            match set_key:
                                case 'flood_message':
                                    key = 'flood_message'
                                    set_value = int(cmd[3])
                                    self.__update_configuration(key, set_value)

                                    self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['verte']}FLOOD{self.Config.CONFIG_COLOR['noire']} ] : Flood message set to {set_value} by {fromuser}")

                                case 'flood_time':
                                    key = 'flood_time'
                                    set_value = int(cmd[3])
                                    self.__update_configuration(key, set_value)

                                    self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['verte']}FLOOD{self.Config.CONFIG_COLOR['noire']} ] : Flood time set to {set_value} by {fromuser}")

                                case 'flood_timer':
                                    key = 'flood_timer'
                                    set_value = int(cmd[3])
                                    self.__update_configuration(key, set_value)

                                    self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['verte']}FLOOD{self.Config.CONFIG_COLOR['noire']} ] : Flood timer set to {set_value} by {fromuser}")

                                case _:
                                    pass

                except ValueError as ve:
                    self.Logs.error(f"{self.__class__.__name__} Value Error : {ve}")

            case 'status':
                color_green = self.Config.CONFIG_COLOR['verte']
                color_red = self.Config.CONFIG_COLOR['rouge']
                color_black = self.Config.CONFIG_COLOR['noire']
                try:
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : [{color_green if self.ModConfig.reputation == 1 else color_red}Reputation{color_black}]                           ==> {self.ModConfig.reputation}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :           reputation_seuil             ==> {self.ModConfig.reputation_seuil}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :           reputation_after_release     ==> {self.ModConfig.reputation_score_after_release}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :           reputation_ban_all_chan      ==> {self.ModConfig.reputation_ban_all_chan}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :           reputation_timer             ==> {self.ModConfig.reputation_timer}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : [Proxy_scan]')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :             {color_green if self.ModConfig.local_scan == 1 else color_red}local_scan{color_black}                 ==> {self.ModConfig.local_scan}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :             {color_green if self.ModConfig.psutil_scan == 1 else color_red}psutil_scan{color_black}                ==> {self.ModConfig.psutil_scan}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :             {color_green if self.ModConfig.abuseipdb_scan == 1 else color_red}abuseipdb_scan{color_black}             ==> {self.ModConfig.abuseipdb_scan}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :             {color_green if self.ModConfig.freeipapi_scan == 1 else color_red}freeipapi_scan{color_black}             ==> {self.ModConfig.freeipapi_scan}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :             {color_green if self.ModConfig.cloudfilt_scan == 1 else color_red}cloudfilt_scan{color_black}             ==> {self.ModConfig.cloudfilt_scan}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : [{color_green if self.ModConfig.flood == 1 else color_red}Flood{color_black}]                                ==> {self.ModConfig.flood}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :      flood_action                      ==> Coming soon')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :      flood_message                     ==> {self.ModConfig.flood_message}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :      flood_time                        ==> {self.ModConfig.flood_time}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :      flood_timer                       ==> {self.ModConfig.flood_timer}')
                except KeyError as ke:
                    self.Logs.error(f"Key Error : {ke}")

            case 'info':
                try:
                    nickoruid = cmd[1]
                    UserObject = self.User.get_User(nickoruid)

                    if not UserObject is None:
                        channels: list = []
                        for chan in self.Channel.UID_CHANNEL_DB:
                            for uid_in_chan in chan.uids:
                                if self.Base.clean_uid(uid_in_chan) == UserObject.uid:
                                    channels.append(chan.name)

                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : UID              : {UserObject.uid}')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : NICKNAME         : {UserObject.nickname}')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : USERNAME         : {UserObject.username}')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : REALNAME         : {UserObject.realname}')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : HOSTNAME         : {UserObject.hostname}')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : VHOST            : {UserObject.vhost}')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : IP               : {UserObject.remote_ip}')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Country          : {UserObject.geoip}')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : WebIrc           : {UserObject.isWebirc}')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : WebWebsocket     : {UserObject.isWebsocket}')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : REPUTATION       : {UserObject.score_connexion}')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : MODES            : {UserObject.umodes}')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : CHANNELS         : {channels}')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : CONNECTION TIME  : {UserObject.connexion_datetime}')
                    else:
                        self.Irc.send2socket(f":{dnickname} NOTICE {fromuser} : This user {nickoruid} doesn't exist")

                except KeyError as ke:
                    self.Logs.warning(f"Key error info user : {ke}")

            case 'sentinel':
                # .sentinel on
                activation = str(cmd[1]).lower()
                service_id = self.Config.SERVICE_ID

                channel_to_dont_quit = [self.Config.SALON_JAIL, self.Config.SERVICE_CHANLOG]

                if activation == 'on':
                    for chan in self.Channel.UID_CHANNEL_DB:
                        if not chan.name in channel_to_dont_quit:
                            self.Irc.send2socket(f":{service_id} JOIN {chan.name}")
                if activation == 'off':
                    for chan in self.Channel.UID_CHANNEL_DB:
                        if not chan.name in channel_to_dont_quit:
                            self.Irc.send2socket(f":{service_id} PART {chan.name}")
                    self.join_saved_channels()
