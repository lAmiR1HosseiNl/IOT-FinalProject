from flask import Flask, jsonify, render_template_string
import paho.mqtt.client as mqtt
import threading
import time
import json

app = Flask(__name__)
data_points = []
last_msg_time = 0  # last message received (server time)

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "IOTProject4032ARMM"
DISCONNECT_THRESHOLD = 10  # seconds

# ---------------- MQTT Callback ----------------
def on_message(client, userdata, msg):
    global last_msg_time
    try:
        payload = json.loads(msg.payload.decode())
        server_time = time.time()
        last_msg_time = server_time

        esp_time = payload.get("timeStamp", 0)
        latency = server_time*1000 - esp_time  # in ms

        # Frequency: difference between consecutive ESP messages
        freq = None
        if data_points:
            freq = esp_time - data_points[-1]['esp_time']

        data_points.append({
            "time": time.strftime("%H:%M:%S"),
            "temp": payload.get("temperature"),
            "hum": payload.get("humidity"),
            "tempF": payload.get("temperatureFarenhait"),
            "heat": payload.get("heatIndexCelsius"),
            "esp_time": esp_time,
            "latency": latency,
            "freq": freq,
            "server_time": server_time
        })

        if len(data_points) > 50:
            data_points.pop(0)
    except:
        pass

# ---------------- MQTT Thread ----------------
def mqtt_thread():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.subscribe(MQTT_TOPIC)
    client.loop_forever()

threading.Thread(target=mqtt_thread, daemon=True).start()

# ---------------- Flask Routes ----------------
@app.route("/")
def index():
    template = """
    <!DOCTYPE html>
    <html>
    <head>
      <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
      <h2>ESP32 DHT Dashboard</h2>
      <div id="status" style="font-weight:bold; margin-bottom:10px;">Checking connection...</div>
      <canvas id="tempChart" height="150"></canvas>
      <canvas id="humChart" height="150"></canvas>
      <canvas id="freqChart" height="100"></canvas>
      <canvas id="latencyChart" height="100"></canvas>

      <script>
        let tempChart, humChart, freqChart, latencyChart;

        async function fetchData() {
          const resp = await fetch('/data');
          const dataPoints = await resp.json();
          const labels = dataPoints.map(d => d.time);

          const tempData = {
            labels: labels,
            datasets: [
              {label: 'Temperature (°C)', data: dataPoints.map(d=>d.temp), borderColor:'red', fill:false},
              {label: 'Heat Index (°C)', data: dataPoints.map(d=>d.heat), borderColor:'orange', fill:false}
            ]
          };

          const humData = {
            labels: labels,
            datasets: [
              {label: 'Humidity (%)', data: dataPoints.map(d=>d.hum), borderColor:'blue', fill:false}
            ]
          };

          const freqData = {
            labels: labels,
            datasets: [
              {label: 'Send Frequency (ms)', data: dataPoints.map(d=>d.freq || 0), borderColor:'green', fill:false}
            ]
          };

          const latencyData = {
            labels: labels,
            datasets: [
              {label: 'Latency (ms)', data: dataPoints.map(d=>d.latency), borderColor:'purple', fill:false}
            ]
          };

          // Update charts
          if (!tempChart) {
            tempChart = new Chart(document.getElementById('tempChart'), {type:'line', data:tempData});
            humChart = new Chart(document.getElementById('humChart'), {type:'line', data:humData});
            freqChart = new Chart(document.getElementById('freqChart'), {type:'line', data:freqData});
            latencyChart = new Chart(document.getElementById('latencyChart'), {type:'line', data:latencyData});
          } else {
            tempChart.data = tempData;
            humChart.data = humData;
            freqChart.data = freqData;
            latencyChart.data = latencyData;
            tempChart.update();
            humChart.update();
            freqChart.update();
            latencyChart.update();
          }

          // Check disconnection
          const now = Date.now()/1000;
          let lastMsgTime = 0;
          if(dataPoints.length > 0){
            lastMsgTime = dataPoints[dataPoints.length-1].server_time;
          }
          const disconnected = (now - lastMsgTime) > {{ threshold }};
          const statusDiv = document.getElementById('status');
          if(disconnected){
            statusDiv.innerHTML = "<span style='color:red'>Disconnected!</span>";
          } else {
            statusDiv.innerHTML = "<span style='color:green'>Connected</span>";
          }
        }

        setInterval(fetchData, 3000);
        fetchData();
      </script>
    </body>
    </html>
    """
    return render_template_string(template, threshold=DISCONNECT_THRESHOLD)

@app.route("/data")
def data():
    return jsonify(data_points)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
