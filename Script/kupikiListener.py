#!/usr/bin/env python
import pika
import subprocess
import json
import socket
# import string
# import random

# returnMessage = {}
# returnMessage["status"] = ""
# returnMessage["message"] = ""

# def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
#     return ''.join(random.choice(chars) for _ in range(size))

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()
channel.queue_declare(queue='kupiki.publish')
channel.queue_declare(queue='kupiki.reply')

systemHostname = socket.gethostname()
counterMsg = 0

def runCommand(command):
    returnCommandMessage = {}
    try:
        returnCommandMessage["message"] = subprocess.check_output(command, shell=True)
        returnCommandMessage["status"] = "success"
    except subprocess.CalledProcessError, e:
        returnCommandMessage["message"] = e.output
        returnCommandMessage["status"] = "failed"
    return returnCommandMessage

def default():
    returnMessage = {}
    returnMessage["status"] = "failed"
    returnMessage["message"] = "Unknown command request"
    return returnMessage

def data_cpu():
    return runCommand("/usr/bin/rrdtool fetch /var/lib/collectd/rrd/" + systemHostname + "/processes/ps_state-running.rrd AVERAGE -r 60 -s -1h")

def data_memory():
    return runCommand("/usr/bin/rrdtool fetch /var/lib/collectd/rrd/" + systemHostname + "/memory/memory-used.rrd AVERAGE -r 60 -s -1h")

def data_disk():
    return runCommand("/usr/bin/rrdtool fetch /var/lib/collectd/rrd/" + systemHostname + "/df-root/df_complex-used.rrd AVERAGE -r 60 -s -1h")

def switcher(command):
    commandSwitcher = {
        "data cpu" : data_cpu,
        "data memory" : data_memory,
        "data disk" : data_disk
    }
    func = commandSwitcher.get(command, default)
    return func()


def callback(ch, method, properties, body):
    global counterMsg
    print(" [%d] Received %r" % (counterMsg, body))

    returnMessage = switcher(body)
    output = json.dumps(returnMessage, ensure_ascii=False)
    # print(output);
    ch.basic_publish(exchange='',
                    routing_key=properties.reply_to,
                    properties=pika.BasicProperties(correlation_id = properties.correlation_id),
                    body=output)
    ch.basic_ack(delivery_tag=method.delivery_tag)
    print(" [%d] Sent reply" % counterMsg)
    counterMsg = counterMsg + 1

channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue='kupiki.publish', on_message_callback=callback)

print(' [*] Waiting for messages. To exit press CTRL+C')
channel.start_consuming()
