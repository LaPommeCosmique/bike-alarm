import mqtt_client
import amqp_client
import json, time
import logging

## SENSOR CONTROLLER

logging.basicConfig(format="%(asctime)s | %(name)s | %(levelname)s | %(message)s", level=logging.INFO)

## AMQP CONNECTION PARAMETERS
ip_rabbit = "<rabbitmq ip address>"
port_rabbit = 30672
user_rabbit = "<rabbitmq username>"
pass_rabbit = "<rabbitmq password>"

## AMQP PUBLISHER EXCHANGES
ex_rabbit = "amq.topic"
rkey_rabbit_tamper_status = "tamper_status"
queue_rabbit_tamper_status = "tamper_status"
rkey_rabbit_compromised_status = "compromised_status"
queue_rabbit_compromised_status = "compromised_status"
rkey_rabbit_lock_status = "lock_status" # maybe
queue_rabbit_lock_status = "lock_status" # maybe

## CONNECT TO AMQP SERVER
amqp_ch = amqp_client.connect_to_broker(ip_rabbit, port=port_rabbit, user=user_rabbit, passw=pass_rabbit)
amqp_client.create_queue(amqp_ch, ex_rabbit, rkey_rabbit_tamper_status, queue_rabbit_tamper_status)
amqp_client.create_queue(amqp_ch, ex_rabbit, rkey_rabbit_compromised_status, queue_rabbit_compromised_status)

# maybe
amqp_client.create_queue(amqp_ch, ex_rabbit, rkey_rabbit_compromised_status, queue_rabbit_compromised_status)

## MQTT CONNECTION
ip_mosquitto = "localhost"

## MQTT TOPICS
topic_accel = "accel_topic" # accelerometer
topic_circuit = "circuit_topic" # movement (reed, wire)
topic_lock_status = "lock_status_topic" # maybe
topics_mosquitto = [
    (topic_accel, 1),
    (topic_circuit, 1),
    (topic_lock_status, 1),  # maybe
]

## CONNECT TO MQTT
mqtt_client.message = None
mqttc = mqtt_client.connect(ip_mosquitto)
mqttc.subscribe(topics_mosquitto)
mqttc.loop_start()

## MQTT MESSAGE HANDLERS
tamper_status = False
compromised_status = False
lock_status = True

accel_threshold = 0.5
def handle_accel_message(msg):
    global tamper_status
    if lock_status and not tamper_status and not compromised_status:
        # check if acceleration exceeds a threshold
        x_accel = msg['x_accel']
        y_accel = msg['y_accel']
        z_accel = msg['z_accel']
        accel_mag = (x_accel**2+y_accel**2+z_accel**2)**0.5
        if accel_mag  > accel_threshold:
            tamper_status = True
            amqp_ch.basic_publish(ex_rabbit, rkey_rabbit_tamper_status, json.dumps({"tamper": True, "mag": accel_mag}))

def handle_circuit_message(msg):
    global compromised_status
    if lock_status and not compromised_status:
        if msg["circuit"] == False:
            compromised_status = True
            amqp_ch.basic_publish(ex_rabbit, rkey_rabbit_compromised_status, json.dumps({"compromised": True}))

def handle_lock_status_message(msg):
    global lock_status, tamper_status, compromised_status
    if msg["status"]:
        lock_status = True
    else:
        lock_status = tamper_status = compromised_status = False
    amqp_ch.basic_publish(ex_rabbit, rkey_rabbit_lock_status, json.dumps(msg))

while True:
    if mqtt_client.message is not None:
        try:
            topic = mqtt_client.message.topic
            msg = json.loads(str(mqtt_client.message.payload.decode("utf-8")))
            if topic == topic_accel:
                handle_accel_message(msg)
            elif topic == topic_circuit:
                handle_circuit_message(msg)
        except Exception as e:
            logging.warning(f"{e}")
