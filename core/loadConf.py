import json, sys
from os import sep
from typing import Union, Literal
from dataclasses import dataclass, field

##########################################
#   CONFIGURATION FILE                   #
##########################################

@dataclass
class ConfigDataModel:

    SERVEUR_IP: str
    """Server public IP (could be 127.0.0.1 localhost)"""

    SERVEUR_HOSTNAME: str
    """IRC Server Hostname (your.hostname.extension)"""

    SERVEUR_LINK: str
    """The link hostname (should be the same as your unrealircd link block)"""

    SERVEUR_PORT: int
    """Server port as configured in your unrealircd link block"""

    SERVEUR_PASSWORD: str
    """Your link password"""

    SERVEUR_ID: str
    """Service identification could be Z01 should be unique"""

    SERVEUR_SSL: bool
    """Activate SSL connexion"""

    SERVICE_NAME: str
    """Service name (Ex. Defender)"""

    SERVICE_NICKNAME: str
    """Nickname of the service (Ex. Defender)"""

    SERVICE_REALNAME: str
    """Realname of the service"""

    SERVICE_USERNAME: str
    """Username of the service"""

    SERVICE_HOST: str
    """The service hostname"""

    SERVICE_INFO: str
    """Swhois of the service"""

    SERVICE_CHANLOG: str
    """The channel used by the service (ex. #services)"""

    SERVICE_SMODES: str
    """The service mode (ex. +ioqBS)"""

    SERVICE_CMODES: str
    """The mode of the log channel (ex. ntsO)"""

    SERVICE_UMODES: str
    """The mode of the service when joining chanlog (ex. o, the service will be operator in the chanlog)"""

    SERVICE_PREFIX: str
    """The default prefix to communicate with the service"""

    SERVICE_ID: str = field(init=False)
    """The service unique ID"""

    OWNER: str
    """The nickname of the admin of the service"""

    PASSWORD: str
    """The password of the admin of the service"""

    SALON_JAIL: str
    """The JAIL channel (ex. #jail)"""

    SALON_JAIL_MODES: str
    """The jail channel modes (ex. sS)"""

    SALON_LIBERER: str
    """Channel where the nickname will be released"""

    SALON_CLONES: str
    """Channel to host clones"""

    API_TIMEOUT: int
    """Default api timeout in second"""

    PORTS_TO_SCAN: list
    """List of ports to scan available for proxy_scan in the mod_defender module"""

    WHITELISTED_IP: list
    """List of remote IP to don't scan"""

    GLINE_DURATION: str
    """Gline duration"""

    DEBUG_LEVEL:Literal[10, 20, 30, 40, 50]
    """Logs level: DEBUG 10 | INFO 20 | WARNING 30 | ERROR 40 | CRITICAL 50"""

    CONFIG_COLOR: dict[str, str]

    table_admin: str
    """Admin table"""

    table_commande: str
    """Core command table"""

    table_log: str
    """Core log table"""

    table_module: str
    """Core module table"""

    table_config: str
    """Core configuration table"""

    table_channel: str
    """Core channel table"""

    current_version: str
    """Current version of Defender"""

    latest_version: str
    """The Latest version fetched from github"""

    db_name: str
    """The database name"""

    db_path: str
    """The database path"""

    def __post_init__(self):
        # Initialiser SERVICE_ID après la création de l'objet
        self.SERVICE_ID:str = f"{self.SERVEUR_ID}AAAAAB"
        """The service ID which is SERVEUR_ID and AAAAAB"""

class Config:

    def __init__(self):

        self.ConfigObject: ConfigDataModel = self.__load_service_configuration()
        return None

    def __load_json_service_configuration(self):
        try:
            conf_filename = f'core{sep}configuration.json'
            with open(conf_filename, 'r') as configuration_data:
                configuration:dict[str, Union[str, int, list, dict]] = json.load(configuration_data)

            for key, value in configuration['CONFIG_COLOR'].items():
                configuration['CONFIG_COLOR'][key] = str(value).encode('utf-8').decode('unicode_escape')

            return configuration

        except FileNotFoundError as fe:
            print(f'FileNotFound: {fe}')
            print('Configuration file not found please create core/configuration.json')
            sys.exit(0)

    def __load_service_configuration(self) -> ConfigDataModel:
        import_config = self.__load_json_service_configuration()

        ConfigObject: ConfigDataModel = ConfigDataModel(
            SERVEUR_IP=import_config["SERVEUR_IP"],
            SERVEUR_HOSTNAME=import_config["SERVEUR_HOSTNAME"],
            SERVEUR_LINK=import_config["SERVEUR_LINK"],
            SERVEUR_PORT=import_config["SERVEUR_PORT"],
            SERVEUR_PASSWORD=import_config["SERVEUR_PASSWORD"],
            SERVEUR_ID=import_config["SERVEUR_ID"],
            SERVEUR_SSL=import_config["SERVEUR_SSL"],
            SERVICE_NAME=import_config["SERVICE_NAME"],
            SERVICE_NICKNAME=import_config["SERVICE_NICKNAME"],
            SERVICE_REALNAME=import_config["SERVICE_REALNAME"],
            SERVICE_USERNAME=import_config["SERVICE_USERNAME"],
            SERVICE_HOST=import_config["SERVICE_HOST"],
            SERVICE_INFO=import_config["SERVICE_INFO"],
            SERVICE_CHANLOG=import_config["SERVICE_CHANLOG"],
            SERVICE_SMODES=import_config["SERVICE_SMODES"],
            SERVICE_CMODES=import_config["SERVICE_CMODES"],
            SERVICE_UMODES=import_config["SERVICE_UMODES"],
            SERVICE_PREFIX=import_config["SERVICE_PREFIX"],
            OWNER=import_config["OWNER"],
            PASSWORD=import_config["PASSWORD"],
            SALON_JAIL=import_config["SALON_JAIL"],
            SALON_JAIL_MODES=import_config["SALON_JAIL_MODES"],
            SALON_LIBERER=import_config["SALON_LIBERER"],
            SALON_CLONES=import_config["SALON_CLONES"],
            API_TIMEOUT=import_config["API_TIMEOUT"],
            PORTS_TO_SCAN=import_config["PORTS_TO_SCAN"],
            WHITELISTED_IP=import_config["WHITELISTED_IP"],
            GLINE_DURATION=import_config["GLINE_DURATION"],
            DEBUG_LEVEL=import_config["DEBUG_LEVEL"],
            CONFIG_COLOR=import_config["CONFIG_COLOR"],
            table_admin='core_admin',
            table_commande='core_command',
            table_log='core_log',
            table_module='core_module',
            table_config='core_config',
            table_channel='core_channel',
            current_version='',
            latest_version='',
            db_name='defender',
            db_path=f'db{sep}'
        )

        return ConfigObject
