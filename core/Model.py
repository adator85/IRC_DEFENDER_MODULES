from dataclasses import dataclass, field
from datetime import datetime
from typing import Union
from core.base import Base

class User:

    @dataclass
    class UserModel:
        uid: str
        nickname: str
        username: str
        hostname: str
        umodes: str
        vhost: str
        isWebirc: bool
        remote_ip: str
        score_connexion: int
        connexion_datetime: datetime = field(default=datetime.now())

    UID_DB: list[UserModel] = []

    def __init__(self, Base: Base) -> None:
        self.log = Base.logs
        pass

    def insert(self, newUser: UserModel) -> bool:
        """Insert a new User object

        Args:
            newUser (UserModel): New userModel object

        Returns:
            bool: True if inserted
        """
        result = False
        exist = False

        for record in self.UID_DB:
            if record.uid == newUser.uid:
                exist = True
                self.log.debug(f'{record.uid} already exist')

        if not exist:
            self.UID_DB.append(newUser)
            result = True
            self.log.debug(f'New User Created: ({newUser})')

        if not result:
            self.log.critical(f'The User Object was not inserted {newUser}')

        return result

    def update(self, uid: str, newNickname: str) -> bool:
        """Update the nickname starting from the UID

        Args:
            uid (str): UID of the user
            newNickname (str): New nickname

        Returns:
            bool: True if updated
        """
        result = False

        for record in self.UID_DB:
            if record.uid == uid:
                record.nickname = newNickname
                result = True
                self.log.debug(f'UID ({record.uid}) has been updated with new nickname {newNickname}')

        if not result:
            self.log.critical(f'The new nickname {newNickname} was not updated, uid = {uid}')

        return result

    def delete(self, uid: str) -> bool:
        """Delete the User starting from the UID

        Args:
            uid (str): UID of the user

        Returns:
            bool: True if deleted
        """
        result = False

        for record in self.UID_DB:
            if record.uid == uid:
                self.UID_DB.remove(record)
                result = True
                self.log.debug(f'UID ({record.uid}) has been deleted')

        if not result:
            self.log.critical(f'The UID {uid} was not deleted')

        return result

    def get_User(self, uidornickname: str) -> Union[UserModel, None]:
        """Get The User Object model

        Args:
            uidornickname (str): UID or Nickname

        Returns:
            UserModel|None: The UserModel Object | None
        """
        User = None
        for record in self.UID_DB:
            if record.uid == uidornickname:
                User = record
            elif record.nickname == uidornickname:
                User = record

        self.log.debug(f'Search {uidornickname} -- result = {User}')

        return User

    def get_uid(self, uidornickname:str) -> Union[str, None]:
        """Get the UID of the user starting from the UID or the Nickname

        Args:
            uidornickname (str): UID or Nickname

        Returns:
            str|None: Return the UID
        """
        uid = None
        for record in self.UID_DB:
            if record.uid == uidornickname:
                uid = record.uid
            if record.nickname == uidornickname:
                uid = record.uid

        self.log.debug(f'The UID that you are looking for {uidornickname} has been found {uid}')
        return uid

    def get_nickname(self, uidornickname:str) -> Union[str, None]:
        """Get the Nickname starting from UID or the nickname

        Args:
            uidornickname (str): UID or Nickname of the user

        Returns:
            str|None: the nickname
        """
        nickname = None
        for record in self.UID_DB:
            if record.nickname == uidornickname:
                nickname = record.nickname
            if record.uid == uidornickname:
                nickname = record.nickname
        self.log.debug(f'The value to check {uidornickname} -> {nickname}')
        return nickname

