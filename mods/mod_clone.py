from dataclasses import dataclass, fields, field
import random, faker, time
from datetime import datetime
from typing import Union
from core.irc import Irc
from core.connection import Connection

class Clone():

    @dataclass
    class ModConfModel:
        clone_count: int
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

        # Créer les nouvelles commandes du module
        self.commands_level = {
            1: ['clone_connect', 'clone_join', 'clone_kill', 'clone_list']
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
            # Variable qui va contenir les options de configuration du module Defender
            self.ModConfig = self.ModConfModel(
                                    clone_count=0,
                                    clone_nicknames=[]
                                )

            # Sync the configuration with core configuration (Mandatory)
            self.Base.db_sync_core_config(self.module_name, self.ModConfig)

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

        return None

    def thread_create_clones(self, nickname: str, username: str, channels:list, server_port:int, ssl:bool) -> None:

        Connection(server_port=server_port, nickname=nickname, username=username, channels=channels, ssl=ssl)

        return None

    def thread_join_channels(self, channel_name: str, wait: float, clone_name:str = None):

        if clone_name is None:
            for clone in self.ModConfig.clone_nicknames:
                self.Irc.send2socket(f':{self.Config.SERVICE_NICKNAME} PRIVMSG {clone} :JOIN {channel_name}')
                time.sleep(wait)
        else:
            for clone in self.ModConfig.clone_nicknames:
                if clone_name == clone:
                    self.Irc.send2socket(f':{self.Config.SERVICE_NICKNAME} PRIVMSG {clone} :JOIN {channel_name}')

    def generate_names(self) -> tuple[str, str]:
        try:
            fake = faker.Faker('en_GB')
            nickname = fake.first_name()
            username = fake.last_name()

            if not nickname in self.ModConfig.clone_nicknames:
                self.ModConfig.clone_nicknames.append(nickname)
            else:
                caracteres = '0123456789'
                randomize = ''.join(random.choice(caracteres) for _ in range(2))
                nickname = nickname + str(randomize)
                self.ModConfig.clone_nicknames.append(nickname)

            return (nickname, username)

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

        command = str(cmd[0]).lower()
        fromuser = user

        dnickname = self.Config.SERVICE_NICKNAME            # Defender nickname

        match command:

            case 'clone_connect':
                # clone_connect 25
                try:
                    number_of_clones = int(cmd[1])
                    for i in range(number_of_clones):
                        nickname, username = self.generate_names()
                        self.Base.create_thread(
                            self.thread_create_clones,
                            (nickname, username, [], 6697, True)
                            )

                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :{str(number_of_clones)} clones joined the network')

                except Exception as err:
                    self.Logs.error(f'{err}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone_connect [number of clone you want to connect]')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :Exemple /msg {dnickname} clone_kill 6')

            case 'clone_kill':
                try:
                    clone_name = str(cmd[1])

                    if clone_name.lower() == 'all':
                        for clone in self.ModConfig.clone_nicknames:
                            self.Irc.send2socket(f':{dnickname} PRIVMSG {clone} :KILL')
                            self.ModConfig.clone_nicknames.remove(clone)
                    else:
                        for clone in self.ModConfig.clone_nicknames:
                            if clone_name == clone:
                                self.Irc.send2socket(f':{dnickname} PRIVMSG {clone} :KILL')
                                self.ModConfig.clone_nicknames.remove(clone)

                except Exception as err:
                    self.Logs.error(f'{err}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone_kill all')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone_kill [clone_name]')

            case 'clone_join':
                try:
                    # clone_join nickname #channel
                    clone_name = str(cmd[1])
                    clone_channel_to_join = cmd[2]

                    if clone_name.lower() == 'all':
                        self.Base.create_thread(self.thread_join_channels, (clone_channel_to_join, 4))
                    else:
                        self.Base.create_thread(self.thread_join_channels, (clone_channel_to_join, 4, clone_name))

                except Exception as err:
                    self.Logs.error(f'{err}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone_join all #channel')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone_join clone_nickname #channel')

            case 'clone_list':

                for clone_name in self.ModConfig.clone_nicknames:
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :>> {clone_name}')
