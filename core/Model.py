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
                # If the user exist then return False and do not go further
                exist = True
                self.log.debug(f'{record.uid} already exist')
                return result

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
                # If the user exist then update and return True and do not go further
                record.nickname = newNickname
                result = True
                self.log.debug(f'UID ({record.uid}) has been updated with new nickname {newNickname}')
                return result

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
                # If the user exist then remove and return True and do not go further
                self.UID_DB.remove(record)
                result = True
                self.log.debug(f'UID ({record.uid}) has been deleted')
                return result

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
                # If the admin exist then return False and do not go further
                exist = True
                self.log.debug(f'{record.uid} already exist')
                return result

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
                # If the admin exist, update and do not go further
                record.nickname = newNickname
                result = True
                self.log.debug(f'UID ({record.uid}) has been updated with new nickname {newNickname}')
                return result

        if not result:
            self.log.critical(f'The new nickname {newNickname} was not updated, uid = {uid}')

        return result

    def delete(self, uid: str) -> bool:

        result = False

        for record in self.UID_ADMIN_DB:
            if record.uid == uid:
                # If the admin exist, delete and do not go further
                self.UID_ADMIN_DB.remove(record)
                result = True
                self.log.debug(f'UID ({record.uid}) has been created')
                return result

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
        """### Channel name 
        It include the #"""
        uids: list
        """### List of UID available in the channel
        including their modes ~ @ % + *

        Returns:
            list: The list of UID's including theirs modes
        """

    UID_CHANNEL_DB: list[ChannelModel] = []
    """List that contains all the Channels objects (ChannelModel)
    """

    def __init__(self, Base: Base) -> None:
        self.log = Base.logs
        self.Base = Base
        pass

    def insert(self, newChan: ChannelModel) -> bool:
        """This method will insert a new channel and if the channel exist it will update the user list (uids)

        Args:
            newChan (ChannelModel): The channel model object

        Returns:
            bool: True if new channel, False if channel exist (However UID could be updated)
        """
        result = False
        exist = False

        for record in self.UID_CHANNEL_DB:
            if record.name == newChan.name:
                # If the channel exist, update the user list and do not go further
                exist = True
                self.log.debug(f'{record.name} already exist')

                for user in newChan.uids:
                    record.uids.append(user)

                # Supprimer les doublons
                del_duplicates = list(set(record.uids))
                record.uids = del_duplicates
                self.log.debug(f'Updating a new UID to the channel {record}')
                return result


        if not exist:
            # If the channel don't exist, then create it
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
                # If the channel exist, then remove it and return True.
                # As soon as the channel found, return True and stop the loop
                self.UID_CHANNEL_DB.remove(record)
                result = True
                self.log.debug(f'Channel ({record.name}) has been created')
                return result

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
                            self.log.debug(f'The UID {uid} has been removed, here is the new object: {record}')
                            result = True

            for record in self.UID_CHANNEL_DB:
                if not record.uids:
                    self.UID_CHANNEL_DB.remove(record)
                    self.log.debug(f'The Channel {record.name} has been removed, here is the new object: {record}')

            return result
        except ValueError as ve:
            self.log.error(f'{ve}')

    def delete_user_from_all_channel(self, uid:str) -> bool:
        try:
            result = False

            for record in self.UID_CHANNEL_DB:
                for user_id in record.uids:
                    if self.Base.clean_uid(user_id) == self.Base.clean_uid(uid):
                        record.uids.remove(user_id)
                        self.log.debug(f'The UID {uid} has been removed, here is the new object: {record}')
                        result = True

            for record in self.UID_CHANNEL_DB:
                if not record.uids:
                    self.UID_CHANNEL_DB.remove(record)
                    self.log.debug(f'The Channel {record.name} has been removed, here is the new object: {record}')

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

class Clones:

    @dataclass
    class CloneModel:
        alive: bool
        nickname: str
        username: str

    UID_CLONE_DB: list[CloneModel] = []

    def __init__(self, Base: Base) -> None:
        self.log = Base.logs

    def insert(self, newCloneObject: CloneModel) -> bool:
        """Create new Clone object

        Args:
            newCloneObject (CloneModel): New CloneModel object

        Returns:
            bool: True if inserted
        """
        result = False
        exist = False

        for record in self.UID_CLONE_DB:
            if record.nickname == newCloneObject.nickname:
                # If the user exist then return False and do not go further
                exist = True
                self.log.debug(f'{record.nickname} already exist')
                return result

        if not exist:
            self.UID_CLONE_DB.append(newCloneObject)
            result = True
            self.log.debug(f'New Clone Object Created: ({newCloneObject})')

        if not result:
            self.log.critical(f'The Clone Object was not inserted {newCloneObject}')

        return result

    def delete(self, nickname: str) -> bool:
        """Delete the Clone Object starting from the nickname

        Args:
            nickname (str): nickname of the clone

        Returns:
            bool: True if deleted
        """
        result = False

        for record in self.UID_CLONE_DB:
            if record.nickname == nickname:
                # If the user exist then remove and return True and do not go further
                self.UID_CLONE_DB.remove(record)
                result = True
                self.log.debug(f'The clone ({record.nickname}) has been deleted')
                return result

        if not result:
            self.log.critical(f'The UID {nickname} was not deleted')

        return result

    def exists(self, nickname: str) -> bool:
        """Check if the nickname exist

        Args:
            nickname (str): Nickname of the clone

        Returns:
            bool: True if the nickname exist
        """
        response = False

        for cloneObject in self.UID_CLONE_DB:
            if cloneObject.nickname == nickname:
                response = True

        return response

    def kill(self, nickname:str) -> bool:

        response = False

        for cloneObject in self.UID_CLONE_DB:
            if cloneObject.nickname == nickname:
                cloneObject.alive = False # Kill the clone
                response = True

        return response
