import json
from os import sep
from typing import Union
from dataclasses import dataclass, field

##########################################
#   CONFIGURATION FILE                   #
##########################################

@dataclass
class ConfigDataModel:

    SERVEUR_IP: str
    SERVEUR_HOSTNAME: str                     # Le hostname du serveur IRC
    SERVEUR_LINK: str                 # Host attendu par votre IRCd (ex. dans votre link block pour Unrealircd)
    SERVEUR_PORT: int                                     # Port du link
    SERVEUR_PASSWORD: str             # Mot de passe du link (Privilégiez argon2 sur Unrealircd)
    SERVEUR_ID: str                                      # SID (identification) du bot en tant que Services
    SERVEUR_SSL: bool                                      # Activer la connexion SSL

    SERVICE_NAME: str                               # Le nom du service
    SERVICE_NICKNAME: str                     # Nick du bot sur IRC
    SERVICE_REALNAME: str                     # Realname du bot
    SERVICE_USERNAME: str                     # Ident du bot
    SERVICE_HOST: str                 # Host du bot
    SERVICE_INFO: str                    # swhois du bot
    SERVICE_CHANLOG: str                           # Salon des logs et autres messages issus du bot
    SERVICE_SMODES: str                               # Mode du service
    SERVICE_CMODES: str                                 # Mode du salon (#ChanLog) que le bot appliquera à son entrée
    SERVICE_UMODES: str                                    # Mode que le bot pourra se donner à sa connexion au salon chanlog
    SERVICE_PREFIX: str                                    # Prefix pour envoyer les commandes au bot
    SERVICE_ID: str = field(init=False)                      # L'identifiant du service

    OWNER: str                                        # Identifiant du compte admin
    PASSWORD: str                                     # Mot de passe du compte admin

    SALON_JAIL: str                                    # Salon pot de miel
    SALON_JAIL_MODES: str                                 # Mode du salon pot de miel
    SALON_LIBERER: str                              # Le salon ou sera envoyé l'utilisateur clean

    API_TIMEOUT: int                                         # Timeout des api's

    PORTS_TO_SCAN: list    # Liste des ports a scanné pour une detection de proxy
    WHITELISTED_IP: list                          # IP a ne pas scanner
    GLINE_DURATION: str                                   # La durée du gline

    DEBUG_LEVEL: int                                        # Le niveau des logs DEBUG 10 | INFO 20 | WARNING 30 | ERROR 40 | CRITICAL 50

    CONFIG_COLOR: dict[str, str]

    table_admin: str
    table_commande: str
    table_log: str
    table_module: str
    table_config: str
    table_channel: str

    current_version: str
    latest_version: str
    db_name: str
    db_path: str

    def __post_init__(self):
        # Initialiser SERVICE_ID après la création de l'objet
        self.SERVICE_ID:str = f"{self.SERVEUR_ID}AAAAAB"

class Config:

    def __init__(self):

        self.ConfigObject: ConfigDataModel = self.__load_service_configuration()
        return None

    def __load_json_service_configuration(self):

        conf_filename = f'core{sep}configuration.json'
        with open(conf_filename, 'r') as configuration_data:
            configuration:dict[str, Union[str, int, list, dict]] = json.load(configuration_data)

        for key, value in configuration['CONFIG_COLOR'].items():
            configuration['CONFIG_COLOR'][key] = str(value).encode('utf-8').decode('unicode_escape')
        
        return configuration
    
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
