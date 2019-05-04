#!/usr/bin/env python
import pika
from subprocess import check_output, CalledProcessError, STDOUT
import json
import socket
import os

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()
channel.queue_declare(queue='kupiki.publish')
channel.queue_declare(queue='kupiki.reply')

systemHostname = socket.gethostname()
counterMsg = 0

def runCommand(command):
    returnCommandMessage = {}
    try:
        returnCommandMessage["message"] = check_output(command, stderr=STDOUT, shell=True)
        returnCommandMessage["status"] = "success"
    except CalledProcessError, e:
        returnCommandMessage["message"] = e.output
        returnCommandMessage["status"] = "failed"
    return returnCommandMessage

def default(message="Unknown command request"):
    if (type(message) != type('')):
        message="Unknown command request"
    returnMessage = {}
    returnMessage["status"] = "failed"
    returnMessage["message"] = message
    return returnMessage

# ######## Data

def getDataCPU():
    return runCommand("/usr/bin/rrdtool fetch /var/lib/collectd/rrd/" + systemHostname + "/processes/ps_state-running.rrd AVERAGE -r 60 -s -1h")

def getDataMemory():
    return runCommand("/usr/bin/rrdtool fetch /var/lib/collectd/rrd/" + systemHostname + "/memory/memory-used.rrd AVERAGE -r 60 -s -1h")

def getDataDisk():
    return runCommand("/usr/bin/rrdtool fetch /var/lib/collectd/rrd/" + systemHostname + "/df-root/df_complex-used.rrd AVERAGE -r 60 -s -1h")

def getDataNetflow():
    if os.path.isfile("/var/cache/nfdump/.nfstat"):
        return runCommand("/usr/bin/nfexpire -l /var/cache/nfdump | grep :")
    else:
        return default("Unable to find statistics of Netflow. Check the Kupiki installation.")

def commandData(commandParametersArray):
    if (len(commandParametersArray) != 1):
        return default()
    else:
        commandParameterSwitcher = {
            "cpu" : getDataCPU,
            "memory" : getDataMemory,
            "disk" : getDataDisk,
            "netflow" : getDataNetflow
        }
        func = commandParameterSwitcher.get(commandParametersArray[0], default)
        return func()

# ######## Services

def getAllServices(commandParametersArray):
    return runCommand("/usr/sbin/service --status-all")

def startService(commandParametersArray):
    if (len(commandParametersArray) != 1):
        return default()
    else:
        return runCommand("/usr/sbin/service {} {}".format(commandParametersArray[0], "start"))

def restartService(commandParametersArray):
    if (len(commandParametersArray) != 1):
        return default()
    else:
        return runCommand("/usr/sbin/service {} {}".format(commandParametersArray[0], "restart"))

def stopService(commandParametersArray):
    print(commandParametersArray)
    if (len(commandParametersArray) != 1):
        return default()
    else:
        return runCommand("/usr/sbin/service {} {}".format(commandParametersArray[0], "stop"))

def commandService(commandParametersArray):
    if (len(commandParametersArray) < 1):
        return default()
    else:
        commandParameterSwitcher = {
            "all" : getAllServices,
            "restart" : startService,
            "start" : startService,
            "stop" : stopService
        }
        func = commandParameterSwitcher.get(commandParametersArray[0], default)
        return func(commandParametersArray[1:])

# ######## Hostpad

def getHostapdConfiguration(commandParametersArray):
    return runCommand("cat /etc/hostapd/hostapd.conf")

def saveHostapdConfiguration(commandParametersArray):
    return runCommand("cat /etc/hostapd/hostapd.conf")

def commandHostapd(commandParametersArray):
    if (len(commandParametersArray) < 1):
        return default()
    else:
        commandParameterSwitcher = {
            "load" : getHostapdConfiguration,
            "save" : saveHostapdConfiguration
        }
        func = commandParameterSwitcher.get(commandParametersArray[0], default)
        return func(commandParametersArray[1:])

# ######## Portal

def getPortalConfiguration(commandParametersArray):
    return runCommand("cat /usr/share/nginx/portal/js/configuration.json")

def savePortalConfiguration(commandParametersArray):
    return runCommand("cat /etc/hostapd/hostapd.conf")

