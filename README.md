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

# Installation et utilisation
    Prérequis:
        - Python version >= 3.10
        - Pip de python installé sur la machine
        - Python librairies psutil & sqlalchemy & requests
        - IRC Serveur Version >= UnrealIRCd-6.1.2.2

    Installation:

        Cloner le dépôt:
        Bash
        git clone https://github.com/adator85/IRC_DEFENDER_MODULES.git
        Utilisez ce code avec précaution.

    Configuration (configuration.json):
        Le fichier configuration.json permet de personnaliser le service:
            Serveur IRC: Adresse du serveur IRC.
            Port: Port du serveur IRC.
            Canal: Canal auquel se connecter.
            Nom du Service: Nom d'utilisateur du bot sur le serveur.
            Mot de passe: Mot de passe du link (si nécessaire).
            Préfixes de commandes: Caractères utilisés pour déclencher les commandes.
            Et bien d'autres...

    Extension:
        Le code est modulaire et conçu pour être facilement étendu. Vous pouvez ajouter de nouvelles commandes, de nouvelles fonctionnalités (mods/mod_test.py  est un exemple pour bien demarrer la création de son module).

    Contributions:
    Les contributions sont les bienvenues ! N'hésitez pas à ouvrir des issues ou des pull requests.

    Avertissement:
    Ce bot est fourni "tel quel" sans aucune garantie. Utilisez-le à vos risques et périls.