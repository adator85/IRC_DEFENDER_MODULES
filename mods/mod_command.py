from dataclasses import dataclass, fields
from core.irc import Irc

class Command():

    @dataclass
    class ModConfModel:
        """The Model containing the module parameters
        """
        pass

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
            1: ['join', 'part'],
            2: ['owner', 'deowner', 'op', 'deop', 'halfop', 'dehalfop', 'voice', 
                'devoice', 'opall', 'deopall', 'devoiceall', 'voiceall', 'ban', 
                'unban','kick', 'kickban', 'umode', 'svsjoin', 'svspart', 'svsnick']
        }

        # Init the module
        self.__init_module()

        # Log the module
        self.Logs.debug(f'Module {self.module_name} loaded ...')

    def __init_module(self) -> None:

        # Insert module commands into the core one (Mandatory)
        self.__set_commands(self.commands_level)

        # Create you own tables (Mandatory)
        self.__create_tables()

        # Load module configuration and sync with core one (Mandatory)
        self.__load_module_configuration()
        # End of mandatory methods you can start your customization #

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

        table_logs = '''CREATE TABLE IF NOT EXISTS test_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            server_msg TEXT
            )
        '''

        self.Base.db_execute_query(table_logs)
        return None

    def __load_module_configuration(self) -> None:
        """### Load Module Configuration
        """
        try:
            # Build the default configuration model (Mandatory)
            self.ModConfig = self.ModConfModel()

            # Sync the configuration with core configuration (Mandatory)
            self.Base.db_sync_core_config(self.module_name, self.ModConfig)

            return None

        except TypeError as te:
            self.Logs.critical(te)

    def __update_configuration(self, param_key: str, param_value: str):
        """Update the local and core configuration

        Args:
            param_key (str): The parameter key
            param_value (str): The parameter value
        """
        self.Base.db_update_core_config(self.module_name, self.ModConfig, param_key, param_value)

    def unload(self) -> None:

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
            if insert.rowcount >=0:
                return True
            else:
                return False
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

    def cmd(self, data:list) -> None:

        return None

    def _hcmds(self, user:str, channel: any, cmd: list, fullcmd: list = []) -> None:

        command = str(cmd[0]).lower()
        dnickname = self.Config.SERVICE_NICKNAME
        service_id = self.Config.SERVICE_ID
        dchanlog = self.Config.SERVICE_CHANLOG
        fromuser = user
        fromchannel = channel

        match command:

            case 'deopall':
                try:
                    self.Irc.send2socket(f":{service_id} SVSMODE {fromchannel} -o")

                except IndexError as e:
                    self.Logs.warning(f'_hcmd OP: {str(e)}')
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'devoiceall':
                try:
                    self.Irc.send2socket(f":{service_id} SVSMODE {fromchannel} -v")

                except IndexError as e:
                    self.Logs.warning(f'_hcmd OP: {str(e)}')
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'voiceall':
                try:
                    chan_info = self.Channel.get_Channel(fromchannel)
                    set_mode = 'v'
                    mode:str = ''
                    users:str = ''
                    uids_split = [chan_info.uids[i:i + 6] for i in range(0, len(chan_info.uids), 6)]

                    self.Irc.send2socket(f":{service_id} MODE {fromchannel} +{set_mode} {dnickname}")
                    for uid in uids_split:
                        for i in range(0, len(uid)):
                            mode += set_mode
                            users += f'{self.User.get_nickname(self.Base.clean_uid(uid[i]))} '
                            if i == len(uid) - 1:
                                self.Irc.send2socket(f":{service_id} MODE {fromchannel} +{mode} {users}")
                                mode = ''
                                users = ''
                except IndexError as e:
                    self.Logs.warning(f'_hcmd OP: {str(e)}')
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'opall':
                try:
                    chan_info = self.Channel.get_Channel(fromchannel)
                    set_mode = 'o'
                    mode:str = ''
                    users:str = ''
                    uids_split = [chan_info.uids[i:i + 6] for i in range(0, len(chan_info.uids), 6)]

                    self.Irc.send2socket(f":{service_id} MODE {fromchannel} +{set_mode} {dnickname}")
                    for uid in uids_split:
                        for i in range(0, len(uid)):
                            mode += set_mode
                            users += f'{self.User.get_nickname(self.Base.clean_uid(uid[i]))} '
                            if i == len(uid) - 1:
                                self.Irc.send2socket(f":{service_id} MODE {fromchannel} +{mode} {users}")
                                mode = ''
                                users = ''
                except IndexError as e:
                    self.Logs.warning(f'_hcmd OP: {str(e)}')
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'op':
                # /mode #channel +o user
                # .op #channel user
                # /msg dnickname op #channel user
                # [':adator', 'PRIVMSG', '#services', ':.o', '#services', 'dktmb']
                try:
                    if fromchannel is None:
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} op [#SALON] [NICKNAME]')
                        return False

                    if len(cmd) == 1:
                        self.Irc.send2socket(f":{dnickname} MODE {fromchannel} +o {fromuser}")
                        return True

                    # deop nickname
                    if len(cmd) == 2:
                        nickname = cmd[1]
                        self.Irc.send2socket(f":{service_id} MODE {fromchannel} +o {nickname}")
                        return True

                    nickname = cmd[2]
                    self.Irc.send2socket(f":{service_id} MODE {fromchannel} +o {nickname}")

                except IndexError as e:
                    self.Logs.warning(f'_hcmd OP: {str(e)}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} op [#SALON] [NICKNAME]')
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'deop':
                # /mode #channel -o user
                # .deop #channel user
                try:
                    if fromchannel is None:
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} deop [#SALON] [NICKNAME]')
                        return False

                    if len(cmd) == 1:
                        self.Irc.send2socket(f":{service_id} MODE {fromchannel} -o {fromuser}")
                        return True

                    # deop nickname
                    if len(cmd) == 2:
                        nickname = cmd[1]
                        self.Irc.send2socket(f":{service_id} MODE {fromchannel} -o {nickname}")
                        return True

                    nickname = cmd[2]
                    self.Irc.send2socket(f":{service_id} MODE {fromchannel} -o {nickname}")

                except IndexError as e:
                    self.Logs.warning(f'_hcmd DEOP: {str(e)}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} deop [#SALON] [NICKNAME]')
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'owner':
                # /mode #channel +q user
                # .owner #channel user
                try:
                    if fromchannel is None:
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} owner [#SALON] [NICKNAME]')
                        return False

                    if len(cmd) == 1:
                        self.Irc.send2socket(f":{service_id} MODE {fromchannel} +q {fromuser}")
                        return True

                    # owner nickname
                    if len(cmd) == 2:
                        nickname = cmd[1]
                        self.Irc.send2socket(f":{service_id} MODE {fromchannel} +q {nickname}")
                        return True

                    nickname = cmd[2]
                    self.Irc.send2socket(f":{service_id} MODE {fromchannel} +q {nickname}")

                except IndexError as e:
                    self.Logs.warning(f'_hcmd OWNER: {str(e)}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} owner [#SALON] [NICKNAME]')
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'deowner':
                # /mode #channel -q user
                # .deowner #channel user
                try:
                    if fromchannel is None:
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} deowner [#SALON] [NICKNAME]')
                        return False

                    if len(cmd) == 1:
                        self.Irc.send2socket(f":{service_id} MODE {fromchannel} -q {fromuser}")
                        return True

                    # deowner nickname
                    if len(cmd) == 2:
                        nickname = cmd[1]
                        self.Irc.send2socket(f":{service_id} MODE {fromchannel} -q {nickname}")
                        return True

                    nickname = cmd[2]
                    self.Irc.send2socket(f":{service_id} MODE {fromchannel} -q {nickname}")

                except IndexError as e:
                    self.Logs.warning(f'_hcmd DEOWNER: {str(e)}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} deowner [#SALON] [NICKNAME]')
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'halfop':
                # /mode #channel +h user
                # .halfop #channel user
                try:
                    if fromchannel is None:
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} halfop [#SALON] [NICKNAME]')
                        return False

                    if len(cmd) == 1:
                        self.Irc.send2socket(f":{service_id} MODE {fromchannel} +h {fromuser}")
                        return True

                    # deop nickname
                    if len(cmd) == 2:
                        nickname = cmd[1]
                        self.Irc.send2socket(f":{service_id} MODE {fromchannel} +h {nickname}")
                        return True

                    nickname = cmd[2]
                    self.Irc.send2socket(f":{service_id} MODE {fromchannel} +h {nickname}")

                except IndexError as e:
                    self.Logs.warning(f'_hcmd halfop: {str(e)}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} halfop [#SALON] [NICKNAME]')
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'dehalfop':
                # /mode #channel -h user
                # .dehalfop #channel user
                try:
                    if fromchannel is None:
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} dehalfop [#SALON] [NICKNAME]')
                        return False

                    if len(cmd) == 1:
                        self.Irc.send2socket(f":{service_id} MODE {fromchannel} -h {fromuser}")
                        return True

                    # dehalfop nickname
                    if len(cmd) == 2:
                        nickname = cmd[1]
                        self.Irc.send2socket(f":{service_id} MODE {fromchannel} -h {nickname}")
                        return True

                    nickname = cmd[2]
                    self.Irc.send2socket(f":{service_id} MODE {fromchannel} -h {nickname}")

                except IndexError as e:
                    self.Logs.warning(f'_hcmd DEHALFOP: {str(e)}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} dehalfop [#SALON] [NICKNAME]')
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'voice':
                # /mode #channel +v user
                # .voice #channel user
                try:
                    if fromchannel is None:
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} voice [#SALON] [NICKNAME]')
                        return False

                    if len(cmd) == 1:
                        self.Irc.send2socket(f":{service_id} MODE {fromchannel} +v {fromuser}")
                        return True

                    # voice nickname
                    if len(cmd) == 2:
                        nickname = cmd[1]
                        self.Irc.send2socket(f":{service_id} MODE {fromchannel} +v {nickname}")
                        return True

                    nickname = cmd[2]
                    self.Irc.send2socket(f":{service_id} MODE {fromchannel} +v {nickname}")

                except IndexError as e:
                    self.Logs.warning(f'_hcmd VOICE: {str(e)}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} voice [#SALON] [NICKNAME]')
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'devoice':
                # /mode #channel -v user
                # .devoice #channel user
                try:
                    if fromchannel is None:
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} devoice [#SALON] [NICKNAME]')
                        return False

                    if len(cmd) == 1:
                        self.Irc.send2socket(f":{service_id} MODE {fromchannel} -v {fromuser}")
                        return True

                    # dehalfop nickname
                    if len(cmd) == 2:
                        nickname = cmd[1]
                        self.Irc.send2socket(f":{service_id} MODE {fromchannel} -v {nickname}")
                        return True

                    nickname = cmd[2]
                    self.Irc.send2socket(f":{service_id} MODE {fromchannel} -v {nickname}")

                except IndexError as e:
                    self.Logs.warning(f'_hcmd DEVOICE: {str(e)}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} devoice [#SALON] [NICKNAME]')
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'ban':
                # .ban #channel nickname
                try:
                    sentchannel = str(cmd[1]) if self.Base.Is_Channel(cmd[1]) else None
                    if sentchannel is None:
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} ban [#SALON] [NICKNAME]')
                        return False

                    nickname = cmd[2]

                    self.Irc.send2socket(f":{service_id} MODE {sentchannel} +b {nickname}!*@*")
                    self.Logs.debug(f'{fromuser} has banned {nickname} from {sentchannel}')
                except IndexError as e:
                    self.Logs.warning(f'_hcmd BAN: {str(e)}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} ban [#SALON] [NICKNAME]')
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'unban':
                # .unban #channel nickname
                try:
                    sentchannel = str(cmd[1]) if self.Base.Is_Channel(cmd[1]) else None
                    if sentchannel is None:
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} ban [#SALON] [NICKNAME]')
                        return False
                    nickname = cmd[2]

                    self.Irc.send2socket(f":{service_id} MODE {sentchannel} -b {nickname}!*@*")
                    self.Logs.debug(f'{fromuser} has unbanned {nickname} from {sentchannel}')

                except IndexError as e:
                    self.Logs.warning(f'_hcmd UNBAN: {str(e)}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} unban [#SALON] [NICKNAME]')
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'kick':
                # .kick #channel nickname reason
                try:
                    sentchannel = str(cmd[1]) if self.Base.Is_Channel(cmd[1]) else None
                    if sentchannel is None:
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} ban [#SALON] [NICKNAME]')
                        return False
                    nickname = cmd[2]
                    reason = []

                    for i in range(3, len(cmd)):
                        reason.append(cmd[i]) 

                    final_reason = ' '.join(reason)

                    self.Irc.send2socket(f":{service_id} KICK {sentchannel} {nickname} {final_reason}")
                    self.Logs.debug(f'{fromuser} has kicked {nickname} from {sentchannel} : {final_reason}')

                except IndexError as e:
                    self.Logs.warning(f'_hcmd KICK: {str(e)}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} kick [#SALON] [NICKNAME] [REASON]')
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'kickban':
                # .kickban #channel nickname reason
                try:
                    sentchannel = str(cmd[1]) if self.Base.Is_Channel(cmd[1]) else None
                    if sentchannel is None:
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} ban [#SALON] [NICKNAME]')
                        return False
                    nickname = cmd[2]
                    reason = []

                    for i in range(3, len(cmd)):
                        reason.append(cmd[i]) 

                    final_reason = ' '.join(reason)

                    self.Irc.send2socket(f":{service_id} KICK {sentchannel} {nickname} {final_reason}")
                    self.Irc.send2socket(f":{service_id} MODE {sentchannel} +b {nickname}!*@*")
                    self.Logs.debug(f'{fromuser} has kicked and banned {nickname} from {sentchannel} : {final_reason}')

                except IndexError as e:
                    self.Logs.warning(f'_hcmd KICKBAN: {str(e)}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} kickban [#SALON] [NICKNAME] [REASON]')
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'join':

                try:
                    sent_channel = str(cmd[1]) if self.Base.Is_Channel(cmd[1]) else None
                    if sent_channel is None:
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :{self.Config.SERVICE_PREFIX}JOIN #channel')
                        return False

                    self.Irc.send2socket(f':{service_id} JOIN {sent_channel}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : {dnickname} JOINED {sent_channel}')
                    self.Base.db_query_channel('add', self.module_name, sent_channel)

                except IndexError as ie:
                    self.Logs.error(f'{ie}')
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'part':

                try:
                    sent_channel = str(cmd[1]) if self.Base.Is_Channel(cmd[1]) else None
                    if sent_channel is None:
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :{self.Config.SERVICE_PREFIX}PART #channel')
                        return False

                    if sent_channel ==  dchanlog:
                        self.Irc.send2socket(f":{dnickname} NOTICE {fromuser} : {dnickname} CAN'T LEFT {sent_channel} AS IT IS LOG CHANNEL")
                        return False

                    self.Irc.send2socket(f':{service_id} PART {sent_channel}')
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : {dnickname} LEFT {sent_channel}')
                    self.Base.db_query_channel('del', self.module_name, sent_channel)

                except IndexError as ie:
                    self.Logs.error(f'{ie}')
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'umode':
                try:
                    # .umode nickname +mode
                    nickname = str(cmd[1])
                    umode = str(cmd[2])

                    self.Irc.send2socket(f':{dnickname} SVSMODE {nickname} {umode}')
                except KeyError as ke:
                    self.Base.logs.error(ke)
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'svsjoin':
                try:
                    # .svsjoin nickname #channel
                    nickname = str(cmd[1])
                    channel = str(cmd[2])
                    if len(cmd) != 3:
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : /msg {dnickname} SVSJOIN nickname #channel')
                        return None

                    self.Irc.send2socket(f':{self.Config.SERVEUR_ID} SVSJOIN {nickname} {channel}')
                except KeyError as ke:
                    self.Base.logs.error(ke)
                except Exception as err:
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : /msg {dnickname} SVSJOIN nickname #channel')
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'svspart':
                try:
                    # .svspart nickname #channel
                    nickname = str(cmd[1])
                    channel = str(cmd[2])
                    if len(cmd) != 3:
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : /msg {dnickname} SVSPART nickname #channel')
                        return None

                    self.Irc.send2socket(f':{self.Config.SERVEUR_ID} SVSPART {nickname} {channel}')
                except KeyError as ke:
                    self.Base.logs.error(ke)
                except Exception as err:
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : /msg {dnickname} SVSPART nickname #channel')
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'svsnick':
                try:
                    # .svsnick nickname newnickname
                    nickname = str(cmd[1])
                    newnickname = str(cmd[2])
                    unixtime = self.Base.get_unixtime()

                    if self.User.get_nickname(nickname) is None:
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : This nickname do not exist')
                        return None

                    if len(cmd) != 3:
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : /msg {dnickname} SVSNICK nickname newnickname')
                        return None

                    self.Irc.send2socket(f':{self.Config.SERVEUR_ID} SVSNICK {nickname} {newnickname} {unixtime}')
                except KeyError as ke:
                    self.Base.logs.error(ke)
                except Exception as err:
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} : /msg {dnickname} SVSNICK nickname newnickname')
                    self.Logs.warning(f'Unknown Error: {str(err)}')
