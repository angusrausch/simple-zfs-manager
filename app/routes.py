from flask import Blueprint, jsonify

def create_routes_blueprint():
    bp = Blueprint('routes', __name__)

    @bp.route('/health')
    def health_check():
        return jsonify({"status": "pass"}), 200

    return bp