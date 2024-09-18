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

            config_dict = {"CONFIG_COLOR" : {
                            "blanche": "\\u0003\\u0030",
                            "noire": "\\u0003\\u0031",
                            "bleue": "\\u0003\\u0020",
                            "verte": "\\u0003\\u0033",
                            "rouge": "\\u0003\\u0034",
                            "jaune": "\\u0003\\u0036",
                            "gras": "\\u0002",
                            "nogc": "\\u0002\\u0003"
                                }
                            }

            missing_color = False

            if not "CONFIG_COLOR" in configuration:
                missing_color = True
                configuration_color = config_dict
            else:
                configuration_color = configuration["CONFIG_COLOR"]

            if missing_color:
                for key, value in configuration_color.items():
                    configuration_color['CONFIG_COLOR'][key] = str(value).encode('utf-8').decode('unicode_escape')
                configuration['CONFIG_COLOR'] = configuration_color['CONFIG_COLOR']
            else:
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
            SERVEUR_IP=import_config["SERVEUR_IP"] if "SERVEUR_IP" in import_config else '127.0.0.1',
            SERVEUR_HOSTNAME=import_config["SERVEUR_HOSTNAME"] if "SERVEUR_HOSTNAME" in import_config else None,
            SERVEUR_LINK=import_config["SERVEUR_LINK"] if "SERVEUR_LINK" in import_config else None,
            SERVEUR_PORT=import_config["SERVEUR_PORT"] if "SERVEUR_PORT" in import_config else 6667,
            SERVEUR_PASSWORD=import_config["SERVEUR_PASSWORD"] if "SERVEUR_PASSWORD" in import_config else None,
            SERVEUR_ID=import_config["SERVEUR_ID"] if "SERVEUR_ID" in import_config else '19Z',
            SERVEUR_SSL=import_config["SERVEUR_SSL"] if "SERVEUR_SSL" in import_config else False,
            SERVICE_NAME=import_config["SERVICE_NAME"] if "SERVICE_NAME" in import_config else 'Defender',
            SERVICE_NICKNAME=import_config["SERVICE_NICKNAME"] if "SERVICE_NICKNAME" in import_config else 'Defender',
            SERVICE_REALNAME=import_config["SERVICE_REALNAME"] if "SERVICE_REALNAME" in import_config else 'Defender Security',
            SERVICE_USERNAME=import_config["SERVICE_USERNAME"] if "SERVICE_USERNAME" in import_config else 'IRCSecurity',
            SERVICE_HOST=import_config["SERVICE_HOST"] if "SERVICE_HOST" in import_config else 'defender.local.network',
            SERVICE_INFO=import_config["SERVICE_INFO"] if "SERVICE_INFO" in import_config else 'Defender Network IRC Service',
            SERVICE_CHANLOG=import_config["SERVICE_CHANLOG"] if "SERVICE_CHANLOG" in import_config else '#services',
            SERVICE_SMODES=import_config["SERVICE_SMODES"] if "SERVICE_SMODES" in import_config else '+ioqBS',
            SERVICE_CMODES=import_config["SERVICE_CMODES"] if "SERVICE_CMODES" in import_config else 'ntsOP',
            SERVICE_UMODES=import_config["SERVICE_UMODES"] if "SERVICE_UMODES" in import_config else 'o',
            SERVICE_PREFIX=import_config["SERVICE_PREFIX"] if "SERVICE_PREFIX" in import_config else '!',
            OWNER=import_config["OWNER"] if "OWNER" in import_config else 'admin',
            PASSWORD=import_config["PASSWORD"] if "PASSWORD" in import_config else 'admin',
            SALON_JAIL=import_config["SALON_JAIL"] if "SALON_JAIL" in import_config else '#jail',
            SALON_JAIL_MODES=import_config["SALON_JAIL_MODES"] if "SALON_JAIL_MODES" in import_config else 'sS',
            SALON_LIBERER=import_config["SALON_LIBERER"] if "SALON_LIBERER" in import_config else '#welcome',
            SALON_CLONES=import_config["SALON_CLONES"] if "SALON_CLONES" in import_config else '#clones',
            API_TIMEOUT=import_config["API_TIMEOUT"] if "API_TIMEOUT" in import_config else 2,
            PORTS_TO_SCAN=import_config["PORTS_TO_SCAN"] if "PORTS_TO_SCAN" in import_config else [],
            WHITELISTED_IP=import_config["WHITELISTED_IP"] if "WHITELISTED_IP" in import_config else ['127.0.0.1'],
            GLINE_DURATION=import_config["GLINE_DURATION"] if "GLINE_DURATION" in import_config else '30',
            DEBUG_LEVEL=import_config["DEBUG_LEVEL"] if "DEBUG_LEVEL" in import_config else 20,
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
