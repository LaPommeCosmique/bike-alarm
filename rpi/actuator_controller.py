import mqtt_client
import amqp_client
import http_client
import json
import logging

## ACTUATOR CONTROLLER

## Questions - does HTTP server publish to AMQP or Elasticsearch, does actuator controller have to query Elasticsearch?
## Does sensor_controller need to subscribe to AMQP to determine if user turns lock status on/off?
## If HTTP server publishes to AMQP, does it publish buzzer sounder through tamper/compromised topics? or specific user topic?

logging.basicConfig(format="%(asctime)s | %(name)s | %(levelname)s | %(message)s", level=logging.INFO)

# initialization? (turn off led and buzzer)

## MESSAGE HANDLERS
def on_lock_status_message(channel, method, properties, msg):
    try:
        msg = json.loads(str(msg.decode("utf-8")))
        if msg is not None:
            if msg["status"]:
                mqttc.publish(lock_status_led_topic, json.dumps(msg))
            else:
                mqttc.publish(lock_status_led_topic, json.dumps(msg))
    except Exception as e:
        logging.warning(f'{e}')

def on_tamper_message(channel, method, properties, msg):
    try:
        msg = json.loads(str(msg.decode("utf-8")))
        if msg is not None:
            if msg["tamper"]:
                mqttc.publish(buzzer_topic, json.dumps({'buzzer':'tamper'}))
            else:
                mqttc.publish(buzzer_topic, json.dumps({'buzzer':'off'}))
    except Exception as e:
        logging.warning(f'{e}')


def on_compromised_message(channel, method, properties, msg):
    try:
        msg = json.loads(str(msg.decode("utf-8")))
        if msg is not None:
            if msg["compromised"]:
                mqttc.publish(buzzer_topic, json.dumps({'buzzer':'compromised'}))
            else:
                mqttc.publish(buzzer_topic, json.dumps({'buzzer':'off'}))
    except Exception as e:
        logging.warning(f'{e}')


# url_elastic = "http://192.168.68.68:32200"
# index_elastic = "temperature"

## AMQP CONNECTION PARAMETERS
ip_rabbit = "172.20.10.5"
port_rabbit = 30672
user_rabbit = "user"
pass_rabbit = "password"

## AMQP SUBSCRIBER QUEUES
lock_status_r_key_rabbit = "lock_status" # maybe
lock_status_queue_rabbit = "lock_status" # maybe
tamper_status_r_key_rabbit = "tamper_status"
tamper_status_queue_rabbit = "tamper_status"
compromised_status_r_key_rabbit = "compromised_status"
compromised_status_queue_rabbit = "compromised_status"

## CONNECT TO AMQP SERVER
amqp_client.message = None
amqp_channel = amqp_client.connect_to_broker(ip_rabbit, port=port_rabbit, user=user_rabbit, passw=pass_rabbit)
amqp_client.subscribe(amqp_channel, lock_status_queue_rabbit, on_lock_status_message)
amqp_client.subscribe(amqp_channel, tamper_status_queue_rabbit, on_tamper_message)
amqp_client.subscribe(amqp_channel, compromised_status_queue_rabbit, on_compromised_message)

## MQTT CONNECTION PARAMETERS
ip_mosquitto = "172.20.10.3"
lock_status_led_topic = "lock_status_led_topic"
buzzer_topic = "buzzer_topic"
mqttc = mqtt_client.connect(ip_mosquitto)

try:
    amqp_channel.start_consuming()
except KeyboardInterrupt:
    amqp_channel.stop_consuming()
amqp_channel.close()
