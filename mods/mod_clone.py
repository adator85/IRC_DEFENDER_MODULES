from dataclasses import dataclass, fields, field
import random, faker, time
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

        return None

    def thread_create_clones(self, nickname: str, username: str, channels: list, server_port: int, ssl: bool) -> None:

        Connection(server_port=server_port, nickname=nickname, username=username, channels=channels, CloneObject=self.Clone, ssl=ssl)

        return None

    def thread_join_channels(self, channel_name: str, wait: float, clone_name:str = None):

        if clone_name is None:
            for clone in self.Clone.UID_CLONE_DB:
                self.Irc.send2socket(f':{self.Config.SERVICE_NICKNAME} PRIVMSG {clone.nickname} :JOIN {channel_name}')
                time.sleep(wait)
        else:
            for clone in self.Clone.UID_CLONE_DB:
                if clone_name == clone.nickname:
                    self.Irc.send2socket(f':{self.Config.SERVICE_NICKNAME} PRIVMSG {clone.nickname} :JOIN {channel_name}')
                    time.sleep(wait)

    def generate_names(self) -> tuple[str, str]:
        try:
            fake = faker.Faker('en_GB')
            nickname = fake.first_name()
            username = fake.last_name()

            if self.Clone.exists(nickname=nickname):
                caracteres = '0123456789'
                randomize = ''.join(random.choice(caracteres) for _ in range(2))
                nickname = nickname + str(randomize)
                self.Clone.insert(
                    self.Clone.CloneModel(alive=True, nickname=nickname, username=username)
                    )
            else:
                self.Clone.insert(
                    self.Clone.CloneModel(alive=True, nickname=nickname, username=username)
                    )

            # if not nickname in self.ModConfig.clone_nicknames:
            #     self.ModConfig.clone_nicknames.append(nickname)
            # else:
            #     caracteres = '0123456789'
            #     randomize = ''.join(random.choice(caracteres) for _ in range(2))
            #     nickname = nickname + str(randomize)
            #     self.ModConfig.clone_nicknames.append(nickname)

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

            case 'clone':
                option = str(cmd[1]).lower()

                if len(command) == 1:
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone connect 6')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone kill [all | nickname]')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone join [all | nickname] #channel')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone list')

                match option:

                    case 'connect':
                        try:
                            number_of_clones = int(cmd[2])
                            for i in range(number_of_clones):
                                nickname, username = self.generate_names()
                                self.Base.create_thread(
                                    self.thread_create_clones,
                                    (nickname, username, [], 6697, True)
                                    )

                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :{str(number_of_clones)} clones joined the network')
                        except Exception as err:
                            self.Logs.error(f'{err}')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} clone connect [number of clone you want to connect]')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :Exemple /msg {dnickname} clone connect 6')

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
                            for clone_name in self.Clone.UID_CLONE_DB:
                                self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :>> {clone_name.nickname} | {clone_name.username}')
                            pass
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
