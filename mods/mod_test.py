import threading
from core.irc import Irc

#   Le module crée devra réspecter quelques conditions
#       1. Importer le module de configuration
#       2. Le nom de class devra toujours s'appeler comme le module exemple => nom de class Dktmb | nom du module mod_dktmb
#       3. la fonction __init__ devra toujours avoir les parametres suivant (self, irc:object)
#           1 . Créer la variable irc dans le module
#           2 . Récuperer la configuration dans une variable
#           3 . Définir et enregistrer les nouvelles commandes
#       4. une fonction _hcmds(self, user:str, cmd: list) devra toujours etre crée.

class Test():

    def __init__(self, ircInstance:Irc) -> None:
        print(f'Module {self.__class__.__name__} loaded ...')

        self.irc = ircInstance                                              # Ajouter l'object mod_irc a la classe

        self.config = ircInstance.Config                                    # Ajouter la configuration a la classe

        # Créer les nouvelles commandes du module
        self.commands = ['test']

        self.__set_commands(self.commands)                                  # Enrigstrer les nouvelles commandes dans le code

        self.core = ircInstance.Base                                        # Instance du module Base

        self.session = ''                                                   # Instancier une session pour la base de données
        self.__create_db('mod_test')                                       # Créer la base de données si necessaire

    def __set_commands(self, commands:list) -> None:
        """Rajoute les commandes du module au programme principal

        Args:
            commands (list): Liste des commandes du module

        Returns:
            None: Aucun retour attendu
        """
        for command in commands:
            self.irc.commands.append(command)

        return True

    def __create_db(self, db_name:str) -> None:
        """Methode qui va créer la base de donnée si elle n'existe pas.
           Une Session unique pour cette classe sera crée, qui sera utilisé dans cette classe / module
        Args:
            database_name (str): Nom de la base de données ( pas d'espace dans le nom )

        Returns:
            None: Aucun retour n'es attendu
        """
        db_directory = self.core.MODS_DB_PATH

        self.session = self.core.db_init(db_directory, db_name)

        table_logs = '''CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            server_msg TEXT
            ) 
        '''

        self.core.db_execute_query(self.session, table_logs)
        return None

    def _hcmds(self, user:str, cmd: list) -> None:

        command = cmd[0].lower()

        match command:

            case 'test':
                try:
                    user_action = cmd[1]
                    self.irc.send2socket(f'PRIVMSG #webmail Je vais voicer {user}')
                    self.irc.send2socket(f'MODE #webmail +v {user_action}')
                    self.core.create_log(f"MODE +v sur {user_action}")
                except KeyError as ke:
                    self.core.create_log(f"Key Error : {ke}")

