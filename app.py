from flask import Flask, render_template, jsonify
import json, os, time

app = Flask(__name__)
DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        return json.load(open(DATA_FILE))
    return {"movies": []}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/movies")
def movies():
    return jsonify(load_data()["movies"])

@app.route("/api/trending")
def trending():
    data = load_data()["movies"]

    def score(m):
        return m.get("views",0)*2 + (5 - (time.time()-m.get("timestamp",0))/86400)

    return jsonify(sorted(data, key=score, reverse=True))

if __name__ == "__main__":
    app.run(debug=True)