class Admin:

    @dataclass
    class AdminModel:
        uid: str
        nickname: str
        username: str
        hostname: str
        umodes: str
        vhost: str
        level: int
        connexion_datetime: datetime = field(default=datetime.now())

    UID_ADMIN_DB: list[AdminModel] = []

    def __init__(self, Base: Base) -> None:
        self.log = Base.logs
        pass

    def insert(self, newAdmin: AdminModel) -> bool:

        result = False
        exist = False

        for record in self.UID_ADMIN_DB:
            if record.uid == newAdmin.uid:
                exist = True
                self.log.debug(f'{record.uid} already exist')

        if not exist:
            self.UID_ADMIN_DB.append(newAdmin)
            result = True
            self.log.debug(f'UID ({newAdmin.uid}) has been created')

        if not result:
            self.log.critical(f'The User Object was not inserted {newAdmin}')

        return result
    
    def update(self, uid: str, newNickname: str) -> bool:

        result = False

        for record in self.UID_ADMIN_DB:
            if record.uid == uid:
                record.nickname = newNickname
                result = True
                self.log.debug(f'UID ({record.uid}) has been updated with new nickname {newNickname}')

        if not result:
            self.log.critical(f'The new nickname {newNickname} was not updated, uid = {uid}')

        return result
    
    def delete(self, uid: str) -> bool:

        result = False

        for record in self.UID_ADMIN_DB:
            if record.uid == uid:
                self.UID_ADMIN_DB.remove(record)
                result = True
                self.log.debug(f'UID ({record.uid}) has been created')

        if not result:
            self.log.critical(f'The UID {uid} was not deleted')

        return result
    
    def get_Admin(self, uidornickname: str) -> Union[AdminModel, None]:

        Admin = None
        for record in self.UID_ADMIN_DB:
            if record.uid == uidornickname:
                Admin = record
            elif record.nickname == uidornickname:
                Admin = record

        self.log.debug(f'Search {uidornickname} -- result = {Admin}')

        return Admin

    def get_uid(self, uidornickname:str) -> Union[str, None]:

        uid = None
        for record in self.UID_ADMIN_DB:
            if record.uid == uidornickname:
                uid = record.uid
            if record.nickname == uidornickname:
                uid = record.uid

        self.log.debug(f'The UID that you are looking for {uidornickname} has been found {uid}')
        return uid

    def get_nickname(self, uidornickname:str) -> Union[str, None]:

        nickname = None
        for record in self.UID_ADMIN_DB:
            if record.nickname == uidornickname:
                nickname = record.nickname
            if record.uid == uidornickname:
                nickname = record.nickname
        self.log.debug(f'The value {uidornickname} -- {nickname}')
        return nickname

class Channel:

    @dataclass
    class ChannelModel:
        name: str
        uids: list

    UID_CHANNEL_DB: list[ChannelModel] = []

    def __init__(self, Base: Base) -> None:
        self.log = Base.logs
        self.Base = Base
        pass

    def insert(self, newChan: ChannelModel) -> bool:

        result = False
        exist = False

        for record in self.UID_CHANNEL_DB:
            if record.name == newChan.name:
                exist = True
                self.log.debug(f'{record.name} already exist')
                
                for user in newChan.uids:
                    record.uids.append(user)

                # Supprimer les doublons 
                del_duplicates = list(set(record.uids))
                record.uids = del_duplicates
                self.log.debug(f'Updating a new UID to the channel {record}')


        if not exist:
            self.UID_CHANNEL_DB.append(newChan)
            result = True
            self.log.debug(f'New Channel Created: ({newChan})')

        if not result:
            self.log.critical(f'The Channel Object was not inserted {newChan}')

        return result

    def delete(self, name: str) -> bool:

        result = False

        for record in self.UID_CHANNEL_DB:
            if record.name == name:
                self.UID_CHANNEL_DB.remove(record)
                result = True
                self.log.debug(f'Channel ({record.name}) has been created')

        if not result:
            self.log.critical(f'The Channel {name} was not deleted')

        return result

    def delete_user_from_channel(self, chan_name: str, uid:str) -> bool:
        try:
            result = False

            for record in self.UID_CHANNEL_DB:
                if record.name == chan_name:
                    for user_id in record.uids:
                        if self.Base.clean_uid(user_id) == uid:
                            record.uids.remove(user_id)
                            self.log.debug(f'uid {uid} has been removed, here is the new object: {record}')
                            result = True

            for record in self.UID_CHANNEL_DB:
                if not record.uids:
                    self.UID_CHANNEL_DB.remove(record)
                    self.log.debug(f'Channel {record.name} has been removed, here is the new object: {record}')

            return result
        except ValueError as ve:
            self.log.error(f'{ve}')

    def get_Channel(self, name: str) -> Union[ChannelModel, None]:

        Channel = None
        for record in self.UID_CHANNEL_DB:
            if record.name == name:
                Channel = record

        self.log.debug(f'Search {name} -- result = {Channel}')

        return Channel

    def get_mode(self, name:str) -> Union[str, None]:

        mode = None
        for record in self.UID_CHANNEL_DB:
            if record.name == name:
                mode = record.mode

        self.log.debug(f'The mode of the channel {name} has been found: {mode}')
        return mode
