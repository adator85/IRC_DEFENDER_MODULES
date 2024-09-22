from dataclasses import dataclass, fields, field
import random, faker, time, logging
from datetime import datetime
from typing import Union
from core.irc import Irc
from core.connection import Connection

class Clone():

    @dataclass
    class ModConfModel:
        clone_nicknames: list[str]

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

        self.Clone = ircInstance.Clones

        # Créer les nouvelles commandes du module
        self.commands_level = {
            1: ['clone']
        }

        # Init the module (Mandatory)
        self.__init_module()

        # Log the module
        self.Logs.debug(f'Module {self.module_name} loaded ...')

    def __init_module(self) -> None:

        # Enrigstrer les nouvelles commandes dans le code
        self.__set_commands(self.commands_level)

        # Créer les tables necessaire a votre module (ce n'es pas obligatoire)
        self.__create_tables()

        # Load module configuration (Mandatory)
        self.__load_module_configuration()

        self.Base.db_query_channel(action='add', module_name=self.module_name, channel_name=self.Config.CLONE_CHANNEL)
        self.Irc.send2socket(f":{self.Config.SERVICE_NICKNAME} JOIN {self.Config.CLONE_CHANNEL}")
        self.Irc.send2socket(f":{self.Config.SERVICE_NICKNAME} MODE {self.Config.CLONE_CHANNEL} +nts")
        self.Irc.send2socket(f":{self.Config.SERVICE_NICKNAME} MODE {self.Config.CLONE_CHANNEL} +k {self.Config.CLONE_CHANNEL_PASSWORD}")

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

        table_channel = '''CREATE TABLE IF NOT EXISTS clone_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            nickname TEXT,
            username TEXT
            )
        '''

        self.Base.db_execute_query(table_channel)

        return None

    def __load_module_configuration(self) -> None:
        """### Load Module Configuration
        """
        try:
            # Variable qui va contenir les options de configuration du module Defender
            self.ModConfig = self.ModConfModel(
                                    clone_nicknames=[]
                                )

            # Sync the configuration with core configuration (Mandatory)
            # self.Base.db_sync_core_config(self.module_name, self.ModConfig)

            return None

        except TypeError as te:
            self.Logs.critical(te)

    def unload(self) -> None:
        """Cette methode sera executée a chaque désactivation ou 
        rechargement de module
        """

        # kill all clones before unload
        for clone in self.ModConfig.clone_nicknames:
            self.Irc.send2socket(f':{self.Config.SERVICE_NICKNAME} PRIVMSG {clone} :KILL')

        self.Base.db_query_channel(action='del', module_name=self.module_name, channel_name=self.Config.CLONE_CHANNEL)
        self.Irc.send2socket(f":{self.Config.SERVICE_NICKNAME} PART {self.Config.CLONE_CHANNEL}")
        return None

    def thread_clone_clean_up(self, wait: float):

        activated = True

        while activated:
            clone_to_kill: list[str] = []

            for clone in self.Clone.UID_CLONE_DB:
                if not clone.connected and clone.alive and not clone.init:
                    clone_to_kill.append(clone.nickname)
                    clone.alive = False

            for clone_nickname in clone_to_kill:
                if self.Clone.delete(clone_nickname):
                    self.Logs.debug(f'<<{clone_nickname}>> object has been deleted')

            del clone_to_kill

            # If LIST empty then stop this thread
            if not self.Clone.UID_CLONE_DB:
                break

            time.sleep(wait)

    def thread_change_hostname(self):

        fake = faker.Faker('en_GB')
        for clone in self.Clone.UID_CLONE_DB:
            if not clone.vhost is None:
                continue

            rand_1 = fake.random_elements(['A','B','C','D','E','F','0','1','2','3','4','5','6','7','8','9'], unique=True, length=8)
            rand_2 = fake.random_elements(['A','B','C','D','E','F','0','1','2','3','4','5','6','7','8','9'], unique=True, length=8)
            rand_3 = fake.random_elements(['A','B','C','D','E','F','0','1','2','3','4','5','6','7','8','9'], unique=True, length=8)

            rand_ip = ''.join(rand_1) + '.' + ''.join(rand_2) + '.' + ''.join(rand_3) + '.IP'
            found = False

            while not found:
                if clone.connected:
                    self.Irc.send2socket(f':{self.Config.SERVICE_NICKNAME} CHGHOST {clone.nickname} {rand_ip}')
                    found = True
                    clone.vhost = rand_ip
                    break
                if not clone in self.Clone.UID_CLONE_DB:
                    found = True
                    break

    def thread_create_clones_with_interval(self, number_of_clones:int, channels: list, connection_interval: float):

        for i in range(number_of_clones):
            nickname, username, realname = self.generate_names()
            self.Base.create_thread(
                self.thread_create_clones,
                (nickname, username, realname, channels, 6697, True)
                )
            time.sleep(connection_interval)

        self.Base.create_thread(
            self.thread_change_hostname
        )

        # self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :{str(number_of_clones)} clones joined the network')

        self.Base.create_thread(self.thread_clone_clean_up, (5, ), run_once=True)

    def thread_create_clones(self, nickname: str, username: str, realname: str, channels: list, server_port: int, ssl: bool) -> None:

        Connection(server_port=server_port, nickname=nickname, username=username, realname=realname, channels=channels, CloneObject=self.Clone, ssl=ssl)

        return None

    def thread_join_channels(self, channel_name: str, wait: float, clone_name:str = None):
        self.Irc.send2socket(f':{self.Config.SERVICE_NICKNAME} PRIVMSG {self.Config.SERVICE_CHANLOG} :Clones start to join {channel_name} with {wait} secondes frequency')
        if clone_name is None:
            for clone in self.Clone.UID_CLONE_DB:
                if not channel_name in clone.channels:
                    time.sleep(wait)
                    self.Irc.send2socket(f':{self.Config.SERVICE_NICKNAME} PRIVMSG {clone.nickname} :JOIN {channel_name}')
                    clone.channels.append(channel_name)
        else:
            for clone in self.Clone.UID_CLONE_DB:
                if clone_name == clone.nickname:
                    if not channel_name in clone.channels:
                        time.sleep(wait)
                        self.Irc.send2socket(f':{self.Config.SERVICE_NICKNAME} PRIVMSG {clone.nickname} :JOIN {channel_name}')
                        clone.channels.append(channel_name)

    def generate_names(self) -> tuple[str, str, str]:
        try:
            logging.getLogger('faker').setLevel(logging.CRITICAL)
            fake = faker.Faker('en_GB')
            # nickname = fake.first_name()
            # username = fake.last_name()

            # Generate Username
            chaine = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
            new_username = fake.random_sample(chaine, 9)
            username = ''.join(new_username)

            # Create realname XX F|M Department
            gender = fake.random_choices(['F','M'], 1)
            gender = ''.join(gender)
            
            if gender == 'F':
                nickname = fake.first_name_female()
            elif gender == 'M':
                nickname = fake.first_name_male()
            else:
                nickname = fake.first_name()

            age = random.randint(20, 60)
            fake_fr = faker.Faker(['fr_FR', 'en_GB'])
            department = fake_fr.department_name()
            realname = f'{age} {gender} {department}'

            if self.Clone.exists(nickname=nickname):
                caracteres = '0123456789'
                randomize = ''.join(random.choice(caracteres) for _ in range(2))
                nickname = nickname + str(randomize)
                self.Clone.insert(
                    self.Clone.CloneModel(alive=True, nickname=nickname, username=username, realname=realname, channels=[])
                    )
            else:
                self.Clone.insert(
                    self.Clone.CloneModel(alive=True, nickname=nickname, username=username, realname=realname, channels=[])
                    )

            return (nickname, username, realname)

        except AttributeError as ae:
            self.Logs.error(f'Attribute Error : {ae}')
        except Exception as err:
            self.Logs.error(err)

    def cmd(self, data:list) -> None:

        service_id = self.Config.SERVICE_ID                 # Defender serveur id
        cmd = list(data).copy()

        if len(cmd) < 2:
            return None

        match cmd[1]:

            case 'REPUTATION':
                pass

    def _hcmds(self, user:str, channel: any, cmd: list, fullcmd: list = []) -> None:

        try:
            command = str(cmd[0]).lower()
            fromuser = user

            dnickname = self.Config.SERVICE_NICKNAME            # Defender nickname

            match command:

                case 'clone':

                    if len(cmd) == 1:
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone connect 6 2.5')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone kill [all | nickname]')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone join [all | nickname] #channel')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone list')

                    option = str(cmd[1]).lower()

                    match option:

                        case 'connect':
                            try:
                                # clone connect 5
                                number_of_clones = int(cmd[2])
                                connection_interval = int(cmd[3]) if len(cmd) == 4 else 0.5
                                self.Base.create_thread(
                                    self.thread_create_clones_with_interval,
                                    (number_of_clones, [], connection_interval)
                                    )

                            except Exception as err:
                                self.Logs.error(f'{err}')
                                self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone connect [number of clone you want to connect] [Connection Interval]')
                                self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :Exemple /msg {dnickname} clone connect 6 2.5')

                        case 'kill':
                            try:
                                # clone kill [all | nickname]
                                clone_name = str(cmd[2])
                                clone_to_kill: list[str] = []

                                if clone_name.lower() == 'all':
                                    for clone in self.Clone.UID_CLONE_DB:
                                        self.Irc.send2socket(f':{dnickname} PRIVMSG {clone.nickname} :KILL')
                                        clone_to_kill.append(clone.nickname)
                                        clone.alive = False

                                    for clone_nickname in clone_to_kill:
                                        self.Clone.delete(clone_nickname)

                                    del clone_to_kill

                                else:
                                    if self.Clone.exists(clone_name):
                                        self.Irc.send2socket(f':{dnickname} PRIVMSG {clone_name} :KILL')
                                        self.Clone.kill(clone_name)
                                        self.Clone.delete(clone_name)

                            except Exception as err:
                                self.Logs.error(f'{err}')
                                self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone kill all')
                                self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone kill clone_nickname')

                        case 'join':
                            try:
                                # clone join [all | nickname] #channel
                                clone_name = str(cmd[2])
                                clone_channel_to_join = str(cmd[3])

                                if clone_name.lower() == 'all':
                                    self.Base.create_thread(self.thread_join_channels, (clone_channel_to_join, 2))
                                else:
                                    self.Base.create_thread(self.thread_join_channels, (clone_channel_to_join, 2, clone_name))

                            except Exception as err:
                                self.Logs.error(f'{err}')
                                self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone join all #channel')
                                self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone join clone_nickname #channel')

                        case 'list':
                            try:
                                clone_count = len(self.Clone.UID_CLONE_DB)
                                self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :>> Number of connected clones: {clone_count}')
                                for clone_name in self.Clone.UID_CLONE_DB:
                                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :>> Nickname: {clone_name.nickname} | Username: {clone_name.username} | Realname: {clone_name.realname} | Vhost: {clone_name.vhost} | Init: {clone_name.init} | Live: {clone_name.alive} | Connected: {clone_name.connected}')
                            except Exception as err:
                                self.Logs.error(f'{err}')

                        case 'say':
                            try:
                                # clone say clone_nickname #channel message
                                clone_name = str(cmd[2])
                                clone_channel = str(cmd[3]) if self.Base.Is_Channel(str(cmd[3])) else None

                                message = []
                                for i in range(4, len(cmd)):
                                    message.append(cmd[i])
                                final_message = ' '.join(message)

                                if clone_channel is None or not self.Clone.exists(clone_name):
                                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone say [clone_nickname] #channel message')
                                    return None
                                
                                if self.Clone.exists(clone_name):
                                    self.Irc.send2socket(f':{dnickname} PRIVMSG {clone_name} :SAY {clone_channel} {final_message}')

                            except Exception as err:
                                self.Logs.error(f'{err}')
                                self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone say [clone_nickname] #channel message')

                        case _:
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone connect 6')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone kill [all | nickname]')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone join [all | nickname] #channel')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone say [clone_nickname] #channel [message]')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone list')
        except IndexError as ie:
            self.Logs.error(f'Index Error: {ie}')
        except Exception as err:
            self.Logs.error(f'Index Error: {err}')
