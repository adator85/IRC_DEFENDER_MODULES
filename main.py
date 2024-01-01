from core import installation

#############################################
#       @Version : 1                        #
#       Requierements :                     #
#           Python3.10 or higher            #
#           SQLAlchemy, requests, psutil    #
#           UnrealIRCD 6.2.2 or higher      #
#############################################

#########################
# LANCEMENT DE DEFENDER #
#########################

try:

    installation.Install()

    from core.irc import Irc
    ircInstance = Irc()
    ircInstance.init_irc(ircInstance)

except AssertionError as ae:
    print(f'Assertion Error -> {ae}')
except KeyboardInterrupt as k:
    ircInstance.Base.execute_periodic_action()