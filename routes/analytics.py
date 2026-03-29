from flask import Blueprint, request, jsonify
from services.analytics_service import AnalyticsService

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/summary', methods=['GET'])
def summary():
    return jsonify(AnalyticsService.get_summary())


@analytics_bp.route('/by-category', methods=['GET'])
def by_category():
    return jsonify(AnalyticsService.by_category())


@analytics_bp.route('/by-date', methods=['GET'])
def by_date():
    period = request.args.get('period', 'daily')
    days = int(request.args.get('days', 30))
    return jsonify(AnalyticsService.by_date(period, days))


@analytics_bp.route('/monthly', methods=['GET'])
def monthly():
    return jsonify(AnalyticsService.monthly_breakdown())


@analytics_bp.route('/budget-vs-actual', methods=['GET'])
def budget_vs_actual():
    return jsonify(AnalyticsService.budget_vs_actual())


@analytics_bp.route('/recent', methods=['GET'])
def recent():
    limit = int(request.args.get('limit', 10))
    return jsonify(AnalyticsService.recent_expenses(limit))
