import os
import sys
import time
import uuid

import pika


def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host="localhost"))
    channel = connection.channel()

    channel.exchange_declare(exchange="hello_world_event", exchange_type="fanout")
    channel.queue_declare(queue="hello-world")
    channel.queue_bind(exchange="hello_world_event", queue="hello-world")

    _id = uuid.uuid4()

    def callback(ch, method, properties, body):
        print(f" [hello-world] Received {body}, _id = {_id}")
        time.sleep(2)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f" [hello-world] ACKED: {body}, _id = {_id}")

    channel.basic_consume(queue="hello-world", on_message_callback=callback)
    print(" [hello-world] Waiting for messages. To exit press CTRL+C")
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
