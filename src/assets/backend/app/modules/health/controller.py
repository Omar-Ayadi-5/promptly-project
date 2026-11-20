from flask import Blueprint, jsonify

blueprint = Blueprint("health", __name__)


@blueprint.route("/api/server_health", methods=['GET'])
def check_server_health():
    return jsonify({"status": "ok"}), 200
