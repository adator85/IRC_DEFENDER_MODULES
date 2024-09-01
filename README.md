# IRC-DEFENDER
Defender est un service IRC basé sur la sécurité des réseaux IRC ( UnrealIRCD )
Il permet d'ajouter une sécurité supplémentaire pour vérifier les users connectés au réseau
en demandant aux user un code de validation.
Il permet aux opérateurs de gérer efficacement un canal, tout en offrant aux utilisateurs des outils d'interaction et de décision collective.

# Fonctionnalités principales
    Commandes opérateurs complètes:
        Kick: Expulser un utilisateur du canal.
        Ban: Interdire définitivement l'accès au canal.
        Unban: Lever une interdiction.
        Op/Deop: Attribuer ou retirer les droits d'opérateur.
        Halfop/Dehalfop: Attribuer ou retirer les droits
        Voice/Devoice: Attribuer ou retirer les droits de voix.

    Système de quarantaine:
        Mise en quarantaine: Isoler temporairement un utilisateur dans un canal privé.
        Libération: Permettre à un utilisateur de quitter la quarantaine en entrant un code spécifique.

    Système de vote:
        Kick: Les utilisateurs peuvent voter pour expulser un membre du canal.
        Autres actions: Possibilité d'étendre le système de vote à d'autres actions (ban, etc.).

# Installation automatique sur une machine Debian/Ubuntu

    Prérequis:
        - Système d'exploitation Linux (Windows non supporté)
        - Python version 3.10 ou supérieure

    Bash:
        $ git clone https://github.com/adator85/IRC_DEFENDER_MODULES.git
        - Renommer le fichier exemple_configuration.json en configuration.json
        - Configurer le fichier configuration.json
        $ python3 main.py

Si votre configuration est bonne, votre service est censé etre connecté a votre réseau IRC
Pour Les prochains lancement de defender vous devez utiliser la commande suivante:

    Bash:
        $ systemctl --user [start | stop | restart | status] defender

# Installation manuelle:
    Bash:
        $ git clone https://github.com/adator85/IRC_DEFENDER_MODULES.git
        $ cd IRC_DEFENDER_MODULES
        $ python3 -m venv .pyenv
        $ source .pyenv/bin/activate
        (pyenv)$ pip install sqlalchemy, psutil, requests, faker
        - Créer un service nommé "defender.service" pour votre service et placer le dans "/PATH/TO/USER/.config/systemd/user/"
        - Si le dossier n'existe pas il faut les créer
        $ sudo systemctl --user start defender

# Configuration

    SERVEUR (Serveur)
        SERVEUR_IP: Adresse IP du serveur IRC à rejoindre.
        SERVEUR_HOSTNAME: Nom d'hôte du serveur IRC à rejoindre (optionnel).
        SERVEUR_LINK: Lien vers le serveur IRC (optionnel).
        SERVEUR_PORT: Port de connexion au serveur IRC.
        SERVEUR_PASSWORD: Mot de passe d'enregistrement du service sur le serveur IRC.
        SERVEUR_ID: Identifiant unique du service.
        SERVEUR_SSL: Active la connexion SSL sécurisée au serveur IRC (true/false).

    SERVICE (Service)
        SERVICE_NAME: Nom du service IRC.
        SERVICE_NICKNAME: Surnom utilisé par le service sur le serveur IRC.
        SERVICE_REALNAME: Nom réel du service affiché sur le serveur IRC.
        SERVICE_USERNAME: Nom d'utilisateur utilisé par le service pour se connecter au serveur IRC.
        SERVICE_HOST: Nom d'hôte du service affiché sur le serveur IRC (optionnel).
        SERVICE_INFO: Description du service.
        SERVICE_CHANLOG: Canal utilisé pour la journalisation des actions du service.
        SERVICE_SMODES: Modes serveur appliqués aux canaux rejoints par le service.
        SERVICE_CMODES: Modes de canal appliqués aux canaux rejoints par le service.
        SERVICE_UMODES: Modes utilisateur appliqués au service.
        SERVICE_PREFIX: Caractère utilisé comme préfixe des commandes du service.

    COMPTE (Compte)
        OWNER: Nom d'utilisateur possédant les droits d'administration du service.
        PASSWORD: Mot de passe de l'administrateur du service.

    CANAUX (Canaux)
        SALON_JAIL: Canal utilisé comme prison pour les utilisateurs sanctionnés.
        SALON_JAIL_MODES: Modes appliqués au canal de prison.
        SALON_LIBERER: Canal utilisé pour la libération des utilisateurs sanctionnés.

    API (API)
        API_TIMEOUT: Durée maximale d'attente d'une réponse de l'API en secondes.

    SCANNER (Scanner)
        PORTS_TO_SCAN: Liste des ports à scanner pour détecter des serveurs potentiellement malveillants.

    SÉCURITÉ (Sécurité)
        WHITELISTED_IP: Liste d'adresses IP autorisées à contourner certaines restrictions.
        GLINE_DURATION: Durée de bannissement temporaire d'un utilisateur en minutes.

    DEBUG (Debug)
        DEBUG_LEVEL: Niveau de verbosité des messages de debug (plus grand est le nombre, plus il y a d'informations).

    COULEURS (Couleurs)
        CONFIG_COLOR: Dictionnaire contenant des codes de couleurs IRC pour un meilleur affichage des messages.

    Modification de la configuration

        Vous devez modifier le fichier configuration.json en remplaçant les valeurs par défaut avec vos propres informations. Assurez-vous de bien lire la description de chaque paramètre pour une configuration optimale du service.

# \\!/ Attention \\!/
Le mot de passe de l'administrateur et le mot de passe du service doivent être modifiés pour des raisons de sécurité.
Ne partagez pas vos informations de connexion au serveur IRC avec des tiers.
a votre premiere connexion vous devez tapez 

        /msg [NomDuService] auth [nickname] [password]
        -- Une fois identifié tapez la commande suivante
        /msg [NomDuService] editaccess [nickname] [Nouveau-Password] 5

# Extension:
    Le code est modulaire et conçu pour être facilement étendu. Vous pouvez ajouter de nouvelles commandes, de nouvelles fonctionnalités (mods/mod_test.py  est un exemple pour bien demarrer la création de son module).

# Contributions:
    Les contributions sont les bienvenues ! N'hésitez pas à ouvrir des issues ou des pull requests.

# Avertissement:
    Ce bot est fourni "tel quel" sans aucune garantie. Utilisez-le à vos risques et périls.