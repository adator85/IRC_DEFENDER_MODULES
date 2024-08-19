from core.irc import Irc

#   Le module crée devra réspecter quelques conditions
#       1. Importer le module de configuration
#       2. Le nom de class devra toujours s'appeler comme le module exemple => nom de class Dktmb | nom du module mod_dktmb
#       3. la fonction __init__ devra toujours avoir les parametres suivant (self, irc:object)
#           1 . Créer la variable Irc dans le module
#           2 . Récuperer la configuration dans une variable
#           3 . Définir et enregistrer les nouvelles commandes
#       4. une fonction _hcmds(self, user:str, cmd: list) devra toujours etre crée.

class Test():

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
            0: ['test'],
            1: ['test_level_1']
        }

        # Init the module
        self.__init_module()

        # Log the module
        self.Logs.debug(f'Module {self.__class__.__name__} loaded ...')

    def __init_module(self) -> None:

        self.__set_commands(self.commands_level)
        self.__create_tables()

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

    def unload(self) -> None:

        return None

    def cmd(self, data:list) -> None:
        return None

    def _hcmds(self, user:str, cmd: list, fullcmd: list = []) -> None:

        command = str(cmd[0]).lower()
        dnickname = self.Config.SERVICE_NICKNAME
        fromuser = user

        match command:

            case 'test':
                try:
                    
                    self.Irc.send2socket(f":{dnickname} NOTICE {fromuser} : test command ready ...")
                    self.Logs.debug(f"Test logs ready")
                except KeyError as ke:
                    self.Logs.error(f"Key Error : {ke}")