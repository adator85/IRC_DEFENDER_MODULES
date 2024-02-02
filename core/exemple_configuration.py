import os
##########################################
#   CONFIGURATION FILE :                 #
#   Rename file to : configuration.py    #
##########################################

class Config:

    DEFENDER_VERSION = '1.1.0'                              # MAJOR.MINOR.BATCH
    DEFENDER_DB_PATH = 'db' + os.sep                        # Séparateur en fonction de l'OS
    DEFENDER_DB_NAME = 'defender'                           # Le nom de la base de données principale
    SERVICE_NAME = 'defender'                               # Le nom du service

    SERVEUR_IP = '8.8.8.8'                                  # IP ou host du serveur à rejoindre
    SERVEUR_HOSTNAME = 'your hostname'                      # Le hostname du serveur IRC 
    SERVEUR_LINK = 'your link'                              # Host attendu par votre IRCd (ex. dans votre link block pour Unrealircd)
    SERVEUR_PORT = 6666                                     # Port du link
    SERVEUR_PASSWORD = 'your link password'                 # Mot de passe du link (Privilégiez argon2 sur Unrealircd)
    SERVEUR_ID = '002'                                      # SID (identification) du bot en tant que Services

    SERVICE_NICKNAME = 'BotName'                            # Nick du bot sur IRC
    SERVICE_REALNAME = 'BotRealname'                        # Realname du bot
    SERVICE_USERNAME = 'BotIdent'                           # Ident du bot
    SERVICE_HOST = 'your service host'                      # Host du bot
    SERVICE_INFO = 'Network IRC Service'                    # swhois du bot
    SERVICE_CHANLOG = '#services'                           # Salon des logs et autres messages issus du bot
    SERVICE_SMODES = '+ioqBS'                               # Mode du service
    SERVICE_CMODES = 'ntsO'                                 # Mode du salon (#ChanLog) que le bot appliquera à son entrée
    SERVICE_UMODES = 'o'                                    # Mode que le bot pourra se donner à sa connexion au salon chanlog
    SERVICE_PREFIX = '.'                                    # Prefix pour envoyer les commandes au bot
    SERVICE_ID = SERVEUR_ID + 'AAAAAB'                      # L'identifiant du service

    OWNER = 'admin'                                         # Identifiant du compte admin
    PASSWORD = 'password'                                   # Mot de passe du compte admin

    SALON_JAIL = '#JAIL'                                    # Salon pot de miel
    SALON_JAIL_MODES = 'sS'                                 # Mode du salon pot de miel
    SALON_LIBERER = '#welcome'                              # Le salon ou sera envoyé l'utilisateur clean

    PORTS_TO_SCAN = [3028, 8080, 1080, 1085, 4145, 9050]    # Liste des ports a scanné pour une detection de proxy

    DEBUG = 0                                               # Afficher l'ensemble des messages du serveurs dans la console

    CONFIG_COLOR = {
        'blanche': '\x0300',                                # Couleur blanche
        'noire': '\x0301',                                  # Couleur noire
        'bleue': '\x0302',                                  # Couleur Bleue
        'verte': '\x0303',                                  # Couleur Verte
        'rouge': '\x0304',                                  # Couleur rouge
        'jaune': '\x0306',                                  # Couleur jaune
        'gras': '\x02',                                     # Gras
        'nogc': '\x02\x03'                                  # Retirer gras et couleur
    }