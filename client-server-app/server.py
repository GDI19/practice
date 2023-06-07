import argparse
import json
import select
from socket import *
import sys
import time
import logging
import logs.server_log_config
from logs.server_log_config import log


server_log = logging.getLogger('server_log')


from common.utils import get_message, send_message

DEFAULT_PORT = 7777

@log
def process_client_message(message, messages_list, client):
    """
    Receive message from client, check it.
    :param message: dict
    :return: response (dict)
    """
    if 'time' in message and 'action' in message and  message['account_name']:
        server_log.debug('Processed msg with correct info')
        if message['action'] == 'presence':
            send_message(client, {'response': 200})
            return
        
        elif message['action'] == 'message' and 'message_text' in message:
            messages_list.append((message['account_name'], message['message_text']))
            return
    
    server_log.critical('Processed msg with noncorrect info')
    return {'response': 400, 'error': 'Bad Request'}


@log
def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', default='', nargs='?')
    parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p

    if not 1024 < listen_port < 65535:
        server_log.critical(
            f'Попытка запуска сервера с указанием неподходящего порта '
            f'{listen_port}. Допустимы адреса с 1024 до 65535.')
        sys.exit(1)
    return listen_address, listen_port


def main():
    server_log.debug('Server has been launched...')
    listen_address, listen_port = arg_parser()

    server_log.info(
        f'Запущен сервер: {listen_address} порт: {listen_port}, '
        f'Если адрес не указан, принимаются соединения с любых адресов.')

    transport = socket(AF_INET, SOCK_STREAM)
    # transport.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    transport.bind((listen_address, listen_port))
    transport.listen(5)
    transport.settimeout(1)

    clients = []
    messages = []

    while True:
        try:
            client, addr = transport.accept()
        except OSError as err:
            pass
        else:
            print("Получен запрос на соединение с %s" % str(addr))
            clients.append(client)

        read_lst = [] 
        write_lst = []


        try:
            read_lst, write_lst, err_lst = select.select(clients, clients, [], 0)
        except OSError:
            pass

        if read_lst:
            for client_with_message in read_lst:
                try:
                    msg_from_client = get_message(client_with_message)
                    server_log.info(f'received message from client: {msg_from_client}')
                    process_client_message(msg_from_client, messages, client_with_message)
                except:
                    server_log.error(f'Клиент {client_with_message.getpeername()} отключился от сервера.')
                    clients.remove(client_with_message)
        

        while messages and write_lst:
            message = {
                'action': 'message',
                'sender': messages[0][0],
                'time': time.time(),
                'message_text': messages[0][1]
            }
            del messages[0]
            for waiting_client in write_lst:
                try:
                    send_message(waiting_client, message)
                except:
                    server_log.info(f'Клиент {waiting_client.getpeername()} отключился от сервера.')
                    clients.remove(waiting_client)


if __name__ == '__main__':
    main()