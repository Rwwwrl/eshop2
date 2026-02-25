import json
import os
import sys
from typing import Callable

import pika

from messaging import AsyncCommand, Message, SomeAsyncCommand1, SomeEvent1, SomeEvent2
from utils import get_message_class_path


def handle_event1(event: SomeEvent1):
    print(repr(event), handle_event1.__name__)


def handle_event2(event: SomeEvent2):
    print(repr(event), handle_event2.__name__)


def handle_async_comand1(async_command: AsyncCommand):
    print(repr(async_command), handle_async_comand1.__name__)


message_to_handler: dict[Message, Callable[[Message], None]] = {
    SomeEvent1: handle_event1,
    SomeEvent2: handle_event2,
    SomeAsyncCommand1: handle_async_comand1,
}


def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host="localhost"))
    channel = connection.channel()
    channel.basic_qos(prefetch_count=1)

    QUEUE_NAME = "wearables"
    channel.queue_declare(queue=QUEUE_NAME)

    for message in message_to_handler:
        exchange_name = get_message_class_path(message)
        channel.exchange_declare(exchange=exchange_name, exchange_type="fanout")
        channel.queue_bind(exchange=exchange_name, queue=QUEUE_NAME)

    def callback(ch, method, properties, body):
        try:
            message = json.loads(body)

            match message["message_class_path"]:
                case "messaging.SomeEvent1":
                    handle_event1(event=message)
                case "messaging.SomeEvent2":
                    handle_event2(event=message)
                case "messaging.SomeAsyncCommand1":
                    handle_async_comand1(async_command=message)
        except Exception:
            print("log exception ...")
        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
    print(" [wearables] Waiting for messages. To exit press CTRL+C")
    channel.start_consuming()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
