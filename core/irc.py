import ssl, re, importlib, sys, time, threading, socket
from datetime import datetime, timedelta

from core.configuration import Config
from core.base import Base

class Irc:

    def __init__(self) -> 'Irc':

        self.defender_connexion_datetime = datetime.now()   # Date et heure de la premiere connexion de Defender
        self.db_uid = {}                                    # Definir la variable qui contiendra la liste des utilisateurs connectés au réseau
        self.db_admin = {}                                  # Definir la variable qui contiendra la liste des administrateurs
        self.db_chan = []                                   # Definir la variable qui contiendra la liste des salons
        self.loaded_classes:dict[str, 'Irc'] = {}           # Definir la variable qui contiendra la liste modules chargés
        self.beat = 30                                      # Lancer toutes les 30 secondes des actions de nettoyages
        self.hb_active = True                               # Heartbeat active
        self.HSID = ''                                      # ID du serveur qui accueil le service ( Host Serveur Id )

        self.INIT = 1                                       # Variable d'intialisation | 1 -> indique si le programme est en cours d'initialisation
        self.RESTART = 0                                    # Variable pour le redemarrage du bot | 0 -> indique que le programme n'es pas en cours de redemarrage
        self.CHARSET = ['utf-8', 'iso-8859-1']              # Charset utiliser pour décoder/encoder les messages 

        self.Config = Config()

        # Liste des commandes internes du bot
        self.commands_level = {
            0: ['help', 'auth', 'copyright'],
            1: ['load','reload','unload', 'deauth', 'uptime'],
            2: ['show_modules', 'show_timers', 'show_threads', 'sentinel'],
            3: ['quit', 'restart','addaccess','editaccess', 'delaccess']
        }

        # l'ensemble des commandes.
        self.commands = []
        for level, commands in self.commands_level.items():
            for command in self.commands_level[level]:
                self.commands.append(command)

        self.Base = Base(self.Config)
        self.Base.create_thread(self.heartbeat, (self.beat, ))

    ##############################################
    #               CONNEXION IRC                #
    ##############################################
    def init_irc(self, ircInstance:'Irc') -> None:
        try:
            self.__create_socket()
            self.__connect_to_irc(ircInstance)
        except AssertionError as ae:
            self.debug(f'Assertion error : {ae}')

    def __create_socket(self) -> None:

        self.IrcSocket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connexion_information = (self.Config.SERVEUR_IP, self.Config.SERVEUR_PORT)
        self.IrcSocket.connect(connexion_information)

        # Créer un object ssl
        ssl_context = self.__ssl_context()
        ssl_connexion = ssl_context.wrap_socket(self.IrcSocket, server_hostname=self.Config.SERVEUR_HOSTNAME)
        self.IrcSocket = ssl_connexion

        return None

    def __ssl_context(self) -> ssl.SSLContext:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        return ctx

    def __connect_to_irc(self, ircInstance: 'Irc') -> None:
        try:
            self.ircObject = ircInstance                        # créer une copie de l'instance Irc
            self.__link(self.IrcSocket)                         # établir la connexion au serveur IRC
            self.signal = True                                  # Une variable pour initier la boucle infinie
            self.load_existing_modules()                        # Charger les modules existant dans la base de données

            while self.signal:
                if self.RESTART == 1:
                    self.IrcSocket.shutdown(socket.SHUT_RDWR)
                    self.IrcSocket.close()

                    while self.IrcSocket.fileno() != -1:
                        time.sleep(0.5)
                        self.debug("--> En attente de la fermeture du socket ...")

                    self.__create_socket()
                    self.__link(self.IrcSocket)
                    self.load_existing_modules()
                    self.RESTART = 0
                # 4072 max what the socket can grab
                buffer_size = self.IrcSocket.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
                # data = self.IrcSocket.recv(buffer_size).splitlines(True)

                data_in_bytes = self.IrcSocket.recv(buffer_size)
                count_bytes = len(data_in_bytes)

                while count_bytes > 4070:
                    # If the received message is > 4070 then loop and add the value to the variable
                    new_data = self.IrcSocket.recv(buffer_size)
                    data_in_bytes += new_data
                    count_bytes = len(new_data)
                    # print("========================================================")

                data = data_in_bytes.splitlines()

                # print(f"{str(buffer_size)} - {str(len(data_in_bytes))}")

                if not data:
                    break

                self.send_response(data)

            self.IrcSocket.shutdown(socket.SHUT_RDWR)
            self.IrcSocket.close()

        except AssertionError as ae:
            self.debug(f'Assertion error : {ae}')
        except ValueError as ve:
            self.debug(f'Value Error : {ve}')
        except OSError as oe:
            self.debug(f"OS Error : {oe}")

    def __link(self, writer:socket.socket) -> None:
        """Créer le link et envoyer les informations nécessaires pour la 
        connexion au serveur.

        Args:
            writer (StreamWriter): permet l'envoi des informations au serveur.
        """

        nickname = self.Config.SERVICE_NICKNAME
        username = self.Config.SERVICE_USERNAME
        realname = self.Config.SERVICE_REALNAME
        chan = self.Config.SERVICE_CHANLOG
        info = self.Config.SERVICE_INFO
        smodes = self.Config.SERVICE_SMODES
        cmodes = self.Config.SERVICE_CMODES
        umodes = self.Config.SERVICE_UMODES
        host = self.Config.SERVICE_HOST
        service_name = self.Config.SERVICE_NAME

        password = self.Config.SERVEUR_PASSWORD
        link = self.Config.SERVEUR_LINK
        sid = self.Config.SERVEUR_ID
        service_id = self.Config.SERVICE_ID

        version = self.Config.DEFENDER_VERSION
        unixtime = self.Base.get_unixtime()

        # Envoyer un message d'identification
        # strtobytes = bytes(":" + sid + " PASS :" + password + "\r\n", 'utf-8')
        # self.IrcSocket.send(strtobytes)
        writer.send(f":{sid} PASS :{password}\r\n".encode('utf-8'))
        writer.send(f":{sid} PROTOCTL NICKv2 VHP UMODE2 NICKIP SJOIN SJOIN2 SJ3 NOQUIT TKLEXT MLOCK SID MTAGS\r\n".encode('utf-8'))
        writer.send(f":{sid} PROTOCTL EAUTH={link},,,{service_name}-v{version}\r\n".encode('utf-8'))
        writer.send(f":{sid} PROTOCTL SID={sid}\r\n".encode('utf-8'))
        writer.send(f":{sid} SERVER {link} 1 :{info}\r\n".encode('utf-8'))
        writer.send(f":{sid} {nickname} :Reserved for services\r\n".encode('utf-8'))
        writer.send(f":{sid} UID {nickname} 1 {unixtime} {username} {host} {service_id} * {smodes} * * * :{realname}\r\n".encode('utf-8'))
        writer.send(f":{sid} SJOIN {unixtime} {chan} + :{service_id}\r\n".encode('utf-8'))
        writer.send(f":{sid} MODE {chan} +{cmodes}\r\n".encode('utf-8'))
        writer.send(f":{service_id} SAMODE {chan} +{umodes} {nickname}\r\n".encode('utf-8'))
        
        # writer.write(f"USER {nickname} {username} {username} {nickname} {username} :{username}\r\n".encode('utf-8'))
        # writer.write(f"USER {username} {username} {username} :{username}\r\n".encode('utf-8'))
        # writer.write(f"NICK {nickname}\r\n".encode('utf-8'))

    def send2socket(self, send_message:str)->None:
        """Envoit les commandes à envoyer au serveur.

        Args:
            string (Str): contient la commande à envoyer au serveur.
        """
        try:
            self.IrcSocket.send(f"{send_message}\r\n".encode(self.CHARSET[0]))

        except UnicodeDecodeError:
            self.debug('Write Decode impossible try iso-8859-1')
            self.IrcSocket.send(f"{send_message}\r\n".encode(self.CHARSET[0],'replace'))
        except UnicodeEncodeError:
            self.debug('Write Encode impossible ... try iso-8859-1')
            self.IrcSocket.send(f"{send_message}\r\n".encode(self.CHARSET[0],'replace'))
        except AssertionError as ae:
            self.debug(f"Assertion error : {ae}")
        except OSError as oe:
            self.debug(f"OS Error : {oe}")

    def send_response(self, responses:list[bytes]) -> None:
        try:
            # print(data)
            for data in responses:
                response = data.decode(self.CHARSET[0]).split()
                self.cmd(response)
        except UnicodeEncodeError:
            for data in responses:
                response = data.decode(self.CHARSET[1],'replace').split()
                self.cmd(response)
        except UnicodeDecodeError:
            for data in responses:
                response = data.decode(self.CHARSET[1],'replace').split()
                self.cmd(response)
        except AssertionError as ae:
            self.debug(f"Assertion error : {ae}")
    ##############################################
    #             FIN CONNEXION IRC              #
    ##############################################
    def load_existing_modules(self) -> None:
        """Charge les modules qui existe déja dans la base de données

        Returns:
            None: Aucun retour requis, elle charge puis c'est tout
        """
        result = self.Base.db_execute_query(f"SELECT module FROM {self.Base.DB_SCHEMA['modules']}")
        for r in result.fetchall():
            self.load_module('sys', r[0], True)

        return None

    def get_defender_uptime(self)->str:
        """Savoir depuis quand Defender est connecté

        Returns:
            str: L'écart entre la date du jour et celle de la connexion de Defender
        """
        current_datetime = datetime.now()
        diff_date = current_datetime - self.defender_connexion_datetime
        uptime = timedelta(days=diff_date.days, seconds=diff_date.seconds)
        
        return uptime

    def heartbeat(self, beat:float) -> None:
        """Execute certaines commandes de nettoyage toutes les x secondes
        x étant définit a l'initialisation de cette class (self.beat)

        Args:
            beat (float): Nombre de secondes entre chaque exécution
        """
        while self.hb_active:
            time.sleep(beat)
            service_id = self.Config.SERVICE_ID
            hsid = self.HSID
            # self.send2socket(f':{service_id} PING :{hsid}')
            self.Base.execute_periodic_action()

    def create_ping_timer(self, time_to_wait:float, class_name:str, method_name: str, method_args: list=[]) -> None:
        # 1. Timer créer
        #   1.1 Créer la fonction a executer
        #   1.2 Envoyer le ping une fois le timer terminer
        # 2. Executer la fonction
        try:
            if not class_name in self.loaded_classes:
                self.debug(f"La class [{class_name} n'existe pas !!]")
                return False

            class_instance = self.loaded_classes[class_name]

            t = threading.Timer(interval=time_to_wait, function=self.__create_tasks, args=(class_instance, method_name, method_args))
            t.start()

            self.Base.running_timers.append(t)

            self.debug(f"Timer ID : {str(t.ident)} | Running Threads : {len(threading.enumerate())}")

        except AssertionError as ae:
            self.debug(f'Assertion Error -> {ae}')
        except TypeError as te:
            self.debug(f"Type error -> {te}")

    def __create_tasks(self, obj: object, method_name: str, param:list) -> None:
        """#### Ajouter les méthodes a éxecuter dans un dictionnaire

        Args:
            obj (object): Une instance de la classe qui va etre executer
            method_name (str): Le nom de la méthode a executer
            param (list): les parametres a faire passer

        Returns:
            None: aucun retour attendu
        """
        self.Base.periodic_func[len(self.Base.periodic_func) + 1] = {
            'object': obj,
            'method_name': method_name,
            'param': param
            }

        self.debug(f'Function to execute : {str(self.Base.periodic_func)}')
        self.send_ping_to_sereur()
        return None

    def send_ping_to_sereur(self) -> None:
        """### Envoyer un PING au serveur   
        """
        service_id = self.Config.SERVICE_ID
        hsid = self.HSID
        self.send2socket(f':{service_id} PING :{hsid}')

        return None

    def load_module(self, fromuser:str, module_name:str, init:bool = False) -> bool:

        try:
            # module_name : mod_voice
            module_name = module_name.lower()
            class_name = module_name.split('_')[1].capitalize()         # ==> Voice

            # print(self.loaded_classes)

            # Si le module est déja chargé
            if 'mods.' + module_name in sys.modules:
                self.debug("Module déja chargé ...")
                self.debug('module name = ' + module_name)
                if class_name in self.loaded_classes:
                    # Si le module existe dans la variable globale retourne False
                    self.send2socket(f":{self.Config.SERVICE_NICKNAME} PRIVMSG {self.Config.SERVICE_CHANLOG} :Le module {module_name} est déja chargé ! si vous souhaiter le recharge tapez {self.Config.SERVICE_PREFIX}reload {module_name}")
                    return False

                the_module = sys.modules['mods.' + module_name]
                importlib.reload(the_module)
                my_class = getattr(the_module, class_name, None)
                new_instance = my_class(self.ircObject)
                self.loaded_classes[class_name] = new_instance

                # Créer le module dans la base de données
                if not init:
                    self.Base.db_record_module(fromuser, module_name)

                self.send2socket(f":{self.Config.SERVICE_NICKNAME} PRIVMSG {self.Config.SERVICE_CHANLOG} :Module {module_name} chargé")
                return False

            # Charger le module
            loaded_module = importlib.import_module(f"mods.{module_name}")

            my_class = getattr(loaded_module, class_name, None)                 # Récuperer le nom de classe
            create_instance_of_the_class = my_class(self.ircObject)             # Créer une nouvelle instance de la classe
            self.loaded_classes[class_name] = create_instance_of_the_class      # Charger la nouvelle class dans la variable globale

            # Enregistrer le module dans la base de données
            if not init:
                self.Base.db_record_module(fromuser, module_name)
            self.send2socket(f":{self.Config.SERVICE_NICKNAME} PRIVMSG {self.Config.SERVICE_CHANLOG} :Module {module_name} chargé")

            self.debug(self.loaded_classes)
            return True

        except ModuleNotFoundError as moduleNotFound:
            self.debug(f"MODULE_NOT_FOUND: {moduleNotFound}")
            self.send2socket(f":{self.Config.SERVICE_NICKNAME} PRIVMSG {self.Config.SERVICE_CHANLOG} :[ {self.Config.CONFIG_COLOR['rouge']}MODULE_NOT_FOUND{self.Config.CONFIG_COLOR['noire']} ]: {moduleNotFound}")
        except:
            self.debug(f"Something went wrong with a module you want to load")

    def insert_db_uid(self, uid:str, nickname:str, username:str, hostname:str, umodes:str, vhost:str, isWebirc: bool) -> None:

        if uid in self.db_uid:
            return None

        self.db_uid[uid] = {
            'nickname': nickname,
            'username': username,
            'hostname': hostname,
            'umodes': umodes,
            'vhost': vhost,
            'isWebirc': isWebirc,
            'datetime': datetime.now()
        }

        self.db_uid[nickname] = {
            'uid': uid,
            'username': username,
            'hostname': hostname,
            'umodes': umodes,
            'vhost': vhost,
            'isWebirc': isWebirc,
            'datetime': datetime.now()
        }

        return None

    def update_db_uid(self, uid:str, newnickname:str) -> None:
        
        # Récupérer l'ancien nickname
        oldnickname = self.db_uid[uid]['nickname']

        # Enregistrement du nouveau nickname
        self.db_uid[newnickname] = {
            'uid': uid,
            'username': self.db_uid[uid]['username'],
            'hostname': self.db_uid[uid]['hostname'],
            'umodes': self.db_uid[uid]['umodes'],
            'vhost': self.db_uid[uid]['vhost']
        }
        
        # Modification du nickname dans la ligne UID 
        self.db_uid[uid]['nickname'] = newnickname

        # Supprimer l'ancien nickname
        if oldnickname in self.db_uid:
            del self.db_uid[oldnickname]
        else:
            self.debug(f"L'ancien nickname {oldnickname} n'existe pas dans UID_DB")
            response = False

        self.debug(f"{oldnickname} changed to {newnickname}")
        
        return None

    def delete_db_uid(self, uid:str) -> None:

        uid_reel = self.get_uid(uid)
        nickname = self.get_nickname(uid_reel)

        if uid_reel in self.db_uid:
            del self.db_uid[uid]

        if nickname in self.db_uid:
            del self.db_uid[nickname]

        return None

    def insert_db_admin(self, uid:str, level:int) -> None:

        if not uid in self.db_uid:
            return None

        nickname = self.db_uid[uid]['nickname']
        username = self.db_uid[uid]['username']
        hostname = self.db_uid[uid]['hostname']
        umodes = self.db_uid[uid]['umodes']
        vhost = self.db_uid[uid]['vhost']
        level = int(level)
        
        

        self.db_admin[uid] = {
            'nickname': nickname,
            'username': username,
            'hostname': hostname,
            'umodes': umodes,
            'vhost': vhost,
            'datetime': self.Base.get_datetime(),
            'level': level
        }

        self.db_admin[nickname] = {
            'uid': uid,
            'username': username,
            'hostname': hostname,
            'umodes': umodes,
            'vhost': vhost,
            'datetime': self.Base.get_datetime(),
            'level': level
        }

        return None

    def delete_db_admin(self, uid:str) -> None:

        if not uid in self.db_admin:
            return None

        nickname_admin = self.db_admin[uid]['nickname']

        if uid in self.db_admin:
            del self.db_admin[uid]

        if nickname_admin in self.db_admin:
            del self.db_admin[nickname_admin]

        return None

    def insert_db_chan(self, channel:str) -> bool:
        """Ajouter l'ensemble des salons dans la variable {CHAN_DB}

        Args:
            channel (str): le salon à insérer dans {CHAN_DB}

        Returns:
            bool: True si insertion OK / False si insertion KO
        """
        if channel in self.db_chan:
            return False
        
        response = True
        # Ajouter un nouveau salon
        self.db_chan.append(channel)

        # Supprimer les doublons de la liste
        self.db_chan = list(set(self.db_chan))

        self.debug(f"Le salon {channel} a été ajouté à la liste CHAN_DB")

        return response

    def create_defender_user(self, nickname:str, level: int, password:str) -> str:

        nickname = self.get_nickname(nickname)
        response = ''

        if level > 4:
            response = "Impossible d'ajouter un niveau > 4"
            self.debug(response)
            return response

        # Verification si le user existe dans notre UID_DB
        if not nickname in self.db_uid:
            response = f"{nickname} n'est pas connecté, impossible de l'enregistrer pour le moment"
            self.debug(response)
            return response

        hostname = self.db_uid[nickname]['hostname']
        vhost = self.db_uid[nickname]['vhost']
        spassword = self.Base.crypt_password(password)

        mes_donnees = {'admin': nickname}
        query_search_user = f"SELECT id FROM {self.Base.DB_SCHEMA['admins']} WHERE user=:admin"
        r = self.Base.db_execute_query(query_search_user, mes_donnees)
        exist_user = r.fetchone()

        # On verifie si le user exist dans la base
        if not exist_user:
            mes_donnees = {'datetime': self.Base.get_datetime(), 'user': nickname, 'password': spassword, 'hostname': hostname, 'vhost': vhost, 'level': level}
            self.Base.db_execute_query(f'''INSERT INTO {self.Base.DB_SCHEMA['admins']} 
                    (createdOn, user, password, hostname, vhost, level) VALUES
                    (:datetime, :user, :password, :hostname, :vhost, :level)
                    ''', mes_donnees)
            response = f"{nickname} ajouté en tant qu'administrateur de niveau {level}"
            self.send2socket(f':{self.Config.SERVICE_NICKNAME} NOTICE {nickname} : {response}')
            self.debug(response)
            return response
        else:
            response = f'{nickname} Existe déjà dans les users enregistrés'
            self.send2socket(f':{self.Config.SERVICE_NICKNAME} NOTICE {nickname} : {response}')
            self.debug(response)
            return response

    def get_uid(self, uidornickname:str) -> str | None:

        uid_recherche = uidornickname
        response = None
        for uid, value in self.db_uid.items():
            if uid == uid_recherche:
                if 'nickname' in value:
                    response = uid
                if 'uid' in value:
                    response = value['uid']

        return response

    def get_nickname(self, uidornickname:str) -> str | None:
        
        nickname_recherche = uidornickname

        response = None
        for nickname, value in self.db_uid.items():
            if nickname == nickname_recherche:
                if 'nickname' in value:
                    response = value['nickname']
                if 'uid' in value:
                    response = nickname

        return response

    def is_cmd_allowed(self,nickname:str, cmd:str) -> bool:
        
        # Vérifier si le user est identifié et si il a les droits
        is_command_allowed = False
        uid = self.get_uid(nickname)
        
        if uid in self.db_admin:
            admin_level = self.db_admin[uid]['level']

            for ref_level, ref_commands in self.commands_level.items():
                # print(f"LevelNo: {ref_level} - {ref_commands} - {admin_level}")
                if ref_level <= int(admin_level):
                    # print(f"LevelNo: {ref_level} - {ref_commands}")
                    if cmd in ref_commands:
                        is_command_allowed = True
        else:
            for ref_level, ref_commands in self.commands_level.items():
                if ref_level == 0:
                    # print(f"LevelNo: {ref_level} - {ref_commands}")
                    if cmd in ref_commands:
                        is_command_allowed = True

        return is_command_allowed

    def debug(self, debug_msg:str) -> None:

        if self.Config.DEBUG == 1:
            if type(debug_msg) == list:
                if debug_msg[0] != 'PING':
                    print(f"[{self.Base.get_datetime()}] - {debug_msg}")
            else:
                print(f"[{self.Base.get_datetime()}] - {debug_msg}")

        return None

    def logs(self, log_msg:str) -> None:

        mes_donnees = {'datetime': self.Base.get_datetime(), 'server_msg': log_msg}
        self.Base.db_execute_query('INSERT INTO sys_logs (datetime, server_msg) VALUES (:datetime, :server_msg)', mes_donnees)

        return None

    def cmd(self, data:list) -> None:
        try:
            cmd_to_send:list[str] = data.copy()
            cmd = data.copy()

            if len(cmd) == 0 or len(cmd) == 1:
                return False

            self.debug(cmd)

            match cmd[0]:

                case 'PING':
                    # Sending PONG response to the serveur
                    pong = str(cmd[1]).replace(':','')
                    self.send2socket(f"PONG :{pong}")
                    return None

                case 'PROTOCTL':
                    #['PROTOCTL', 'CHANMODES=beI,fkL,lFH,cdimnprstzCDGKMNOPQRSTVZ', 'USERMODES=diopqrstwxzBDGHIRSTWZ', 'BOOTED=1702138935', 
                    # 'PREFIX=(qaohv)~&@%+', 'SID=001', 'MLOCK', 'TS=1703793941', 'EXTSWHOIS']

                    # GET SERVER ID HOST
                    if len(cmd) > 5:
                        if '=' in cmd[5]:
                            serveur_hosting_id = str(cmd[5]).split('=')
                            self.HSID = serveur_hosting_id[1]
                            return False

                case _:
                    pass

            if len(cmd) < 2:
                return False

            match cmd[1]:

                case 'SLOG':
                    # self.Base.scan_ports(cmd[7])
                    # if self.Config.ABUSEIPDB == 1:
                    #     self.Base.create_thread(self.abuseipdb_scan, (cmd[7], ))
                    pass

                case 'REPUTATION':
                    # :001 REPUTATION 91.168.141.239 118
                    try:
                        # if self.Config.ABUSEIPDB == 1:
                        #     self.Base.create_thread(self.abuseipdb_scan, (cmd[2], ))
                        pass
                        # Possibilité de déclancher les bans a ce niveau.
                    except IndexError:
                        self.debug(f'cmd reputation: index error')

                case '320':
                    #:irc.deb.biz.st 320 PyDefender IRCParis07 :is in security-groups: known-users,webirc-users,tls-and-known-users,tls-users
                    pass

                case '318':
                    #:irc.deb.biz.st 318 PyDefender IRCParis93 :End of /WHOIS list.
                    pass

                case 'MD':
                    # [':001', 'MD', 'client', '001CG0TG7', 'webirc', ':2']
                    pass

                case 'EOS':

                    hsid = str(cmd[0]).replace(':','')
                    if hsid == self.HSID:
                        if self.INIT == 1:
                            self.send2socket(f"MODE {self.Config.SERVICE_NICKNAME} +B")
                            self.send2socket(f"JOIN {self.Config.SERVICE_CHANLOG}")
                            print(f"################### DEFENDER ###################")
                            print(f"#               SERVICE CONNECTE                ")
                            print(f"# SERVEUR  :    {self.Config.SERVEUR_IP}        ")
                            print(f"# PORT     :    {self.Config.SERVEUR_PORT}      ")
                            print(f"# NICKNAME :    {self.Config.SERVICE_NICKNAME}  ")
                            print(f"# CHANNEL  :    {self.Config.SERVICE_CHANLOG}   ")
                            print(f"# VERSION  :    {self.Config.DEFENDER_VERSION}  ")
                            print(f"################################################")

                        # Initialisation terminé aprés le premier PING
                        self.INIT = 0
                        # self.send2socket(f':{self.Config.SERVICE_ID} PING :{hsid}')
                        # print(self.db_uid)

                case _:
                    pass

            if len(cmd) < 3:
                return False

            match cmd[2]:

                case 'QUIT':
                    # :001N1WD7L QUIT :Quit: free_znc_1
                    cmd.pop(0)
                    uid_who_quit = str(cmd[0]).replace(':', '')
                    self.delete_db_uid(uid_who_quit)
                
                case 'PONG':
                    # ['@msgid=aTNJhp17kcPboF5diQqkUL;time=2023-12-28T20:35:58.411Z', ':irc.deb.biz.st', 'PONG', 'irc.deb.biz.st', ':Dev-PyDefender']
                    self.Base.execute_periodic_action()

                case 'NICK':
                    # ['@unrealircd.org/geoip=FR;unrealircd.org/', ':001OOU2H3', 'NICK', 'WebIrc', '1703795844']
                    # Changement de nickname

                    # Supprimer la premiere valeur de la liste
                    cmd.pop(0)
                    uid = str(cmd[0]).replace(':','')
                    newnickname = cmd[2]

                    self.update_db_uid(uid, newnickname)

                case 'SJOIN':
                    # ['@msgid=ictnEBhHmTUHzkEeVZl6rR;time=2023-12-28T20:03:18.482Z', ':001', 'SJOIN', '1702139101', '#stats', '+nst', ':@001SB890A', '@00BAAAAAI']
                    cmd.pop(0)
                    channel = cmd[3]
                    self.insert_db_chan(channel)

                case 'UID':

                    if 'webirc' in cmd[0]:
                        isWebirc = True
                    else:
                        isWebirc = False

                    uid = str(cmd[8])
                    nickname = str(cmd[3])
                    username = str(cmd[6])
                    hostname = str(cmd[7])
                    umodes = str(cmd[10])
                    vhost = str(cmd[11])

                    self.insert_db_uid(uid, nickname, username, hostname, umodes, vhost, isWebirc)

                    for classe_name, classe_object in self.loaded_classes.items():
                        classe_object.cmd(cmd_to_send)

                case 'PRIVMSG':
                    try:
                        # Supprimer la premiere valeur
                        cmd.pop(0)

                        get_uid_or_nickname = str(cmd[0].replace(':',''))
                        # user_trigger = get_user.split('!')[0]
                        user_trigger = self.get_nickname(get_uid_or_nickname)
                        dnickname = self.Config.SERVICE_NICKNAME

                        pattern = fr'(:\{self.Config.SERVICE_PREFIX})(.*)$'
                        hcmds = re.search(pattern, ' '.join(cmd)) # va matcher avec tout les caractéres aprés le .

                        if hcmds: # Commande qui commencent par le point
                            liste_des_commandes = list(hcmds.groups())
                            convert_to_string = ' '.join(liste_des_commandes)
                            arg = convert_to_string.split()
                            arg.remove(f':{self.Config.SERVICE_PREFIX}')
                            if not arg[0].lower() in self.commands:
                                self.debug(f"This command {arg[0]} is not available")
                                return False

                            cmd_to_send = convert_to_string.replace(':','')
                            self.Base.log_cmd(user_trigger, cmd_to_send)

                            self._hcmds(user_trigger, arg)

                        if cmd[2] == self.Config.SERVICE_ID:
                            pattern = fr'^:.*?:(.*)$'

                            hcmds = re.search(pattern, ' '.join(cmd))

                            if hcmds: # par /msg defender [commande]
                                liste_des_commandes = list(hcmds.groups())
                                convert_to_string = ' '.join(liste_des_commandes)
                                arg = convert_to_string.split()

                                # Réponse a un CTCP VERSION
                                if arg[0] == '\x01VERSION\x01':
                                    self.send2socket(f':{dnickname} NOTICE {user_trigger} :\x01VERSION Service {self.Config.SERVICE_NICKNAME} V{self.Config.DEFENDER_VERSION}\x01')
                                    return False
                                
                                # Réponse a un TIME
                                if arg[0] == '\x01TIME\x01':
                                    current_datetime = self.Base.get_datetime()
                                    self.send2socket(f':{dnickname} NOTICE {user_trigger} :\x01TIME {current_datetime}\x01')
                                    return False
                                
                                # Réponse a un PING
                                if arg[0] == '\x01PING':
                                    recieved_unixtime = int(arg[1].replace('\x01',''))
                                    current_unixtime = self.Base.get_unixtime()
                                    ping_response = current_unixtime - recieved_unixtime
                                    self.send2socket(f':{dnickname} NOTICE {user_trigger} :\x01PING {str(ping_response)} secs\x01')
                                    return False

                                if not arg[0].lower() in self.commands:
                                    self.debug(f"This command {arg[0]} is not available")
                                    return False

                                cmd_to_send = convert_to_string.replace(':','')
                                self.Base.log_cmd(self.get_nickname(user_trigger), cmd_to_send)

                                self._hcmds(user_trigger, arg)

                    except IndexError:
                        self.debug(f'cmd --> PRIVMSG --> List index out of range')

                case _:
                    pass

            if cmd[2] != 'UID':
                # Envoyer la commande aux classes dynamiquement chargées
                for classe_name, classe_object in self.loaded_classes.items():
                    classe_object.cmd(cmd_to_send)

        except IndexError as ie:
            self.debug(f"IRC CMD -> IndexError : {ie} - {cmd} - length {str(len(cmd))}")

    def _hcmds(self, user: str, cmd:list) -> None:

        fromuser = self.get_nickname(user)                                        # Nickname qui a lancé la commande
        uid = self.get_uid(fromuser)                                              # Récuperer le uid de l'utilisateur

        # Defender information
        dnickname = self.Config.SERVICE_NICKNAME                                  # Defender nickname
        dchanlog = self.Config.SERVICE_CHANLOG                                    # Defender chan log

        if len(cmd) > 0:
            command = str(cmd[0]).lower()
        else:
            return False

        is_command_allowed = self.is_cmd_allowed(fromuser, command)
        if not is_command_allowed:
            command = 'notallowed'

        # Envoyer la commande aux classes dynamiquement chargées
        if command != 'notallowed':
            for classe_name, classe_object in self.loaded_classes.items():
                classe_object._hcmds(user, cmd)

        match command:

            case 'notallowed':
                try:
                    current_command = cmd[0]
                    self.send2socket(f':{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR["rouge"]}{current_command}{self.Config.CONFIG_COLOR["noire"]} ] - Accès Refusé à {self.get_nickname(fromuser)}')
                    self.send2socket(f':{dnickname} NOTICE {fromuser} : Accès Refusé')
                except IndexError:
                    self.debug(f'_hcmd notallowed : Index Error')

            case 'deauth':

                current_command = cmd[0]
                uid_to_deauth = self.get_uid(fromuser)
                self.delete_db_admin(uid_to_deauth)
                self.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['rouge']}{current_command}{self.Config.CONFIG_COLOR['noire']} ] - {self.get_nickname(fromuser)} est désormais déconnecter de {dnickname}")

            case 'auth':
                # ['auth', 'adator', 'password']
                current_command = cmd[0]
                user_to_log = self.get_nickname(cmd[1])
                password = cmd[2]

                if not user_to_log is None:
                    mes_donnees = {'user': user_to_log, 'password': self.Base.crypt_password(password)}
                    query = f"SELECT id, level FROM {self.Base.DB_SCHEMA['admins']} WHERE user = :user AND password = :password"
                    result = self.Base.db_execute_query(query, mes_donnees)
                    user_from_db = result.fetchone()
                    
                    if not user_from_db is None:
                        uid_user = self.get_uid(user_to_log)
                        self.insert_db_admin(uid_user, user_from_db[1])
                        self.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['verte']}{current_command}{self.Config.CONFIG_COLOR['noire']} ] - {self.get_nickname(fromuser)} est désormais connecté a {dnickname}")
                    else:
                        self.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.CONFIG_COLOR['rouge']}{current_command}{self.Config.CONFIG_COLOR['noire']} ] - {self.get_nickname(fromuser)} a tapé un mauvais mot de pass")
                        self.send2socket(f":{self.Config.SERVICE_NICKNAME} NOTICE {fromuser} :Mot de passe incorrecte")

                else:
                    self.send2socket(f":{self.Config.SERVICE_NICKNAME} NOTICE {fromuser} :L'utilisateur {user_to_log} n'existe pas")

            case 'addaccess':
                try:
                    # .addaccess adator 5 password
                    newnickname = cmd[1]
                    newlevel = self.Base.int_if_possible(cmd[2])
                    password = cmd[3]

                    response = self.create_defender_user(newnickname, newlevel, password)
                    self.send2socket(f':{dnickname} NOTICE {fromuser} : {response}')
                    self.debug(response)

                except IndexError as ie:
                    self.debug(f'_hcmd addaccess: {ie}')
                    self.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} addaccess [nickname] [level] [password]')
                except TypeError as te:
                    self.debug(f'_hcmd addaccess: out of index : {te}')
                    self.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} addaccess [nickname] [level] [password]')

            case 'editaccess':
                # .editaccess [USER] [PASSWORD] [LEVEL]
                try:
                    user_to_edit = cmd[1]
                    user_new_level = int(cmd[3])
                    user_password = self.Base.crypt_password(cmd[2])

                    if len(cmd) < 4 or len(cmd) > 4:
                        self.send2socket(f':{dnickname} NOTICE {fromuser} : .editaccess [USER] [NEWPASSWORD] [NEWLEVEL]')
                        return None

                    current_user = self.get_nickname(fromuser)
                    current_uid = self.get_uid(fromuser)
                    current_user_level = self.db_admin[current_uid]['level']

                    if user_new_level > 5:
                        self.send2socket(f':{dnickname} NOTICE {fromuser} : Maximum authorized level is 5')
                        return None

                    # Rechercher le user dans la base de données.
                    mes_donnees = {'user': user_to_edit}
                    query = f"SELECT user, level FROM {self.Base.DB_SCHEMA['admins']} WHERE user = :user"
                    result = self.Base.db_execute_query(query, mes_donnees)

                    isUserExist = result.fetchone()
                    if not isUserExist is None:

                        if current_user_level < int(isUserExist[1]):
                            self.send2socket(f':{dnickname} NOTICE {fromuser} : You are not allowed to edit this access')
                            return None
                        
                        if current_user_level == int(isUserExist[1]) and current_user != user_to_edit:
                            self.send2socket(f":{dnickname} NOTICE {fromuser} : You can't edit access of a user with same level")
                            return None

                        # Le user existe dans la base de données
                        data_to_update = {'user': user_to_edit, 'password': user_password, 'level': user_new_level}
                        sql_update = f"UPDATE {self.Base.DB_SCHEMA['admins']} SET level = :level, password = :password WHERE user = :user"
                        exec_query = self.Base.db_execute_query(sql_update, data_to_update)
                        if exec_query.rowcount > 0:
                            self.send2socket(f':{dnickname} NOTICE {fromuser} : User {user_to_edit} has been modified with level {str(user_new_level)}')
                        else:
                            self.send2socket(f":{dnickname} NOTICE {fromuser} : Impossible de modifier l'utilisateur {str(user_new_level)}")

                except TypeError as te:
                    self.debug(f"Type error : {te}")
                except ValueError as ve:
                    self.debug(f"Value Error : {ve}")
                    self.send2socket(f':{dnickname} NOTICE {fromuser} : .editaccess [USER] [NEWPASSWORD] [NEWLEVEL]')

            case 'delaccess':
                # .delaccess [USER] [CONFIRMUSER]
                user_to_del = cmd[1]
                user_confirmation = cmd[2]

                if user_to_del != user_confirmation:
                    self.send2socket(f':{dnickname} NOTICE {fromuser} : Les user ne sont pas les mêmes, tu dois confirmer le user que tu veux supprimer')
                    return None

                print(len(cmd))
                if len(cmd) < 3:
                    self.send2socket(f':{dnickname} NOTICE {fromuser} : .delaccess [USER] [CONFIRMUSER]')
                    return None

                current_user = self.get_nickname(fromuser)
                current_uid = self.get_uid(fromuser)
                current_user_level = self.db_admin[current_uid]['level']

                # Rechercher le user dans la base de données.
                mes_donnees = {'user': user_to_del}
                query = f"SELECT user, level FROM {self.Base.DB_SCHEMA['admins']} WHERE user = :user"
                result = self.Base.db_execute_query(query, mes_donnees)
                info_user = result.fetchone()
                
                if not info_user is None:
                    level_user_to_del = info_user[1]
                    if current_user_level <= level_user_to_del:
                        self.send2socket(f':{dnickname} NOTICE {fromuser} : You are not allowed to delete this access')
                        return None

                    data_to_delete = {'user': user_to_del}
                    sql_delete = f"DELETE FROM {self.Base.DB_SCHEMA['admins']} WHERE user = :user"
                    exec_query = self.Base.db_execute_query(sql_delete, data_to_delete)
                    if exec_query.rowcount > 0:
                        self.send2socket(f':{dnickname} NOTICE {fromuser} : User {user_to_del} has been deleted !')
                    else:
                        self.send2socket(f":{dnickname} NOTICE {fromuser} : Impossible de supprimer l'utilisateur.")

            case 'help':

                help = ''
                count_level_definition = 0
                if uid in self.db_admin:
                    user_level = self.db_admin[uid]['level']
                else:
                    user_level = 0

                self.send2socket(f':{dnickname} NOTICE {fromuser} : **************** LIST DES COMMANDES *****************')
                self.send2socket(f':{dnickname} NOTICE {fromuser} : ')
                for levDef in self.commands_level:
                    
                    if int(user_level) >= int(count_level_definition):

                        self.send2socket(f':{dnickname} NOTICE {fromuser} : **************** {self.Config.CONFIG_COLOR["noire"]}[ {self.Config.CONFIG_COLOR["verte"]}LEVEL {str(levDef)} {self.Config.CONFIG_COLOR["noire"]}] ****************')
                        count_commands = 0
                        help = ''
                        for comm in self.commands_level[count_level_definition]:

                            help += f"{comm.upper()}"
                            if int(count_commands) < len(self.commands_level[count_level_definition])-1:
                                help += ' | '
                            count_commands += 1

                        self.send2socket(f':{dnickname} NOTICE {fromuser} : {help}')

                    count_level_definition += 1

                self.send2socket(f':{dnickname} NOTICE {fromuser} : **************** FIN DES COMMANDES *****************')

            case 'load':

                self.load_module(fromuser, str(cmd[1]))

            case 'unload':
                # unload mod_dktmb
                try:
                    module_name = str(cmd[1]).lower()                              # Le nom du module. exemple: mod_defender
                    class_name = module_name.split('_')[1].capitalize()            # Nom de la class. exemple: Defender

                    if class_name in self.loaded_classes:

                        for level, command in self.loaded_classes[class_name].commands_level.items():
                            # Supprimer la commande de la variable commands
                            for c in self.loaded_classes[class_name].commands_level[level]:
                                self.commands.remove(c)
                                self.commands_level[level].remove(c)

                        del self.loaded_classes[class_name]

                        # Supprimer le module de la base de données
                        self.Base.db_delete_module(module_name)

                        self.send2socket(f":{self.Config.SERVICE_NICKNAME} PRIVMSG {self.Config.SERVICE_CHANLOG} :Module {module_name} supprimé")
                except:
                    self.debug(f"Something went wrong with a module you want to load")

            case 'reload':
                # reload mod_dktmb
                try:
                    module_name = str(cmd[1]).lower()                                          # ==> mod_defender
                    class_name = module_name.split('_')[1].capitalize()                        # ==> Defender

                    if 'mods.' + module_name in sys.modules:
                        self.debug('Module Already Loaded ... reload the module ...')
                        the_module = sys.modules['mods.' + module_name]
                        importlib.reload(the_module)
                        
                        # Supprimer la class déja instancier
                        if class_name in self.loaded_classes:
                        # Supprimer les commandes déclarer dans la classe
                            for level, command in self.loaded_classes[class_name].commands_level.items():
                                # Supprimer la commande de la variable commands
                                for c in self.loaded_classes[class_name].commands_level[level]:
                                    self.commands.remove(c)
                                    self.commands_level[level].remove(c)

                            del self.loaded_classes[class_name]

                        my_class = getattr(the_module, class_name, None)
                        new_instance = my_class(self.ircObject)
                        self.loaded_classes[class_name] = new_instance

                        self.send2socket(f":{self.Config.SERVICE_NICKNAME} PRIVMSG {self.Config.SERVICE_CHANLOG} :Module {module_name} rechargé")
                        return False
                    else:
                        self.send2socket(f":{self.Config.SERVICE_NICKNAME} PRIVMSG {self.Config.SERVICE_CHANLOG} :Module {module_name} n'est pas chargé !")
                except:
                    self.debug(f"Something went wrong with a module you want to reload")

            case 'quit':
                try:
                    reason = []
                    for i in range(1, len(cmd)):
                        reason.append(cmd[i])
                    final_reason = ' '.join(reason)

                    self.hb_active = False
                    self.Base.shutdown()
                    self.Base.execute_periodic_action()

                    self.send2socket(f':{dnickname} NOTICE {fromuser} : Arrêt du service {dnickname}')
                    self.send2socket(f':{self.Config.SERVEUR_LINK} SQUIT {self.Config.SERVEUR_LINK} :{final_reason}')
                    self.debug(f'Arrêt du server {dnickname}')
                    self.RESTART = 0
                    self.signal = False

                except IndexError:
                    self.debug('_hcmd die: out of index')
                
                self.send2socket(f"QUIT Good bye")

            case 'restart':
                reason = []
                for i in range(1, len(cmd)):
                    reason.append(cmd[i])
                final_reason = ' '.join(reason)

                self.db_uid.clear()                     #Vider UID_DB
                self.db_chan = []                       #Vider les salons

                self.send2socket(f':{dnickname} NOTICE {fromuser} : Redémarrage du service {dnickname}')
                self.send2socket(f':{self.Config.SERVEUR_LINK} SQUIT {self.Config.SERVEUR_LINK} :{final_reason}')
                self.debug(f'Redémarrage du server {dnickname}')
                self.loaded_classes.clear()
                self.RESTART = 1                 # Set restart status to 1 saying that the service will restart
                self.INIT = 1                    # set init to 1 saying that the service will be re initiated

            case 'show_modules':

                self.debug(self.loaded_classes)

                results = self.Base.db_execute_query(f'SELECT module FROM {self.Base.DB_SCHEMA["modules"]}')
                results = results.fetchall()

                if len(results) == 0:
                    self.send2socket(f":{dnickname} PRIVMSG {dchanlog} :Aucun module chargé")
                    return False

                for r in results:
                    self.send2socket(f":{dnickname} PRIVMSG {dchanlog} :Le module {r[0]} chargé")
                    self.debug(r[0])

            case 'show_timers':

                if self.Base.running_timers:
                    self.send2socket(f":{dnickname} PRIVMSG {dchanlog} :{self.Base.running_timers}")
                    self.debug(self.Base.running_timers)
                else:
                    self.send2socket(f":{dnickname} PRIVMSG {dchanlog} :Aucun timers en cours d'execution")

            case 'show_threads':
                self.send2socket(f":{dnickname} PRIVMSG {dchanlog} :{self.Base.running_threads}")

            case 'uptime':
                uptime = self.get_defender_uptime()
                self.send2socket(f':{dnickname} NOTICE {fromuser} : {uptime}')

            case 'copyright':
                self.send2socket(f':{dnickname} NOTICE {fromuser} : # Defender V.{self.Config.DEFENDER_VERSION} Developped by adator® and dktmb® #')

            case 'sentinel':
                # .sentinel on
                activation = str(cmd[1]).lower()
                service_id = self.Config.SERVICE_ID
                
                channel_to_dont_quit = [self.Config.SALON_JAIL, dchanlog]
                
                if activation == 'on':
                    for chan in self.db_chan:
                        if not chan in channel_to_dont_quit:
                            self.send2socket(f":{service_id} JOIN {chan}")
                if activation == 'off':
                    for chan in self.db_chan:
                        if not chan in channel_to_dont_quit:
                            self.send2socket(f":{service_id} PART {chan}")

            case _:
                pass
