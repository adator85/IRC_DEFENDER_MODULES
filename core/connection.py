import socket, ssl, time
from ssl import SSLSocket
from core.loadConf import Config
from core.base import Base
from typing import Union

class Connection:

    def __init__(self, server_port: int, nickname: str, username: str, channels:list[str], ssl:bool = False) -> None:
        self.Config = Config().ConfigObject
        self.Base = Base(self.Config)
        self.IrcSocket: Union[socket.socket, SSLSocket] = None
        self.signal: bool = True
        self.nickname = nickname
        self.username = username
        self.channels:list[str] = channels
        self.CHARSET = ['utf-8', 'iso-8859-1']

        self.create_socket(self.Config.SERVEUR_IP, self.Config.SERVEUR_HOSTNAME, server_port, ssl)
        self.send_connection_information_to_server(self.IrcSocket)
        self.connect()

    def create_socket(self, server_ip: str,  server_hostname: str, server_port: int, ssl: bool = False) -> bool:

        try:
            soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM or socket.SOCK_NONBLOCK)
            connexion_information = (server_ip, server_port)

            if ssl:
                # Créer un object ssl
                ssl_context = self.__ssl_context()
                ssl_connexion = ssl_context.wrap_socket(soc, server_hostname=server_hostname)
                ssl_connexion.connect(connexion_information)
                self.IrcSocket:SSLSocket = ssl_connexion
                self.SSL_VERSION = self.IrcSocket.version()
                self.Base.logs.debug(f'> Connexion en mode SSL : Version = {self.SSL_VERSION}')
            else:
                soc.connect(connexion_information)
                self.IrcSocket:socket.socket = soc
                self.Base.logs.debug(f'> Connexion en mode normal')

            return True

        except ssl.SSLEOFError as soe:
            self.Base.logs.critical(f"SSLEOFError __create_socket: {soe} - {soc.fileno()}")
            return False
        except ssl.SSLError as se:
            self.Base.logs.critical(f"SSLError __create_socket: {se} - {soc.fileno()}")
            return False
        except OSError as oe:
            self.Base.logs.critical(f"OSError __create_socket: {oe} - {soc.fileno()}")
            return False
        except AttributeError as ae:
            self.Base.logs.critical(f"AttributeError __create_socket: {ae} - {soc.fileno()}")
            return False

    def send2socket(self, send_message:str) -> None:
        """Envoit les commandes à envoyer au serveur.

        Args:
            string (Str): contient la commande à envoyer au serveur.
        """
        try:
            with self.Base.lock:
                # print(f">{str(send_message)}")
                self.IrcSocket.send(f"{send_message}\r\n".encode(self.CHARSET[0]))
                self.Base.logs.debug(f'{send_message}')

        except UnicodeDecodeError:
            self.Base.logs.error(f'Decode Error try iso-8859-1 - message: {send_message}')
            self.IrcSocket.send(f"{send_message}\r\n".encode(self.CHARSET[1],'replace'))
        except UnicodeEncodeError:
            self.Base.logs.error(f'Encode Error try iso-8859-1 - message: {send_message}')
            self.IrcSocket.send(f"{send_message}\r\n".encode(self.CHARSET[1],'replace'))
        except AssertionError as ae:
            self.Base.logs.warning(f'Assertion Error {ae} - message: {send_message}')
        except ssl.SSLEOFError as soe:
            self.Base.logs.error(f"SSLEOFError: {soe} - {send_message}")
        except ssl.SSLError as se:
            self.Base.logs.error(f"SSLError: {se} - {send_message}")
        except OSError as oe:
            self.Base.logs.error(f"OSError: {oe} - {send_message}")

    def send_connection_information_to_server(self, writer:Union[socket.socket, SSLSocket]) -> None:
        """Créer le link et envoyer les informations nécessaires pour la 
        connexion au serveur.

        Args:
            writer (StreamWriter): permet l'envoi des informations au serveur.
        """
        try:
            nickname = self.nickname
            username = self.username

            # Envoyer un message d'identification
            writer.send(f"USER {nickname} {username} {username} {nickname} {username} :{username}\r\n".encode('utf-8'))
            writer.send(f"USER {username} {username} {username} :{username}\r\n".encode('utf-8'))
            writer.send(f"NICK {nickname}\r\n".encode('utf-8'))

            self.Base.logs.debug('Link information sent to the server')

            return None
        except AttributeError as ae:
            self.Base.logs.critical(f'{ae}')

    def connect(self):
        try:

            while self.signal:
                try:
                    # 4072 max what the socket can grab
                    buffer_size = self.IrcSocket.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
                    data_in_bytes = self.IrcSocket.recv(buffer_size)
                    data = data_in_bytes.splitlines(True)
                    count_bytes = len(data_in_bytes)

                    while count_bytes > 4070:
                        # If the received message is > 4070 then loop and add the value to the variable
                        new_data = self.IrcSocket.recv(buffer_size)
                        data_in_bytes += new_data
                        count_bytes = len(new_data)

                    data = data_in_bytes.splitlines(True)

                    if not data:
                        break

                    self.parser(data)

                except ssl.SSLEOFError as soe:
                    self.Base.logs.error(f"SSLEOFError __connect_to_irc: {soe} - {data}")
                    self.signal = False
                except ssl.SSLError as se:
                    self.Base.logs.error(f"SSLError __connect_to_irc: {se} - {data}")
                    self.signal = False
                except OSError as oe:
                    self.Base.logs.error(f"OSError __connect_to_irc: {oe} - {data}")
                    self.signal = False

            self.IrcSocket.shutdown(socket.SHUT_RDWR)
            self.IrcSocket.close()
            self.Base.logs.info("--> Clone Disconnected ...")

        except AssertionError as ae:
            self.Base.logs.error(f'Assertion error : {ae}')
        except ValueError as ve:
            self.Base.logs.error(f'Value Error : {ve}')
        except ssl.SSLEOFError as soe:
            self.Base.logs.error(f"OS Error __connect_to_irc: {soe}")
        except AttributeError as atte:
            self.Base.logs.critical(f"{atte}")
        except Exception as e:
            self.Base.logs.error(f"Exception: {e}")

    def parser(self, cmd:list[bytes]):
        try:
            for data in cmd:
                response = data.decode(self.CHARSET[0]).split()
                # print(response)

                match response[0]:
                    case 'PING':
                        pong = str(response[1]).replace(':','')
                        self.send2socket(f"PONG :{pong}")
                        return None
                    case 'ERROR':
                        error_value = str(response[1]).replace(':','')
                        if error_value == 'Closing':
                            self.signal = False

                match response[1]:
                    case '376':
                        for channel in self.channels:
                            self.send2socket(f"JOIN {channel}")
                        return None
                    case 'PRIVMSG':
                        fullname = str(response[0]).replace(':', '')
                        nickname = fullname.split('!')[0].replace(':','')
                        if nickname == self.Config.SERVICE_NICKNAME:
                            command = str(response[3]).replace(':','')
                            if command == 'KILL':
                                self.send2socket(f'QUIT :Thanks and goodbye')
                                self.signal = False
                            if command == 'JOIN':
                                channel_to_join = str(response[4])
                                self.send2socket(f"JOIN {channel_to_join}")

        except UnicodeEncodeError:
            for data in cmd:
                response = data.decode(self.CHARSET[1],'replace').split()
        except UnicodeDecodeError:
            for data in cmd:
                response = data.decode(self.CHARSET[1],'replace').split()
        except AssertionError as ae:
            self.Base.logs.error(f"Assertion error : {ae}")
        pass

    def __ssl_context(self) -> ssl.SSLContext:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        self.Base.logs.debug(f'SSLContext initiated with verified mode {ctx.verify_mode}')

        return ctx