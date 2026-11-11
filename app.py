"""Small HTTP application for the Kaizen CI/CD classroom lab."""

import os
import socket

from flask import Flask, jsonify, request


def create_app():
    app = Flask(__name__)
    version = os.getenv("APP_VERSION", "local")

    @app.get("/")
    def home():
        return jsonify(
            message="Hello from Kaizen!",
            version=version,
            hostname=socket.gethostname(),
        )

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.post("/api/add")
    def add():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify(error="Provide a JSON object with integers a and b"), 400
        a, b = body.get("a"), body.get("b")
        if type(a) is not int or type(b) is not int:
            return jsonify(error="a and b must be integers"), 400
        return jsonify(result=a + b)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
