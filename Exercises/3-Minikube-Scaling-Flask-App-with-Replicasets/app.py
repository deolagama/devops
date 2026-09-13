from flask import Flask, jsonify, request
import socket
import os

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({
        "message": "Flash Sale Application",
        "served_by_pod": socket.gethostname()
    })

@app.route("/buy")
def buy():
    user = request.args.get("user", "guest")

    return jsonify({
        "message": "Purchase request processed",
        "user": user,
        "served_by_pod": socket.gethostname()
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
