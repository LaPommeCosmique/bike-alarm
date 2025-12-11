import json
import time
from typing import Optional

import pandas as pd
import pika
import requests
import streamlit as st

st.set_page_config(page_title="Bike Monitor", layout="wide", initial_sidebar_state="expanded")

# -----------------------------
# Styles to mimic the mock UI
# -----------------------------
st.markdown(
    """
    <style>
        .bezel-btn button {
            border: 2px solid #444 !important;
            box-shadow: inset -2px -2px 0 #bbb, inset 2px 2px 0 #fff, 2px 2px 0 #0002;
            border-radius: 4px !important;
            font-weight: 600;
        }
        .battery {
            display: inline-flex; align-items: center; gap: 6px; font-weight: 600;
        }
        .battery .icon { font-size: 22px; }
        .topbar {
            border-bottom: 1px solid #e5e5e5; padding: 6px 8px; margin-bottom: 12px;
            display: flex; align-items: center; gap: 8px; color: #555;
        }
        .topbar input { width: 100%; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Sidebar - connection settings
# -----------------------------
st.sidebar.header("Connections")

# AMQP
st.sidebar.subheader("AMQP (RabbitMQ)")
amqp_host = st.sidebar.text_input("Host / IP", value="172.20.10.5")
amqp_port = st.sidebar.number_input("Port", value=30672, step=1)
amqp_user = st.sidebar.text_input("Username", value="user")
amqp_pass = st.sidebar.text_input("Password", value="password")
amqp_vhost = st.sidebar.text_input("vhost", value="/")
exchange = st.sidebar.text_input("Exchange", value="amq.topic")

st.sidebar.caption("Routing keys for each command")
rk_sound = st.sidebar.text_input("Sound alarm topic", value="tamper_status")
rk_silence = st.sidebar.text_input("Silence alarm topic", value="tamper_status")
rk_toggle = st.sidebar.text_input("On/Off topic", value="lock_status")

# Elasticsearch
st.sidebar.subheader("Elasticsearch")
es_base = st.sidebar.text_input("Base URL", value="http://172.20.10.5:32200")
activity_index = st.sidebar.text_input("Activity index", value="activity")
device_id = None

# Init last-fire timestamps once
if "last_fire" not in st.session_state:
    st.session_state["last_fire"] = {
        "sound": 0.0,
        "disable": 0.0,  # kept for compatibility, not used anymore
        "silence": 0.0,
    }

DEBOUNCE_SEC = 0.5  # minimum time between sends per button
now = time.time()

# ---------------------------------
# Helpers: AMQP + Elasticsearch
# ---------------------------------
def _amqp_params():
    creds = pika.PlainCredentials(amqp_user, amqp_pass)
    return pika.ConnectionParameters(
        host=amqp_host,
        port=int(amqp_port),
        virtual_host=amqp_vhost,
        credentials=creds,
        heartbeat=30,
    )


def publish_command(routing_key: str, cmd: str, extra: Optional[dict] = None) -> str:
    payload = {"cmd": cmd, "ts": time.time()}
    if extra:
        payload.update(extra)
    body = json.dumps(payload).encode("utf-8")
    try:
        con = pika.BlockingConnection(_amqp_params())
        ch = con.channel()
        ch.basic_publish(exchange=exchange, routing_key=routing_key, body=body)
        con.close()
        return "OK"
    except Exception as e:
        return f"ERROR: {e}"


def es_activity_rows(limit: int = 100) -> pd.DataFrame:
    try:
        url = f"{es_base.rstrip('/')}/{activity_index}/_search"
        query = {"query": {"match_all": {}}}
        r = requests.get(
            url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(query),
            timeout=10,
        )
        r.raise_for_status()
        rows = [
            {
                "activity": h["_source"].get("activity"),
                "timestamp": h["_source"].get("timestamp"),
            }
            for h in r.json().get("hits", {}).get("hits", [])
        ]
        return pd.DataFrame(rows)
    except Exception as e:
        return pd.DataFrame(
            [{"activity": f"ERROR: {e}", "timestamp": None}]
        )


# ---------------------------------
# Top bar
# ---------------------------------
with st.container():
    st.markdown(
        '<div class="topbar">🔍 <input disabled value="https://www.bike.ai"> </div>',
        unsafe_allow_html=True,
    )

# ---------------------------------
# Tabs
# ---------------------------------
monitor_tab, activity_tab = st.tabs(["Monitoring", "Activity Log"])

# ---------------------------------
# Monitoring tab
# ---------------------------------
with monitor_tab:
    st.write("")
    colA, colB, colC = st.columns([1, 1, 1])

    # Left column: Sound + Silence
    with colA:
        st.markdown("#### ")
        c1, c2 = st.columns(2)

        # Sound Alarm
        with c1:
            if st.button(
                "Sound Alarm",
                use_container_width=True,
                key="sound",
                help="Send cmd: sound_alarm",
                type="primary",
            ):
                now = time.time()
                if now - st.session_state["last_fire"]["sound"] > DEBOUNCE_SEC:
                    st.session_state["last_fire"]["sound"] = now
                    res = publish_command(rk_sound, True)
                    st.toast(f"Sound Alarm → {res}")

        # Silence Alarm
        with c2:
            if st.button(
                "Silence Alarm",
                use_container_width=True,
                key="silence",
                help="Send cmd: silence_alarm",
            ):
                now = time.time()
                if now - st.session_state["last_fire"]["sound"] > DEBOUNCE_SEC:
                    st.session_state["last_fire"]["sound"] = now
                    res = publish_command(rk_silence, False)
                    st.toast(f"Silence → {res}")

    # Right side: On/Off toggle only
    with colC:
        st.markdown("#### ")
        alarm_on = st.toggle("Alarm On/Off", value=True)

        if alarm_on:
            # Send ON command
            publish_command(rk_toggle, "on")
            # st.toast("Alarm turned ON")
        else:
            # Send OFF command
            publish_command(rk_toggle, "off")
            # st.toast("Alarm turned OFF")


# ---------------------------------
# Activity Log tab
# ---------------------------------
with activity_tab:
    st.write("Latest events from Elasticsearch)")
    limit = 1000
    if st.button("Refresh log"):
        st.session_state["_act_force"] = True

    now = time.time()
    last = st.session_state.get("_act_ts", 0)
    do_fetch = (now - last > 20) or st.session_state.get("_act_force")
    if do_fetch:
        df = es_activity_rows(limit)
        st.session_state["_act_df"] = df
        st.session_state["_act_ts"] = now
        st.session_state["_act_force"] = False

    df = st.session_state.get(
        "_act_df", pd.DataFrame(columns=["activity", "timestamp"])
    )
    st.dataframe(df, use_container_width=True)
