import json

import pika

from messaging import SomeAsyncCommand1, SomeEvent1, SomeEvent2
from utils import get_message_class_path


def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host="localhost"))
    channel = connection.channel()

    for message in (
        SomeEvent1(value1="some value 1"),
        SomeEvent2(value2="some value 2"),
        SomeAsyncCommand1(value1="some async command 1"),
    ):
        message = {**message.model_dump(), "message_class_path": get_message_class_path(type(message))}
        message = json.dumps(message)

        channel.basic_publish(
            exchange=get_message_class_path(SomeEvent1),
            routing_key="",
            body=message,
        )
        print(f" [x] Sent '{message}'")

    connection.close()


if __name__ == "__main__":
    main()
