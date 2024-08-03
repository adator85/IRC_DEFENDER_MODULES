import os, json

####################################################################################################
#                                       DO NOT TOUCH THIS FILE                                     #
####################################################################################################

class SysConfig:

    DEFENDER_VERSION = '4.0.0'                              # MAJOR.MINOR.BATCH
    LATEST_DEFENDER_VERSION = '0.0.0'                       # Latest Version of Defender in git
    DEFENDER_DB_PATH = 'db' + os.sep                        # Séparateur en fonction de l'OS
    DEFENDER_DB_NAME = 'defender'                           # Le nom de la base de données principale

    def __init__(self) -> None:

        version_filename = f'.{os.sep}version.json'
        with open(version_filename, 'r') as version_data:
            self.global_configuration:dict[str, str] = json.load(version_data)

        self.DEFENDER_VERSION = self.global_configuration["version"]

        return None