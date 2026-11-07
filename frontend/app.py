"""Flask application for local frontend development and testing."""

import os
from flask import Flask, send_from_directory

app = Flask(
    __name__,
    static_folder=".",
    static_url_path="",
)


@app.route("/")
def index():
    """Serves the static index.html."""
    return send_from_directory(".", "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    """Serves css, js, and static assets."""
    return send_from_directory(".", filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "1") == "1"
    print(f"Starting HF Backend Frontend on http://127.0.0.1:{port} ...")
    app.run(host="0.0.0.0", port=port, debug=debug)

