from flask import Blueprint, request, jsonify
from services.ml_service import MLService

ml_bp = Blueprint('ml', __name__)


@ml_bp.route('/suggest-category', methods=['POST'])
def suggest_category():
    data = request.get_json()
    if not data or 'description' not in data:
        return jsonify({'error': 'description is required'}), 400
    result = MLService.suggest_category(data['description'])
    return jsonify(result)


@ml_bp.route('/forecast', methods=['GET'])
def forecast():
    days = int(request.args.get('days', 30))
    result = MLService.forecast_spending(days)
    return jsonify(result)


@ml_bp.route('/anomalies', methods=['GET'])
def anomalies():
    result = MLService.detect_anomalies()
    return jsonify(result)


@ml_bp.route('/burn-rate', methods=['GET'])
def burn_rate():
    result = MLService.budget_burn_rate()
    return jsonify(result)


@ml_bp.route('/insights', methods=['GET'])
def insights():
    result = MLService.generate_insights()
    return jsonify(result)