def commandPortal(commandParametersArray):
    if (len(commandParametersArray) < 1):
        return default()
    else:
        commandParameterSwitcher = {
            "load" : getPortalConfiguration,
            "save" : savePortalConfiguration
        }
        func = commandParameterSwitcher.get(commandParametersArray[0], default)
        return func(commandParametersArray[1:])

# ######## Temperature

def getTemperature():
    return runCommand("/opt/vc/bin/vcgencmd measure_temp | cut -d= -f2 | cut -d\' -f1 || echo '-'")

def commandTemperature(commandParametersArray):
    if (len(commandParametersArray) == 0):
        return getTemperature()
    else:
        return default()

# ######## System

def getSystemCheck():
    return runCommand("/usr/bin/apt list --upgradable 2>/dev/null | /usr/bin/wc -l | /usr/bin/awk '{print$1-1}'")

def getSystemUpdate():
    return runCommand("/usr/bin/apt-get update -y -qq")

def getSystemUpgrade():
    return runCommand("/usr/bin/apt-get -qq -y -o 'Dpkg::Options::=--force-confdef' -o 'Dpkg::Options::=--force-confold' upgrade")

def systemReboot():
    return runCommand("/sbin/shutdown -r -t 1")

def systemShutdown():
    return runCommand("/sbin/shutdown -t 1")

def commandSystem(commandParametersArray):
    if (len(commandParametersArray) != 1):
        return default()
    else:
        commandParameterSwitcher = {
            "check" : getSystemCheck,
            "update" : getSystemUpdate,
            "upgrade" : getSystemUpgrade,
            "reboot" : systemReboot,
            "shutdown" : systemShutdown
        }
        func = commandParameterSwitcher.get(commandParametersArray[0], default)
        return func()

# ######## Mac Authentication

def getMacAuthConfiguration(commandParametersArray):
    returnMessage = {}
    returnMessage['status'] = 'success'
    resultMessage = {}
    resultMessage['active'] = True
    resultMessage['password'] = ''
    macAuthActivated = runCommand("grep HS_MACAUTH= /etc/chilli/config | cut -d'=' -f1 | grep '#' > /dev/null")
    if (macAuthActivated['status'] == "failed"): resultMessage['active'] = False
    macAuthActivated = runCommand("grep HS_MACAUTH=off /etc/chilli/config > /dev/null")
    if (macAuthActivated['status'] == "failed"): resultMessage['active'] = True
    macAuthPassword = runCommand("grep HS_MACPASSWD= /etc/chilli/config | cut -d'=' -f2")
    if (macAuthPassword['status'] != "failed"): resultMessage['password'] = macAuthPassword['message']
    returnMessage['message'] = resultMessage
    return returnMessage

def saveMacAuthConfiguration(commandParametersArray):
    return runCommand("cat /etc/hostapd/hostapd.conf")

def commandMacAuth(commandParametersArray):
    if (len(commandParametersArray) != 1):
        return default()
    else:
        commandParameterSwitcher = {
            "load" : getMacAuthConfiguration,
            "save" : saveMacAuthConfiguration
        }
        func = commandParameterSwitcher.get(commandParametersArray[0], default)
        return func(commandParametersArray[1:])

# ######## Main process

def switcher(command):
    commandArray = command.split()
    if (len(commandArray) < 1):
        return default()
    else:
        commandSwitcher = {
            "data" : commandData,
            "service" : commandService,
            "temperature" : commandTemperature,
            "system" : commandSystem,
            "hostapd" : commandHostapd,
            "portal" : commandPortal,
            "macauth" : commandMacAuth
        }
        func = commandSwitcher.get(commandArray[0], default)
        return func(commandArray[1:])

def callback(ch, method, properties, body):
    global counterMsg
    print(" [{}] Received command {} for id {}".format(counterMsg, body, properties.correlation_id))

    returnMessage = switcher(body)
    output = json.dumps(returnMessage, ensure_ascii=False)
    print(" [{}] Sending reply to {} on {}".format(counterMsg, properties.correlation_id, properties.reply_to))
    ch.basic_publish(exchange='',
                    routing_key=properties.reply_to,
                    properties=pika.BasicProperties(correlation_id = properties.correlation_id),
                    body=output)
    ch.basic_ack(delivery_tag=method.delivery_tag)
    print(" [{}] Message content is {}".format(counterMsg, output))
    counterMsg = counterMsg + 1

channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue='kupiki.publish', on_message_callback=callback)

print(' [*] Waiting for messages. To exit press CTRL+C')
channel.start_consuming()
