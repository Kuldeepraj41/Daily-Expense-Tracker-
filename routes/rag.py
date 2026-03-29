from flask import Blueprint, request, jsonify
from services.rag_service import RAGService
from services.analytics_service import AnalyticsService
from services.expense_service import ExpenseService

rag_bp = Blueprint('rag', __name__)

_rag = RAGService()


@rag_bp.route('/query', methods=['POST'])
def rag_query():
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({'error': 'query field is required'}), 400

    user_query = data['query'].strip()
    if not user_query:
        return jsonify({'error': 'Query cannot be empty'}), 400

    expenses = ExpenseService.get_all()
    budgets = ExpenseService.get_budgets()

    result = _rag.query(user_query, expenses, budgets)
    return jsonify(result)


@rag_bp.route('/suggestions', methods=['GET'])
def suggestions():
    stats = AnalyticsService.get_summary()
    questions = _rag.get_suggested_questions(stats)
    return jsonify({'questions': questions})
