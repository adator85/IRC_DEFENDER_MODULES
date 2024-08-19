from dataclasses import dataclass, field
from datetime import datetime
from typing import Union

class User:

    @dataclass
    class UserDataClass:
        uid: str
        nickname: str
        username: str
        hostname: str
        umodes: str
        vhost: str
        isWebirc: bool
        connexion_datetime: datetime = field(default=datetime.now())

    UID_DB:list[UserDataClass] = []

    def __init__(self) -> None:
        pass

    def insert(self, user: UserDataClass) -> bool:
        """Insert new user

        Args:
            user (UserDataClass): The User dataclass

        Returns:
            bool: True if the record has been created
        """
        exists = False
        inserted = False

        for record in self.UID_DB:
          if record.uid == user.uid:
                exists = True
                print(f'{user.uid} already exist')

        if not exists:
            self.UID_DB.append(user)
            print(f'New record with uid: {user.uid}')
            inserted = True

        return inserted

    def update(self, uid: str, newnickname: str) -> bool:
        """Updating a single record with a new nickname

        Args:
            uid (str): the uid of the user
            newnickname (str): the new nickname

        Returns:
            bool: True if the record has been updated
        """
        status = False
        for user in self.UID_DB:
            if user.uid == uid:
                user.nickname = newnickname
                status = True
                print(f'Updating record with uid: {uid}')

        return status

    def delete(self, uid: str) -> bool:
        """Delete a user based on his uid

        Args:
            uid (str): The UID of the user

        Returns:
            bool: True if the record has been deleted
        """
        status = False
        for user in self.UID_DB:
            if user.uid == uid:
              self.UID_DB.remove(user)
              status = True
              print(f'Removing record with uid: {uid}')

        return status

    def isexist(self, uidornickname:str) -> bool:
        """do the UID or Nickname exist ?

        Args:
            uidornickname (str): The UID or the Nickname

        Returns:
            bool: True if exist or False if don't exist
        """
        result = False
        for record in self.UID_DB:
            if record.uid == uidornickname:
                result = True
            if record.nickname == uidornickname:
                result = True

        return result

    def get_User(self, uidornickname) -> Union[UserDataClass, None]:

        UserObject = None
        for record in self.UID_DB:
            if record.uid == uidornickname:
                UserObject = record
            elif record.nickname == uidornickname:
                UserObject = record
        
        return UserObject

    def get_uid(self, uidornickname:str) -> Union[str, None]:

        uid = None
        for record in self.UID_DB:
            if record.uid == uidornickname:
                uid = record.uid
            if record.nickname == uidornickname:
                uid = record.uid

        return uid

    def get_nickname(self, uidornickname:str) -> Union[str, None]:

        nickname = None
        for record in self.UID_DB:
            if record.nickname == uidornickname:
                nickname = record.nickname
            if record.uid == uidornickname:
                nickname = record.nickname

        return nickname

class Admin:
    @dataclass
    class AdminDataClass:
        uid: str
        nickname: str
        username: str
        hostname: str
        umodes: str
        vhost: str
        level: int
        connexion_datetime: datetime = field(default=datetime.now())

    UID_ADMIN_DB:list[AdminDataClass] = []

    def __init__(self) -> None:
        pass

    def insert(self, admin: AdminDataClass) -> bool:
        """Insert new user

        Args:
            user (UserDataClass): The User dataclass

        Returns:
            bool: True if the record has been created
        """
        exists = False
        inserted = False

        for record in self.UID_ADMIN_DB:
          if record.uid == admin.uid:
                exists = True
                print(f'{admin.uid} already exist')

        if not exists:
            self.UID_ADMIN_DB.append(admin)
            print(f'New record with uid: {admin.uid}')
            inserted = True
        
        return inserted

    def update(self, uid: str, newnickname: str) -> bool:
        """Updating a single record with a new nickname

        Args:
            uid (str): the uid of the user
            newnickname (str): the new nickname

        Returns:
            bool: True if the record has been updated
        """
        status = False
        for admin in self.UID_ADMIN_DB:
            if admin.uid == uid:
                admin.nickname = newnickname
                status = True
                print(f'Updating record with uid: {uid}')

        return status

    def delete(self, uid: str) -> bool:
        """Delete a user based on his uid

        Args:
            uid (str): The UID of the user

        Returns:
            bool: True if the record has been deleted
        """
        status = False
        for admin in self.UID_ADMIN_DB:
            if admin.uid == uid:
              self.UID_ADMIN_DB.remove(admin)
              status = True
              print(f'Removing record with uid: {uid}')

        return status

    def isexist(self, uidornickname:str) -> bool:
        """do the UID or Nickname exist ?

        Args:
            uidornickname (str): The UID or the Nickname

        Returns:
            bool: True if exist or False if don't exist
        """
        result = False
        for record in self.UID_ADMIN_DB:
            if record.uid == uidornickname:
                result = True
            if record.nickname == uidornickname:
                result = True

        return result

    def get_Admin(self, uidornickname) -> Union[AdminDataClass, None]:

        AdminObject = None
        for record in self.UID_ADMIN_DB:
            if record.uid == uidornickname:
                AdminObject = record
            elif record.nickname == uidornickname:
                AdminObject = record
        
        return AdminObject

    def get_uid(self, uidornickname:str) -> Union[str, None]:

        uid = None
        for record in self.UID_ADMIN_DB:
            if record.uid == uidornickname:
                uid = record.uid
            if record.nickname == uidornickname:
                uid = record.uid

        return uid

    def get_nickname(self, uidornickname:str) -> Union[str, None]:

        nickname = None
        for record in self.UID_ADMIN_DB:
            if record.nickname == uidornickname:
                nickname = record.nickname
            if record.uid == uidornickname:
                nickname = record.nickname

        return nickname

    def get_level(self, uidornickname:str) -> int:

        level = 0
        for record in self.UID_ADMIN_DB:
            if record.uid == uidornickname:
                level = record.level
            if record.nickname == uidornickname:
                level = record.level

        return level

