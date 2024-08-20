from core.irc import Irc
import re
from dataclasses import dataclass, field

# Activer le systeme sur un salon (activate #salon)
#   Le service devra se connecter au salon
#   Le service devra se mettre en op
# Soumettre un nom de user (submit nickname)
# voter pour un ban (vote_for)
# voter contre un ban (vote_against)



class Votekick():

    @dataclass
    class VoteChannelModel:
        channel_name: str
        target_user: str
        voter_users: list
        vote_for: int
        vote_against: int
    
    VOTE_CHANNEL_DB:list[VoteChannelModel] = []

    def __init__(self, ircInstance:Irc) -> None:
        # Add Irc Object to the module
        self.Irc = ircInstance

        # Add Global Configuration to the module
        self.Config = ircInstance.Config

        # Add Base object to the module
        self.Base = ircInstance.Base

        # Add logs object to the module
        self.Logs = ircInstance.Base.logs

        # Add User object to the module
        self.User = ircInstance.User

        # Add Channel object to the module
        self.Channel = ircInstance.Channel

        # Créer les nouvelles commandes du module
        self.commands_level = {
            0: ['vote_for', 'vote_against'],
            1: ['activate', 'deactivate', 'submit', 'vote_stat', 'vote_verdict', 'vote_cancel']
        }

        # Init the module
        self.__init_module()

        # Log the module
        self.Logs.debug(f'Module {self.__class__.__name__} loaded ...')

    def __init_module(self) -> None:

        self.__set_commands(self.commands_level)
        self.__create_tables()
        self.join_saved_channels()

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

        table_logs = '''CREATE TABLE IF NOT EXISTS votekick_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            server_msg TEXT
            ) 
        '''

        table_vote = '''CREATE TABLE IF NOT EXISTS votekick_channel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            channel TEXT
            )
        '''

        self.Base.db_execute_query(table_logs)
        self.Base.db_execute_query(table_vote)
        return None

    def unload(self) -> None:
        try:
            for chan in self.VOTE_CHANNEL_DB:
                self.Irc.send2socket(f":{self.Config.SERVICE_NICKNAME} PART {chan.channel_name}")

            self.VOTE_CHANNEL_DB = []
            self.Logs.debug(f'Delete memory DB VOTE_CHANNEL_DB: {self.VOTE_CHANNEL_DB}')

            return None
        except UnboundLocalError as ne:
            self.Logs.error(f'{ne}')
        except NameError as ue:
            self.Logs.error(f'{ue}')
        except:
            self.Logs.error('Error on the module')

    def init_vote_system(self, channel: str) -> bool:

        response = False
        for chan in self.VOTE_CHANNEL_DB:
            if chan.channel_name == channel:
                chan.target_user = ''
                chan.voter_users = []
                chan.vote_against = 0
                chan.vote_for = 0
                response = True

        return response

    def insert_vote_channel(self, ChannelObject: VoteChannelModel) -> bool:
        result = False
        found = False
        for chan in self.VOTE_CHANNEL_DB:
            if chan.channel_name == ChannelObject.channel_name:
                found = True

        if not found:
            self.VOTE_CHANNEL_DB.append(ChannelObject)
            self.Logs.debug(f"The channel has been added {ChannelObject}")
            self.db_add_vote_channel(ChannelObject.channel_name)

        return result

    def db_add_vote_channel(self, channel:str) -> bool:
        """Cette fonction ajoute les salons ou seront autoriser les votes

        Args:
            channel (str): le salon à enregistrer.
        """
        current_datetime = self.Base.get_datetime()
        mes_donnees = {'channel': channel}

        response = self.Base.db_execute_query("SELECT id FROM votekick_channel WHERE channel = :channel", mes_donnees)

        isChannelExist = response.fetchone()

        if isChannelExist is None:
            mes_donnees = {'datetime': current_datetime, 'channel': channel}
            insert = self.Base.db_execute_query(f"INSERT INTO votekick_channel (datetime, channel) VALUES (:datetime, :channel)", mes_donnees)
            if insert.rowcount > 0:
                return True
            else:
                return False
        else:
            return False

    def db_delete_vote_channel(self, channel: str) -> bool:
        """Cette fonction supprime les salons de join de Defender

        Args:
            channel (str): le salon à enregistrer.
        """
        mes_donnes = {'channel': channel}
        response = self.Base.db_execute_query("DELETE FROM votekick_channel WHERE channel = :channel", mes_donnes)
        
        affected_row = response.rowcount

        if affected_row > 0:
            return True
        else:
            return False

    def join_saved_channels(self) -> None:

        result = self.Base.db_execute_query("SELECT id, channel FROM votekick_channel")
        channels = result.fetchall()
        unixtime = self.Base.get_unixtime()

        for channel in channels:
            id, chan = channel
            self.insert_vote_channel(self.VoteChannelModel(channel_name=chan, target_user='', voter_users=[], vote_for=0, vote_against=0))
            self.Irc.send2socket(f":{self.Config.SERVEUR_ID} SJOIN {unixtime} {chan} + :{self.Config.SERVICE_ID}")
            self.Irc.send2socket(f":{self.Config.SERVICE_NICKNAME} SAMODE {chan} +o {self.Config.SERVICE_NICKNAME}")

        return None

    def is_vote_ongoing(self, channel: str) -> bool:

        response = False
        for vote in self.VOTE_CHANNEL_DB:
            if vote.channel_name == channel:
                if vote.target_user:
                    response = True

        return response

    def timer_vote_verdict(self, channel: str) -> None:

        dnickname = self.Config.SERVICE_NICKNAME

        for chan in self.VOTE_CHANNEL_DB:
            if chan.channel_name == channel:
                target_user = self.User.get_nickname(chan.target_user)
                if chan.vote_for > chan.vote_against:
                    self.Irc.send2socket(f':{dnickname} PRIVMSG {channel} :The user {self.Config.CONFIG_COLOR["gras"]}{target_user}{self.Config.CONFIG_COLOR["nogc"]}  will be kicked from this channel')
                    self.Irc.send2socket(f":{dnickname} KICK {channel} {target_user} Following the vote, you are not welcome in {channel}")
                    self.Channel.delete_user_from_channel(channel, self.User.get_uid(target_user))
                elif chan.vote_for <= chan.vote_against:
                    self.Irc.send2socket(f':{dnickname} PRIVMSG {channel} :This user will stay on this channel')

                # Init the system
                if self.init_vote_system(channel):
                    self.Irc.send2socket(f':{dnickname} PRIVMSG {channel} :System vote re initiated')

        return None

    def cmd(self, data:list) -> None:
        cmd = list(data).copy()

        match cmd[2]:
            case 'SJOIN':
                pass
            case _:
                pass

        return None

    def _hcmds(self, user:str, cmd: list, fullcmd: list = []) -> None:
        # cmd is the command starting from the user command
        # full cmd is sending the entire server response

        command = str(cmd[0]).lower()
        dnickname = self.Config.SERVICE_NICKNAME
        fromuser = user

        if len(fullcmd) >= 3:
            fromchannel = str(fullcmd[2]).lower() if self.Base.Is_Channel(str(fullcmd[2]).lower()) else None
        else:
            fromchannel = None

        if len(cmd) >= 2:
            sentchannel = str(cmd[1]).lower() if self.Base.Is_Channel(str(cmd[1]).lower()) else None
        else:
            sentchannel = None

        if not fromchannel is None:
            channel = fromchannel
        elif not sentchannel is None:
            channel = sentchannel
        else:
            channel = None

        match command:

            case 'vote_cancel':
                try:
                    if channel is None:
                        self.Logs.error(f"The channel is not known, defender can't cancel the vote")
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :You need to specify the channel => /msg {dnickname} vote_cancel #channel')

                    for vote in self.VOTE_CHANNEL_DB:
                        if vote.channel_name == channel:
                            self.init_vote_system(channel)
                            self.Irc.send2socket(f':{dnickname} PRIVMSG {channel} :Vote system re-initiated')

                except IndexError as ke:
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} vote_cancel #channel')
                    self.Logs.error(f'Index Error: {ke}')

            case 'vote_for':
                try:
                    # vote_for
                    channel = str(fullcmd[2]).lower()
                    for chan in self.VOTE_CHANNEL_DB:
                        if chan.channel_name == channel:
                            if fromuser in chan.voter_users:
                                self.Irc.send2socket(f':{dnickname} PRIVMSG {channel} :You already submitted a vote')
                            else:
                                chan.vote_for += 1
                                chan.voter_users.append(fromuser)
                                self.Irc.send2socket(f':{dnickname} PRIVMSG {channel} :Vote recorded, thank you')

                except KeyError as ke:
                    self.Logs.error(f'Key Error: {ke}')
                except IndexError as ie:
                    self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} vote_cancel #channel')
                    self.Logs.error(f'Index Error: {ie}')

            case 'vote_against':
                try:
                    # vote_against
                    channel = str(fullcmd[2]).lower()
                    for chan in self.VOTE_CHANNEL_DB:
                        if chan.channel_name == channel:
                            if fromuser in chan.voter_users:
                                self.Irc.send2socket(f':{dnickname} PRIVMSG {channel} :You already submitted a vote')
                            else:
                                chan.vote_against += 1
                                chan.voter_users.append(fromuser)
                                self.Irc.send2socket(f':{dnickname} PRIVMSG {channel} :Vote recorded, thank you')

                except KeyError as ke:
                    self.Logs.error(f'Key Error: {ke}')

            case 'vote_stat':
                try:
                    # channel = str(fullcmd[2]).lower()
                    for chan in self.VOTE_CHANNEL_DB:
                        if chan.channel_name == channel:
                            self.Irc.send2socket(f':{dnickname} PRIVMSG {channel} :Channel: {chan.channel_name} | Target: {self.User.get_nickname(chan.target_user)} | For: {chan.vote_for} | Against: {chan.vote_against} | Number of voters: {str(len(chan.voter_users))}')

                except KeyError as ke:
                    self.Logs.error(f'Key Error: {ke}')

            case 'vote_verdict':
                try:
                    # channel = str(fullcmd[2]).lower()
                    for chan in self.VOTE_CHANNEL_DB:
                        if chan.channel_name == channel:
                            target_user = self.User.get_nickname(chan.target_user)
                            if chan.vote_for > chan.vote_against:
                                self.Irc.send2socket(f':{dnickname} PRIVMSG {channel} :The user {self.Config.CONFIG_COLOR["gras"]}{target_user}{self.Config.CONFIG_COLOR["nogc"]}  will be kicked from this channel')
                                self.Irc.send2socket(f":{dnickname} KICK {channel} {target_user} Following the vote, you are not welcome in {channel}")
                            elif chan.vote_for <= chan.vote_against:
                                self.Irc.send2socket(f':{dnickname} PRIVMSG {channel} :This user will stay on this channel')
                            
                            # Init the system
                            if self.init_vote_system(channel):
                                self.Irc.send2socket(f':{dnickname} PRIVMSG {channel} :System vote re initiated')

                except KeyError as ke:
                    self.Logs.error(f'Key Error: {ke}')

            case 'submit':
                # submit nickname
                try:
                    nickname_submitted = cmd[1]
                    # channel = str(fullcmd[2]).lower()
                    uid_submitted = self.User.get_uid(nickname_submitted)
                    user_submitted = self.User.get_User(nickname_submitted)

                    # check if there is an ongoing vote
                    if self.is_vote_ongoing(channel):
                        for vote in self.VOTE_CHANNEL_DB:
                            if vote.channel_name == channel:
                                ongoing_user = self.User.get_nickname(vote.target_user)

                        self.Irc.send2socket(f':{dnickname} PRIVMSG {channel} :There is an ongoing vote on {ongoing_user}')
                        return False

                    # check if the user exist
                    if user_submitted is None:
                        self.Irc.send2socket(f':{dnickname} PRIVMSG {channel} :This nickname <{nickname_submitted}> do not exist')
                        return False

                    uid_cleaned = self.Base.clean_uid(uid_submitted)
                    ChannelInfo = self.Channel.get_Channel(channel)

                    clean_uids_in_channel: list = []
                    for uid in ChannelInfo.uids:
                        clean_uids_in_channel.append(self.Base.clean_uid(uid))

                    if not uid_cleaned in clean_uids_in_channel:
                        self.Irc.send2socket(f':{dnickname} PRIVMSG {channel} :This nickname <{nickname_submitted}> is not available in this channel')
                        return False

                    # check if Ircop or Service or Bot
                    pattern = fr'[o|B|S]'
                    operator_user = re.findall(pattern, user_submitted.umodes)
                    if operator_user:
                        self.Irc.send2socket(f':{dnickname} PRIVMSG {channel} :You cant vote for this user ! he/she is protected')
                        return False

                    for chan in self.VOTE_CHANNEL_DB:
                        if chan.channel_name == channel:
                            chan.target_user = self.User.get_uid(nickname_submitted)

                    self.Irc.send2socket(f':{dnickname} PRIVMSG {channel} :{nickname_submitted} has been targeted for a vote')

                    self.Base.create_timer(60, self.timer_vote_verdict, (channel, ))
                    self.Irc.send2socket(f':{dnickname} PRIVMSG {channel} :This vote will end after 60 secondes')

                except KeyError as ke:
                    self.Logs.error(f'Key Error: {ke}')
                except TypeError as te:
                    self.Logs.error(te)

            case 'activate':
                try:
                    # activate #channel
                    # channel = str(cmd[1]).lower()

                    self.insert_vote_channel(
                        self.VoteChannelModel(
                            channel_name=channel, 
                            target_user='',
                            voter_users=[],
                            vote_for=0,
                            vote_against=0
                            )
                        )

                    self.Irc.send2socket(f":{dnickname} JOIN {channel}")
                    self.Irc.send2socket(f":{dnickname} SAMODE {channel} +o {dnickname}")
                    self.Irc.send2socket(f":{dnickname} PRIVMSG {channel} :You can now use !submit <nickname> to decide if he will stay or not on this channel ")

                except KeyError as ke:
                    self.Logs.error(f"Key Error : {ke}")

            case 'deactivate':
                try:
                    # deactivate #channel
                    # channel = str(cmd[1]).lower()

                    self.Irc.send2socket(f":{dnickname} SAMODE {channel} -o {dnickname}")
                    self.Irc.send2socket(f":{dnickname} PART {channel}")

                    for chan in self.VOTE_CHANNEL_DB:
                        if chan.channel_name == channel:
                            self.VOTE_CHANNEL_DB.remove(chan)
                            self.db_delete_vote_channel(chan.channel_name)

                    self.Logs.debug(f"Test logs ready")
                except KeyError as ke:
                    self.Logs.error(f"Key Error : {ke}")