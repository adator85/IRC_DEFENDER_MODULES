# IRC-DEFENDER
Defender est un service IRC basé sur la sécurité des réseaux IRC ( UnrealIRCD )
Il permet d'ajouter une sécurité supplémentaire pour vérifier les users connectés au réseau
en demandant aux user un code de validation.

Pré-requis :

    - Python version >= 3.10
    - Pip de python installé sur la machine
    - Python librairies psutil & sqlalchemy & requests
    - IRC Serveur Version >= UnrealIRCd-6.1.2.2

Lancement de Defender :

    - Installer les librairies python : psutil & sqlalchemy & requests
        - pip3 install psutil sqlalchemy requests ou pip install psutil sqlalchemy requests
    - Ne pas lancer Defender en tant que root
    - Créer plutot un service qui lancera Defender en tant qu'utilisateur non root
    - Un fichier PID sera crée.

# TO DO LIST

    - Optimiser le systeme de réputation:
        - lorsque les users ce connectent, Ils entrent dans un salon puis une fraction de seconde le service les bans

# VERSION 1

    [02.01.2024]
        - Les deux variables RESTART et INIT ont été déplacées vers le module Irc
        - Nouvelle class Install:
            - Le programme va vérifier si les 3 librairies sont installées (SQLAlchemy & requests & psutil)
            - Une fois la vérification, il va mêtre a jour pip puis installera les dépendances

    [28.12.2023]
        - Changement de méthode pour récuperer la version actuelle de python
        - Ajout de la réponse a une PING de la part d'un utilisateur
        - Installation automatique des packages sqlalchemy, requests et psutil

# BUG FIX

    [29.12.2023]
        - Correction des messages de receptions trop longs > 4070 caractéres; 
            - la méthode boucle et incrémente la réponse tant que le nombre de caractére reçu est supérieur a 4072
        - Rajout du protocol MTAGS a la connexion du service
            - Impact majeur dans la lecture des messages reçu du serveur ( PRIVMSG, SLOGS, UID, QUIT, NICK, PONG, SJOIN)

# ALREADY IMPLEMENTED

    - Connexion en tant que service
    - Gestion des messages reçus/envoyés par le serveur
    - Gestion des caractéres spéciaux
    - Gestion des logs (salon, fichiers et console)
        - Mode debug : gestion des logs coté console
    - Création du systeme de gestion de commandes
        - Defender reconnait les commandes qui commence par le suffix définit dans la configuration
        - Defender reconnait aussi reconnaitre les commandes qui viennent de /msg Defender [commande]
    - Identifications
        - Systéme d'identification [OK]
        - Systéme de changement d'information [OK]
        - Suppression d'un admin
        - Systéme de groupe d'accés [OK]

    Reputation security
        - Activation ou désaction du systéme --> OK | .reputation ON/off
        - Le user sera en mesure de changer la limite de la réputation --> OK | .reputation set limit 120
        - Defender devra envoyer l'utilisateur dans un salon définit dans la configuration --> OK
        - Defender bannira l'utilisateur de la totalité des salons, il le bannira aussi lorsqu'il souhaitera accéder a de nouveau salon --> OK
        - Defender devra envoyer un message du type "Merci de taper cette comande /msg {nomdudefender} code {un code générer aléatoirement} --> OK
        - Defender devra reconnaitre le code --> OK
        - Defender devra liberer l'utilisateur et l'envoyer vers un salon définit dans la configuration --> OK
