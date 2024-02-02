from datetime import datetime
import re, socket, psutil, requests, json
from core.irc import Irc

#   Le module crée devra réspecter quelques conditions
#       1. Le nom de la classe devra toujours s'appeler comme le module. Exemple => nom de class Defender | nom du module mod_defender
#       2. la methode __init__ devra toujours avoir les parametres suivant (self, irc:object)
#           1 . Créer la variable Irc dans le module
#           2 . Récuperer la configuration dans une variable
#           3 . Définir et enregistrer les nouvelles commandes
#           4 . Créer vos tables, en utilisant toujours le nom des votre classe en minuscule ==> defender_votre-table
#       3. une methode _hcmds(self, user:str, cmd: list) devra toujours etre crée.

class Defender():

    def __init__(self, ircInstance:Irc) -> None:

        self.Irc = ircInstance                                              # Ajouter l'object mod_irc a la classe ( Obligatoire )
        self.Config = ircInstance.Config                                    # Ajouter la configuration a la classe ( Obligatoire )
        self.Base = ircInstance.Base                                        # Ajouter l'objet Base au module ( Obligatoire )

        self.Irc.debug(f'Module {self.__class__.__name__} loaded ...')

        # Créer les nouvelles commandes du module
        self.commands_level = {
            0: ['code'],
            1: ['join','part', 'info'],
            2: ['q', 'dq', 'o', 'do', 'h', 'dh', 'v', 'dv', 'b', 'ub','k', 'kb'],
            3: ['reputation','proxy_scan', 'flood', 'status', 'timer','show_reputation', 'show_users']
        }
        self.__set_commands(self.commands_level)                            # Enrigstrer les nouvelles commandes dans le code

        self.__create_tables()                                              # Créer les tables necessaire a votre module (ce n'es pas obligatoire)

        self.init_defender()                                                # Créer une methode init ( ce n'es pas obligatoire )

    def __set_commands(self, commands:dict) -> None:
        """### Rajoute les commandes du module au programme principal

        Args:
            commands (list): Liste des commandes du module

        Returns:
            None: Aucun retour attendu
        """
        for level, com in commands.items():
            for c in commands[level]:
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

        self.Base.db_execute_query(table_channel)
        self.Base.db_execute_query(table_config)
        self.Base.db_execute_query(table_trusted)
        return None

    def init_defender(self) -> bool:

        self.db_reputation = {}                                                                                 # Definir la variable qui contiendra la liste des user concerné par la réputation
        self.flood_system = {}                                                                                  # Variable qui va contenir les users
        self.reputation_first_connexion = {'ip': '', 'score': -1}                                               # Contient les premieres informations de connexion
        self.abuseipdb_key = '13c34603fee4d2941a2c443cc5c77fd750757ca2a2c1b304bd0f418aff80c24be12651d1a3cfe674' # Laisser vide si aucune clé

        # Rejoindre les salons
        self.join_saved_channels()

        # Variable qui va contenir les options de configuration du module Defender
        self.defConfig = {
            'reputation': 0,
            'reputation_timer': 0,
            'reputation_seuil': 600,
            'reputation_ban_all_chan': 0,
            'local_scan': 0,
            'psutil_scan': 0,
            'abuseipdb_scan': 0,
            'flood': 0,
            'flood_message': 5,
            'flood_time': 1,
            'flood_timer': 20
        }

        # Syncrhoniser la variable defConfig avec la configuration de la base de données.
        self.sync_db_configuration()

        return True

    def sync_db_configuration(self) -> None:

        query = "SELECT parameter, value FROM def_config"
        response = self.Base.db_execute_query(query)

        result = response.fetchall()

        # Si le resultat ne contient aucune valeur
        if not result:
            # Base de données vide Inserer la premiere configuration
            for param, value in self.defConfig.items():
                mes_donnees = {'datetime': self.Base.get_datetime(), 'parameter': param, 'value': value}
                insert = self.Base.db_execute_query('INSERT INTO def_config (datetime, parameter, value) VALUES (:datetime, :parameter, :value)', mes_donnees)
                insert_rows = insert.rowcount
                if insert_rows > 0:
                    self.Irc.debug(f'Row affected into def_config : {insert_rows}')

        # Inserer une nouvelle configuration
        for param, value in self.defConfig.items():
            mes_donnees = {'parameter': param}
            search_param_query = "SELECT parameter, value FROM def_config WHERE parameter = :parameter"
            result = self.Base.db_execute_query(search_param_query, mes_donnees)
            isParamExist = result.fetchone()

            if isParamExist is None:
                mes_donnees = {'datetime': self.Base.get_datetime(), 'parameter': param, 'value': value}
                insert = self.Base.db_execute_query('INSERT INTO def_config (datetime, parameter, value) VALUES (:datetime, :parameter, :value)', mes_donnees)
                insert_rows = insert.rowcount
                if insert_rows > 0:
                    self.Irc.debug(f'DB_Def_config - new param included : {insert_rows}')

        # Supprimer un parameter si il n'existe plus dans la variable global
        query = "SELECT parameter FROM def_config"
        response = self.Base.db_execute_query(query)
        dbresult = response.fetchall()

        for dbparam in dbresult:
            if not dbparam[0] in self.defConfig:
                mes_donnees = {'parameter': dbparam[0]}
                delete = self.Base.db_execute_query('DELETE FROM def_config WHERE parameter = :parameter', mes_donnees)
                row_affected = delete.rowcount
                if row_affected > 0:
                    self.Irc.debug(f'DB_Def_config - param [{dbparam[0]}] has been deleted')

        # Synchroniser la base de données avec la variable global
        query = "SELECT parameter, value FROM def_config"
        response = self.Base.db_execute_query(query)
        result = response.fetchall()

        for param, value in result:
            self.defConfig[param] = self.Base.int_if_possible(value)

        self.Irc.debug(self.defConfig)
        return None

    def update_db_configuration(self, param:str, value:str) -> None:

        if not param in self.defConfig:
            self.Irc.debug(f"Le parametre {param} n'existe pas dans la variable global")
            return None

        mes_donnees = {'parameter': param}
        search_param_query = "SELECT parameter, value FROM def_config WHERE parameter = :parameter"
        result = self.Base.db_execute_query(search_param_query, mes_donnees)
        isParamExist = result.fetchone()

        if not isParamExist is None:
            mes_donnees = {'datetime': self.Base.get_datetime(), 'parameter': param, 'value': value}
            update = self.Base.db_execute_query('UPDATE def_config SET datetime = :datetime, value = :value WHERE parameter = :parameter', mes_donnees)
            updated_rows = update.rowcount
            if updated_rows > 0:
                self.defConfig[param] = self.Base.int_if_possible(value)
                self.Irc.debug(f'DB_Def_config - new param updated : {param} {value}')

        self.Irc.debug(self.defConfig)
        
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

    def insert_db_reputation(self, uid:str, ip:str, nickname:str, username:str, hostname:str, umodes:str, vhost:str, score:int, isWebirc:bool) -> None:

        currentDateTime = self.Base.get_datetime()
        secret_code = self.Base.get_random(8)
        # Vérifier si le uid existe déja
        if uid in self.db_reputation:
            return None

        self.db_reputation[uid] = {
            'nickname': nickname,
            'username': username,
            'hostname': hostname,
            'umodes': umodes,
            'vhost': vhost,
            'ip': ip,
            'score': score,
            'isWebirc': isWebirc,
            'secret_code': secret_code,
            'connected_datetime': currentDateTime,
            'updated_datetime': currentDateTime
        }

        return None

    def update_db_reputation(self, uidornickname:str, newnickname:str) -> None:
        
        uid = self.Irc.get_uid(uidornickname)
        currentDateTime = self.Base.get_datetime()
        secret_code = self.Base.get_random(8)

        if not uid in self.Irc.db_uid:
            self.Irc.debug(f'Etrange UID {uid}')
            return None

        if uid in self.db_reputation:
            self.db_reputation[uid]['nickname'] = newnickname
            self.db_reputation[uid]['updated_datetime'] = currentDateTime
            self.db_reputation[uid]['secret_code'] = secret_code
        else:
            self.Irc.debug(f"L'UID {uid} n'existe pas dans REPUTATION_DB")

        return None

    def delete_db_reputation(self, uid:str) -> None:
        """Cette fonction va supprimer le UID du dictionnaire self.db_reputation

        Args:
            uid (str): le uid ou le nickname du user
        """

        # Si le UID existe dans le dictionnaire alors le supprimer
        if uid in self.db_reputation:
            # Si le nickname existe dans le dictionnaire alors le supprimer
            del self.db_reputation[uid]
            self.Irc.debug(f"Le UID {uid} a été supprimé du REPUTATION_DB")

    def insert_db_trusted(self, uid: str, nickname:str) -> None:

        uid = self.Irc.get_uid(uid)
        nickname = self.Irc.get_nickname(nickname)

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

        get_uid = self.Irc.get_uid(uidornickname)
        
        if not get_uid in self.Irc.db_uid:
            return 0

        # Convertir la date enregistrée dans UID_DB en un objet {datetime}
        connected_time_string = self.Irc.db_uid[get_uid]['datetime']
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

    def system_reputation(self, uid:str)->None:
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

            if not uid in self.db_reputation:
                return False

            code = self.db_reputation[uid]['secret_code']
            salon_logs = self.Config.SERVICE_CHANLOG
            salon_jail = self.Config.SALON_JAIL
            jailed_nickname = self.db_reputation[uid]['nickname']
            jailed_score = self.db_reputation[uid]['score']

            color_red = self.Config.CONFIG_COLOR['rouge']
            color_black = self.Config.CONFIG_COLOR['noire']
            color_bold = self.Config.CONFIG_COLOR['gras']
            service_id = self.Config.SERVICE_ID
            service_prefix = self.Config.SERVICE_PREFIX
            reputation_ban_all_chan = self.Base.int_if_possible(self.defConfig['reputation_ban_all_chan'])

            if not self.db_reputation[uid]['isWebirc']:
                # Si le user ne vient pas de webIrc

                self.Irc.send2socket(f":{service_id} SAJOIN {jailed_nickname} {salon_jail}")
                self.Irc.send2socket(f":{service_id} PRIVMSG {salon_logs} :[{color_red} REPUTATION {color_black}] : Connexion de {jailed_nickname} ({jailed_score}) ==> {salon_jail}")
                self.Irc.send2socket(f":{service_id} NOTICE {jailed_nickname} :[{color_red} {jailed_nickname} {color_black}] : Merci de tapez la commande suivante {color_bold}{service_prefix}code {code}{color_bold}")
                if reputation_ban_all_chan == 1:
                    for chan in self.Irc.db_chan:
                        if chan != salon_jail:
                            self.Irc.send2socket(f":{service_id} MODE {chan} +b {jailed_nickname}!*@*")
                            self.Irc.send2socket(f":{service_id} KICK {chan} {jailed_nickname}")
                
                self.Irc.debug(f"system_reputation : {jailed_nickname} à été capturé par le système de réputation")
                # self.Irc.create_ping_timer(int(self.defConfig['reputation_timer']) * 60, 'Defender', 'system_reputation_timer')
                self.Base.create_timer(int(self.defConfig['reputation_timer']) * 60, self.system_reputation_timer)
            else:
                self.Irc.debug(f"system_reputation : {jailed_nickname} à été supprimé du système de réputation car connecté via WebIrc ou il est dans la 'Trusted list'")
                self.delete_db_reputation(uid)

        except IndexError as e:
            self.Irc.debug(f"system_reputation : {str(e)}")

    def system_reputation_timer(self) -> None:
        try:
            reputation_flag = int(self.defConfig['reputation'])
            reputation_timer = int(self.defConfig['reputation_timer'])
            reputation_seuil = self.defConfig['reputation_seuil']
            service_id = self.Config.SERVICE_ID
            dchanlog = self.Config.SERVICE_CHANLOG
            color_red = self.Config.CONFIG_COLOR['rouge']
            color_black = self.Config.CONFIG_COLOR['noire']
            salon_jail = self.Config.SALON_JAIL

            if reputation_flag == 0:
                return None
            elif reputation_timer == 0:
                return None

            # self.Irc.debug(self.db_reputation)
            uid_to_clean = []

            for uid in self.db_reputation:
                if not self.db_reputation[uid]['isWebirc']: # Si il ne vient pas de WebIRC
                    self.Irc.debug(f"Nickname: {self.db_reputation[uid]['nickname']} | uptime: {self.get_user_uptime_in_minutes(uid)} | reputation time: {reputation_timer}")
                    if self.get_user_uptime_in_minutes(uid) >= reputation_timer and int(self.db_reputation[uid]['score']) <= int(reputation_seuil):
                        self.Irc.send2socket(f":{service_id} PRIVMSG {dchanlog} :[{color_red} REPUTATION {color_black}] : Action sur {self.db_reputation[uid]['nickname']} aprés {str(reputation_timer)} minutes d'inactivité")
                        # if not system_reputation_timer_action(cglobal['reputation_timer_action'], uid, self.db_reputation[uid]['nickname']):
                        #     return False
                        self.Irc.send2socket(f":{service_id} KILL {self.db_reputation[uid]['nickname']} After {str(reputation_timer)} minutes of inactivity you should reconnect and type the password code ")

                        self.Irc.debug(f"Action sur {self.db_reputation[uid]['nickname']} aprés {str(reputation_timer)} minutes d'inactivité")
                        uid_to_clean.append(uid)

            for uid in uid_to_clean:
                # Suppression des éléments dans {UID_DB} et {REPUTATION_DB}
                for chan in self.Irc.db_chan:
                    if chan != salon_jail:
                        self.Irc.send2socket(f":{service_id} MODE {chan} -b {self.db_reputation[uid]['nickname']}!*@*")

                # Lorsqu'un utilisateur quitte, il doit être supprimé de {UID_DB}.
                self.Irc.delete_db_uid(uid)
                self.delete_db_reputation(uid)

        except AssertionError as ae:
            self.Irc.debug(f'Assertion Error -> {ae}')

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

        if self.defConfig['flood'] == 0:
            return None

        if not '#' in channel:
            return None

        flood_time = self.defConfig['flood_time']
        flood_message = self.defConfig['flood_message']
        flood_timer = self.defConfig['flood_timer']
        service_id = self.Config.SERVICE_ID
        dnickname = self.Config.SERVICE_NICKNAME
        color_red = self.Config.CONFIG_COLOR['rouge']
        color_bold = self.Config.CONFIG_COLOR['gras']
        
        get_detected_uid = self.Irc.get_uid(detected_user)
        get_detected_nickname = self.Irc.get_nickname(detected_user)
        
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
            self.Irc.debug('system de flood detecté')
            self.Irc.send2socket(f':{dnickname} PRIVMSG {channel} : {color_red} {color_bold} Flood detected. Apply the +m mode (Ô_o)')
            self.Irc.send2socket(f":{service_id} MODE {channel} +m")
            self.Irc.debug(f'FLOOD Détecté sur {get_detected_nickname} mode +m appliqué sur le salon {channel}')
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

    def scan_ports(self, remote_ip: str) -> None:

        for port in self.Config.PORTS_TO_SCAN:
            newSocket = ''
            newSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            newSocket.settimeout(0.5)
            try:
                connection = (remote_ip, self.Base.int_if_possible(port))
                newSocket.connect(connection)
                self.Irc.send2socket(f":{self.Config.SERVICE_NICKNAME} PRIVMSG {self.Config.SERVICE_CHANLOG} :[ {self.Config.CONFIG_COLOR['rouge']}PROXY_SCAN{self.Config.CONFIG_COLOR['noire']} ] :     Port [{str(port)}] ouvert sur l'adresse ip [{remote_ip}]")
                # print(f"=======> Le port {str(port)} est ouvert !!")
                self.Base.running_sockets.append(newSocket)
                # print(newSocket)
                newSocket.shutdown(socket.SHUT_RDWR)
                newSocket.close()
            except (socket.timeout, ConnectionRefusedError):
                self.Irc.debug(f"Le port {str(port)} est fermé")
            except AttributeError as ae:
                self.Irc.debug(f"AttributeError : {ae}")
            finally:
                # newSocket.shutdown(socket.SHUT_RDWR)
                newSocket.close()
                self.Irc.debug('=======> Fermeture de la socket')
        
        pass

    def get_ports_connexion(self, remote_ip: str) -> list[int]:
        connections = psutil.net_connections(kind='inet')

        matching_ports = [conn.raddr.port for conn in connections if conn.raddr and conn.raddr.ip == remote_ip]
        self.Irc.debug(f"Connexion of {remote_ip} using ports : {str(matching_ports)}")

        return matching_ports

    def abuseipdb_scan(self, remote_ip:str) -> dict[str, any] | None:
        """Analyse l'ip avec AbuseIpDB
           Cette methode devra etre lancer toujours via un thread ou un timer.
        Args:
            remote_ip (_type_): l'ip a analyser

        Returns:
            dict[str, any] | None: les informations du provider
            keys : 'score', 'country', 'isTor', 'totalReports'
        """
        if self.defConfig['abuseipdb_scan'] == 0:
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

        response = requests.request(method='GET', url=url, headers=headers, params=querystring)

        # Formatted output
        decodedResponse = json.loads(response.text)
        try:
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

            self.Irc.send2socket(f":{service_id} PRIVMSG {service_chanlog} :[ {color_red}ABUSEIPDB_SCAN{color_black} ] : Connexion de {remote_ip} Score: {str(result['score'])} | Country : {result['country']} | Tor : {str(result['isTor'])} | Total Reports : {str(result['totalReports'])}")

            response.close()

            return result
        except KeyError as ke:
            self.Irc.debug(f"AbuseIpDb KeyError : {ke}")

    def cmd(self, data:list) -> None:

        service_id = self.Config.SERVICE_ID                 # Defender serveur id
        cmd = list(data).copy()

        if len(cmd) < 2:
            return None

        match cmd[1]:

            case 'REPUTATION':
                # :001 REPUTATION 91.168.141.239 118
                try:
                    self.reputation_first_connexion['ip'] = cmd[2]
                    self.reputation_first_connexion['score'] = cmd[3]

                    # self.Base.scan_ports(cmd[2])
                    if self.defConfig['local_scan'] == 1:
                        self.Base.create_thread(self.scan_ports, (cmd[2], ))

                    if self.defConfig['psutil_scan'] == 1:
                        self.Base.create_thread(self.get_ports_connexion, (cmd[2], ))

                    if self.defConfig['abuseipdb_scan'] == 1:
                        self.Base.create_thread(self.abuseipdb_scan, (cmd[2], ))
                    # Possibilité de déclancher les bans a ce niveau.
                except IndexError:
                    self.Irc.debug(f'cmd reputation: index error')

        match cmd[2]:

            case 'PRIVMSG':
                cmd.pop(0)
                user_trigger = str(cmd[0]).replace(':','')
                channel = cmd[2]
                find_nickname = self.Irc.get_nickname(user_trigger)
                self.flood(find_nickname, channel)

            case 'UID':

                if self.Irc.INIT == 1:
                    return None

                if 'webirc' in cmd[0]:
                    isWebirc = True
                else:
                    isWebirc = False

                # Supprimer la premiere valeur et finir le code normalement
                cmd.pop(0)

                uid = str(cmd[7])
                nickname = str(cmd[2])
                username = str(cmd[5])
                hostname = str(cmd[6])
                umodes = str(cmd[9])
                vhost = str(cmd[10])

                reputation_flag = self.Base.int_if_possible(self.defConfig['reputation'])
                reputation_seuil = self.Base.int_if_possible(self.defConfig['reputation_seuil'])

                if self.Irc.INIT == 0:
                    # A chaque nouvelle connexion chargé les données dans reputation
                    client_ip = ''
                    client_score = 0
                    if 'ip' in self.reputation_first_connexion:
                        client_ip = self.reputation_first_connexion['ip']
                    if 'score' in self.reputation_first_connexion:
                        client_score = self.reputation_first_connexion['score']

                    # Si réputation activé lancer un whois sur le nickname connecté
                    # Si le user n'es pas un service ni un IrcOP alors whois
                    if not re.match(fr'^.*[S|o?].*$', umodes):
                        if reputation_flag == 1 and int(client_score) <= int(reputation_seuil):
                            # if not db_isTrusted_user(user_id):
                            self.insert_db_reputation(uid, client_ip, nickname, username, hostname, umodes, vhost, client_score, isWebirc)
                            # self.Irc.send2socket(f":{service_id} WHOIS {nickname}")
                            if uid in self.db_reputation:
                                if reputation_flag == 1 and int(client_score) <= int(reputation_seuil):
                                    self.system_reputation(uid)
                                    self.Irc.debug('Démarrer le systeme de reputation')

            case 'SJOIN':
                # ['@msgid=F9B7JeHL5pj9nN57cJ5pEr;time=2023-12-28T20:47:24.305Z', ':001', 'SJOIN', '1702138958', '#welcome', ':0015L1AHL']
                try:
                    cmd.pop(0)
                    parsed_chan = cmd[3]
                    self.Irc.insert_db_chan(parsed_chan)

                    if self.defConfig['reputation'] == 1:
                        parsed_UID = cmd[4]
                        pattern = fr'^:[@|%|\+|~|\*]*'
                        parsed_UID = re.sub(pattern, '', parsed_UID)
                        if parsed_UID in self.db_reputation:
                            # print(f"====> {str(self.db_reputation)}")
                            isWebirc = self.db_reputation[parsed_UID]['isWebirc']
                            if self.defConfig['reputation_ban_all_chan'] == 1 and not isWebirc:
                                if parsed_chan != self.Config.SALON_JAIL:
                                    self.Irc.send2socket(f":{service_id} MODE {parsed_chan} +b {self.db_reputation[parsed_UID]['nickname']}!*@*")
                                    self.Irc.send2socket(f":{service_id} KICK {parsed_chan} {self.db_reputation[parsed_UID]['nickname']}")

                        self.Irc.debug(f'SJOIN parsed_uid : {parsed_UID}')
                except KeyError as ke:
                    self.Irc.debug(f"key error SJOIN : {ke}")

            case 'SLOG':
                # self.Base.scan_ports(cmd[7])
                cmd.pop(0)
                if self.defConfig['local_scan'] == 1:
                    self.Base.create_thread(self.scan_ports, (cmd[7], ))

                if self.defConfig['psutil_scan'] == 1:
                    self.Base.create_thread(self.get_ports_connexion, (cmd[7], ))

                if self.defConfig['abuseipdb_scan'] == 1:
                    self.Base.create_thread(self.abuseipdb_scan, (cmd[7], ))

            case 'NICK':
                # :0010BS24L NICK [NEWNICK] 1697917711
                # Changement de nickname
                cmd.pop(0)
                uid = str(cmd[0]).replace(':','')
                oldnick = self.db_reputation[uid]['nickname']
                newnickname = cmd[2]
                
                jail_salon = self.Config.SALON_JAIL
                service_id = self.Config.SERVICE_ID

                self.update_db_reputation(uid, newnickname)

                if uid in self.db_reputation:
                    for chan in self.Irc.db_chan:
                        if chan != jail_salon:
                            self.Irc.send2socket(f":{service_id} MODE {chan} -b {oldnick}!*@*")
                            self.Irc.send2socket(f":{service_id} MODE {chan} +b {newnickname}!*@*")

            case 'QUIT':
                # :001N1WD7L QUIT :Quit: free_znc_1
                cmd.pop(0)
                user_id = str(cmd[0]).replace(':','')
                final_UID = user_id

                jail_salon = self.Config.SALON_JAIL
                service_id = self.Config.SERVICE_ID

                if final_UID in self.db_reputation:
                    final_nickname = self.db_reputation[user_id]['nickname']
                    for chan in self.Irc.db_chan:
                        if chan != jail_salon:
                            self.Irc.send2socket(f":{service_id} MODE {chan} -b {final_nickname}!*@*")
                    self.delete_db_reputation(final_UID)

    def _hcmds(self, user:str, cmd: list) -> None:

        command = str(cmd[0]).lower()
        fromuser = user

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
                    # self.Irc.create_ping_timer(timer_sent, 'Defender', 'run_db_action_timer')
                    self.Base.create_timer(timer_sent, self.run_db_action_timer)
                    # self.Base.create_timer(timer_sent, self.Base.garbage_collector_sockets)

                except TypeError as te:
                    self.Irc.debug(f"Type Error -> {te}")
                except ValueError as ve:
                    self.Irc.debug(f"Value Error -> {ve}")

            case 'show_reputation':

                if not self.db_reputation:
                    self.Irc.send2socket(f':{dnickname} PRIVMSG {dchanlog} : No one is suspected')

                for uid, nickname in self.db_reputation.items():
                    self.Irc.send2socket(f':{dnickname} PRIVMSG {dchanlog} : Uid: {uid} | Nickname: {self.db_reputation[uid]["nickname"]} | Connected on: {self.db_reputation[uid]["connected_datetime"]} | Updated on: {self.db_reputation[uid]["updated_datetime"]}')

            case 'code':
                try:
                    release_code = cmd[1]
                    jailed_nickname = self.Irc.get_nickname(fromuser)
                    jailed_UID = self.Irc.get_uid(fromuser)
                    if not jailed_UID in self.db_reputation:
                        self.Irc.send2socket(f":{dnickname} NOTICE {fromuser} : No code is requested ...")
                        return False

                    jailed_IP = self.db_reputation[jailed_UID]['ip']
                    jailed_salon = self.Config.SALON_JAIL
                    reputation_seuil = self.defConfig['reputation_seuil']
                    welcome_salon = self.Config.SALON_LIBERER
                    
                    self.Irc.debug(f"IP de {jailed_nickname} : {jailed_IP}")
                    link = self.Config.SERVEUR_LINK
                    color_green = self.Config.CONFIG_COLOR['verte']
                    color_black = self.Config.CONFIG_COLOR['noire']
                    

                    if jailed_UID in self.db_reputation:
                        if release_code == self.db_reputation[jailed_UID]['secret_code']:
                            self.Irc.send2socket(f':{dnickname} PRIVMSG {jailed_salon} : Bon mot de passe. Allez du vent !')

                            if self.defConfig['reputation_ban_all_chan'] == 1:
                                for chan in self.Irc.db_chan:
                                    if chan != jailed_salon:
                                        self.Irc.send2socket(f":{service_id} MODE {chan} -b {jailed_nickname}!*@*")

                            del self.db_reputation[jailed_UID]
                            self.Irc.debug(f'{jailed_UID} - {jailed_nickname} removed from REPUTATION_DB')
                            self.Irc.send2socket(f":{service_id} SAPART {jailed_nickname} {jailed_salon}")
                            self.Irc.send2socket(f":{service_id} SAJOIN {jailed_nickname} {welcome_salon}")
                            self.Irc.send2socket(f":{link} REPUTATION {jailed_IP} {int(reputation_seuil) + 1}")
                            self.Irc.send2socket(f":{service_id} PRIVMSG {jailed_nickname} :[{color_green} MOT DE PASS CORRECT {color_black}] : You have now the right to enjoy the network !")

                        else:
                            self.Irc.send2socket(f':{dnickname} PRIVMSG {jailed_salon} : Mauvais password')
                            self.Irc.send2socket(f":{service_id} PRIVMSG {jailed_nickname} :[{color_green} MAUVAIS PASSWORD {color_black}]")
                    else:
                        self.Irc.send2socket(f":{dnickname} PRIVMSG {jailed_salon} : Ce n'est pas à toi de taper le mot de passe !")
                    
                except IndexError:
                    self.Irc.debug('_hcmd code: out of index')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} code [code]')
                except KeyError as ke:
                    self.Irc.debug(f'_hcmd code: KeyError {ke}')
                    # self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} code [code]')
                pass


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

                            if self.defConfig[key] == 1:
                                self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['verte']}REPUTATION{self.Config.CONFIG_COLOR['noire']} ] : Already activated")
                                return False

                            self.update_db_configuration('reputation', 1)
                            self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['verte']}REPUTATION{self.Config.CONFIG_COLOR['noire']} ] : Activated by {fromuser}")
                            self.Irc.send2socket(f":{service_id} JOIN {jail_chan}")
                            self.Irc.send2socket(f":{service_id} SAMODE {jail_chan} +{dumodes} {dnickname}")
                            self.Irc.send2socket(f":{service_id} MODE {jail_chan} +{jail_chan_mode}")
                            self.add_defender_channel(jail_chan)

                        if activation == 'off':

                            if self.defConfig[key] == 0:
                                self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['verte']}REPUTATION{self.Config.CONFIG_COLOR['noire']} ] : Already deactivated")
                                return False

                            self.update_db_configuration('reputation', 0)
                            self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['rouge']}REPUTATION{self.Config.CONFIG_COLOR['noire']} ] : Deactivated by {fromuser}")
                            self.Irc.send2socket(f":{service_id} SAMODE {jail_chan} -{dumodes} {dnickname}")
                            self.Irc.send2socket(f":{service_id} MODE {jail_chan} -sS")
                            self.Irc.send2socket(f":{service_id} PART {jail_chan}")
                            self.delete_defender_channel(jail_chan)

                    if len_cmd == 4:
                        get_set = str(cmd[1]).lower()
                        
                        if get_set != 'set':
                            return False

                        get_options = str(cmd[2]).lower()

                        match get_options:
                            case 'banallchan':
                                key = 'reputation_ban_all_chan'
                                get_value = str(cmd[3]).lower()
                                if get_value == 'on':

                                    if self.defConfig[key] == 1:
                                        self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['rouge']}BAN ON ALL CHANS{self.Config.CONFIG_COLOR['noire']} ] : Already activated")
                                        return False

                                    self.update_db_configuration(key, 1)
                                    self.Irc.send2socket(f':{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR["verte"]}BAN ON ALL CHANS{self.Config.CONFIG_COLOR["noire"]} ] : Activated by {fromuser}')

                                elif get_value == 'off':
                                    print(get_value)
                                    if self.defConfig[key] == 0:
                                        self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['rouge']}BAN ON ALL CHANS{self.Config.CONFIG_COLOR['noire']} ] : Already deactivated")
                                        return False

                                    self.update_db_configuration(key, 0)
                                    self.Irc.send2socket(f':{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR["verte"]}BAN ON ALL CHANS{self.Config.CONFIG_COLOR["noire"]} ] : Deactivated by {fromuser}')
                            case 'limit':
                                reputation_seuil = int(cmd[3])
                                key = 'reputation_seuil'
                                self.update_db_configuration(key, reputation_seuil)

                                self.Irc.send2socket(f':{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR["verte"]}REPUTATION SEUIL{self.Config.CONFIG_COLOR["noire"]} ] : Limit set to {str(reputation_seuil)} by {fromuser}')
                                self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Reputation set to {reputation_seuil}')

                            case 'timer':
                                reputation_timer = int(cmd[3])
                                key = 'reputation_timer'
                                self.update_db_configuration(key, reputation_timer)
                                self.Irc.send2socket(f':{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR["verte"]}REPUTATION TIMER{self.Config.CONFIG_COLOR["noire"]} ] : Timer set to {str(reputation_timer)} minute(s) by {fromuser}')
                                self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Reputation set to {reputation_timer}')

                            case _:
                                pass

                except IndexError:
                    self.Irc.debug('_hcmd reputation: out of index')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} reputation [ON/OFF]')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} reputation set banallchan [ON/OFF]')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} reputation set limit [1234]')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} reputation set timer [1234]')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} reputation set action [kill|None]')

                except ValueError:
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

                    option = str(cmd[2]).lower() # => local_scan, psutil_scan, abuseipdb_scan
                    action = str(cmd[3]).lower() # => on / off

                    match option:
                        case 'local_scan':
                            if action == 'on':
                                if self.defConfig[option] == 1:
                                    self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Already activated")
                                    return None
                                self.update_db_configuration(option, 1)
                                self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Activated by {fromuser}")
                            elif action == 'off':
                                if self.defConfig[option] == 0:
                                    self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Already Deactivated")
                                    return None
                                self.update_db_configuration(option, 0)
                                self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Deactivated by {fromuser}")

                        case 'psutil_scan':
                            if action == 'on':
                                if self.defConfig[option] == 1:
                                    self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Already activated")
                                    return None
                                self.update_db_configuration(option, 1)
                                self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Activated by {fromuser}")
                            elif action == 'off':
                                if self.defConfig[option] == 0:
                                    self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Already Deactivated")
                                    return None
                                self.update_db_configuration(option, 0)
                                self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Deactivated by {fromuser}")

                        case 'abuseipdb_scan':
                            if action == 'on':
                                if self.defConfig[option] == 1:
                                    self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Already activated")
                                    return None
                                self.update_db_configuration(option, 1)
                                self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Activated by {fromuser}")
                            elif action == 'off':
                                if self.defConfig[option] == 0:
                                    self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Already Deactivated")
                                    return None
                                self.update_db_configuration(option, 0)
                                self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Deactivated by {fromuser}")

                        case _:
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} proxy_scan set local_scan [ON/OFF]')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} proxy_scan set psutil_scan [ON/OFF]')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} proxy_scan set abuseipdb_scan [ON/OFF]')
                else:
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} proxy_scan set local_scan [ON/OFF]')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} proxy_scan set psutil_scan [ON/OFF]')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} proxy_scan set abuseipdb_scan [ON/OFF]')

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
                            if self.defConfig[key] == 1:
                                self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['verte']}FLOOD{self.Config.CONFIG_COLOR['noire']} ] : Already activated")
                                return False

                            self.update_db_configuration(key, 1)
                            self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['verte']}FLOOD{self.Config.CONFIG_COLOR['noire']} ] : Activated by {fromuser}")

                        if activation == 'off':
                            if self.defConfig[key] == 0:
                                self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['rouge']}FLOOD{self.Config.CONFIG_COLOR['noire']} ] : Already Deactivated")
                                return False

                            self.update_db_configuration(key, 0)
                            self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['verte']}FLOOD{self.Config.CONFIG_COLOR['noire']} ] : Deactivated by {fromuser}")

                    if len_cmd == 4:
                        set_key = str(cmd[2]).lower()

                        if str(cmd[1]).lower() == 'set':
                            match set_key:
                                case 'flood_message':
                                    key = 'flood_message'
                                    set_value = int(cmd[3])
                                    print(f"{str(set_value)} - {set_key}")
                                    self.update_db_configuration(key, set_value)
                                    self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['verte']}FLOOD{self.Config.CONFIG_COLOR['noire']} ] : Flood message set to {set_value} by {fromuser}")

                                case 'flood_time':
                                    key = 'flood_time'
                                    set_value = int(cmd[3])
                                    self.update_db_configuration(key, set_value)
                                    self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['verte']}FLOOD{self.Config.CONFIG_COLOR['noire']} ] : Flood time set to {set_value} by {fromuser}")

                                case 'flood_timer':
                                    key = 'flood_timer'
                                    set_value = int(cmd[3])
                                    self.update_db_configuration(key, set_value)
                                    self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['verte']}FLOOD{self.Config.CONFIG_COLOR['noire']} ] : Flood timer set to {set_value} by {fromuser}")

                                case _:
                                    pass

                except ValueError as ve:
                    self.Irc.debug(f"{self.__class__.__name__} Value Error : {ve}")

            case 'status':
                color_green = self.Config.CONFIG_COLOR['verte']
                color_red = self.Config.CONFIG_COLOR['rouge']
                color_black = self.Config.CONFIG_COLOR['noire']
                try:
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : [{color_green if self.defConfig["reputation"] == 1 else color_red}Reputation{color_black}]                           ==> {self.defConfig["reputation"]}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :           reputation_seuil             ==> {self.defConfig["reputation_seuil"]}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :           reputation_ban_all_chan      ==> {self.defConfig["reputation_ban_all_chan"]}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :           reputation_timer             ==> {self.defConfig["reputation_timer"]}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : [Proxy_scan]')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :             {color_green if self.defConfig["local_scan"] == 1 else color_red}local_scan{color_black}                 ==> {self.defConfig["local_scan"]}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :             {color_green if self.defConfig["psutil_scan"] == 1 else color_red}psutil_scan{color_black}                ==> {self.defConfig["psutil_scan"]}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :             {color_green if self.defConfig["abuseipdb_scan"] == 1 else color_red}abuseipdb_scan{color_black}             ==> {self.defConfig["abuseipdb_scan"]}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : [{color_green if self.defConfig["flood"] == 1 else color_red}Flood{color_black}]                                ==> {self.defConfig["flood"]}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :      flood_action                      ==> Coming soon')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :      flood_message                     ==> {self.defConfig["flood_message"]}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :      flood_time                        ==> {self.defConfig["flood_time"]}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :      flood_timer                       ==> {self.defConfig["flood_timer"]}')
                except KeyError as ke:
                    self.Irc.debug(f"Key Error : {ke}")

            case 'join':

                try:
                    channel = cmd[1]
                    self.Irc.send2socket(f':{service_id} JOIN {channel}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : {dnickname} JOINED {channel}')
                    self.add_defender_channel(channel)
                except IndexError:
                    self.Irc.debug('_hcmd join: out of index')

            case 'part':

                try:
                    channel = cmd[1]
                    if channel ==  dchanlog:
                        self.Irc.send2socket(f":{dnickname} NOTICE {fromuser} : {dnickname} CAN'T LEFT {channel} AS IT IS LOG CHANNEL")
                        return False

                    self.Irc.send2socket(f':{service_id} PART {channel}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : {dnickname} LEFT {channel}')
                    self.delete_defender_channel(channel)
                except IndexError:
                    self.Irc.debug('_hcmd part: out of index')

            case 'op' | 'o':
                # /mode #channel +o user
                # .op #channel user
                # [':adator', 'PRIVMSG', '#services', ':.o', '#services', 'dktmb']
                try:
                    print(cmd)
                    channel = cmd[1]
                    nickname = cmd[2]
                    self.Irc.send2socket(f":{service_id} MODE {channel} +o {nickname}")
                except IndexError as e:
                    self.Irc.debug(f'_hcmd OP: {str(e)}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} op [#SALON] [NICKNAME]')

            case 'deop' | 'do':
                # /mode #channel -o user
                # .deop #channel user
                try:
                    channel = cmd[1]
                    nickname = cmd[2]
                    self.Irc.send2socket(f":{service_id} MODE {channel} -o {nickname}")
                except IndexError as e:
                    self.Irc.debug(f'_hcmd DEOP: {str(e)}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} deop [#SALON] [NICKNAME]')

            case 'owner' | 'q':
                # /mode #channel +q user
                # .owner #channel user
                try:
                    channel = cmd[1]
                    nickname = cmd[2]
                    self.Irc.send2socket(f":{service_id} MODE {channel} +q {nickname}")
                except IndexError as e:
                    self.Irc.debug(f'_hcmd OWNER: {str(e)}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} owner [#SALON] [NICKNAME]')

            case 'deowner' | 'dq':
                # /mode #channel -q user
                # .deowner #channel user
                try:
                    channel = cmd[1]
                    nickname = cmd[2]
                    self.Irc.send2socket(f":{service_id} MODE {channel} -q {nickname}")
                except IndexError as e:
                    self.Irc.debug(f'_hcmd DEOWNER: {str(e)}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} deowner [#SALON] [NICKNAME]')

            case 'halfop' | 'h':
                # /mode #channel +h user
                # .halfop #channel user
                try:
                    channel = cmd[1]
                    nickname = cmd[2]
                    self.Irc.send2socket(f":{service_id} MODE {channel} +h {nickname}")
                except IndexError as e:
                    self.Irc.debug(f'_hcmd halfop: {str(e)}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} halfop [#SALON] [NICKNAME]')

            case 'dehalfop' | 'dh':
                # /mode #channel -h user
                # .dehalfop #channel user
                try:
                    channel = cmd[1]
                    nickname = cmd[2]
                    self.Irc.send2socket(f":{service_id} MODE {channel} -h {nickname}")
                except IndexError as e:
                    self.Irc.debug(f'_hcmd DEHALFOP: {str(e)}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} dehalfop [#SALON] [NICKNAME]')

            case 'voice' | 'v':
                # /mode #channel +v user
                # .voice #channel user
                try:
                    channel = cmd[1]
                    nickname = cmd[2]
                    self.Irc.send2socket(f":{service_id} MODE {channel} +v {nickname}")
                except IndexError as e:
                    self.Irc.debug(f'_hcmd VOICE: {str(e)}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} voice [#SALON] [NICKNAME]')

            case 'devoice' | 'dv':
                # /mode #channel -v user
                # .devoice #channel user
                try:
                    channel = cmd[1]
                    nickname = cmd[2]
                    self.Irc.send2socket(f":{service_id} MODE {channel} -v {nickname}")
                except IndexError as e:
                    self.Irc.debug(f'_hcmd DEVOICE: {str(e)}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} devoice [#SALON] [NICKNAME]')

            case 'ban' | 'b':
                # .ban #channel nickname
                try:
                    channel = cmd[1]
                    nickname = cmd[2]

                    self.Irc.send2socket(f":{service_id} MODE {channel} +b {nickname}!*@*")
                    self.Irc.debug(f'{fromuser} has banned {nickname} from {channel}')
                except IndexError as e:
                    self.Irc.debug(f'_hcmd BAN: {str(e)}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} ban [#SALON] [NICKNAME]')

            case 'unban' | 'ub':
                # .unban #channel nickname
                try:
                    channel = cmd[1]
                    nickname = cmd[2]

                    self.Irc.send2socket(f":{service_id} MODE {channel} -b {nickname}!*@*")
                    self.Irc.debug(f'{fromuser} has unbanned {nickname} from {channel}')
                except IndexError as e:
                    self.Irc.debug(f'_hcmd UNBAN: {str(e)}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} unban [#SALON] [NICKNAME]')

            case 'kick' | 'k':
                # .kick #channel nickname reason
                try:
                    channel = cmd[1]
                    nickname = cmd[2]
                    reason = []

                    for i in range(3, len(cmd)):
                        reason.append(cmd[i]) 

                    final_reason = ' '.join(reason)

                    self.Irc.send2socket(f":{service_id} KICK {channel} {nickname} {final_reason}")
                    self.Irc.debug(f'{fromuser} has kicked {nickname} from {channel} : {final_reason}')
                except IndexError as e:
                    self.Irc.debug(f'_hcmd KICK: {str(e)}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} kick [#SALON] [NICKNAME] [REASON]')

            case 'kickban' | 'kb':
                # .kickban #channel nickname reason
                try:
                    channel = cmd[1]
                    nickname = cmd[2]
                    reason = []

                    for i in range(3, len(cmd)):
                        reason.append(cmd[i]) 

                    final_reason = ' '.join(reason)

                    self.Irc.send2socket(f":{service_id} KICK {channel} {nickname} {final_reason}")
                    self.Irc.send2socket(f":{service_id} MODE {channel} +b {nickname}!*@*")
                    self.Irc.debug(f'{fromuser} has kicked and banned {nickname} from {channel} : {final_reason}')
                except IndexError as e:
                    self.Irc.debug(f'_hcmd KICKBAN: {str(e)}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} kickban [#SALON] [NICKNAME] [REASON]')

            case 'info':
                try:
                    nickoruid = cmd[1]
                    uid_query = None
                    nickname_query = None

                    if not self.Irc.get_nickname(nickoruid) is None:
                        nickname_query = self.Irc.get_nickname(nickoruid)

                    if not self.Irc.get_uid(nickoruid) is None:
                        uid_query = self.Irc.get_uid(nickoruid)

                    if nickname_query is None and uid_query is None:
                        self.Irc.send2socket(f":{dnickname} NOTICE {fromuser} : This user {nickoruid} doesn't exist")
                    else:
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : UID              : {uid_query}')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : NICKNAME         : {self.Irc.db_uid[uid_query]["nickname"]}')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : USERNAME         : {self.Irc.db_uid[uid_query]["username"]}')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : HOSTNAME         : {self.Irc.db_uid[uid_query]["hostname"]}')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : VHOST            : {self.Irc.db_uid[uid_query]["vhost"]}')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : MODES            : {self.Irc.db_uid[uid_query]["umodes"]}')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : CONNECTION TIME  : {self.Irc.db_uid[uid_query]["datetime"]}')
                except KeyError as ke:
                    self.Irc.debug(f"Key error info user : {ke}")

            case 'show_users':
                for uid, infousers in self.Irc.db_uid.items():
                    # print(uid + " " + str(infousers))
                    for info in infousers:
                        if info == 'nickname':
                            self.Irc.send2socket(f":{dnickname} PRIVMSG {dchanlog} :UID : {uid} - isWebirc: {infousers['isWebirc']} - {info}: {infousers[info]}")
