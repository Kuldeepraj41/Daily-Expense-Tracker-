from flask import Blueprint, request, jsonify
from services.expense_service import ExpenseService
from database.db import seed_sample_expenses, db
import io
import pandas as pd
from datetime import date

expenses_bp = Blueprint('expenses', __name__)


@expenses_bp.route('/', methods=['GET'])
def list_expenses():
    category = request.args.get('category')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    search = request.args.get('search')
    sort_by = request.args.get('sort_by', 'date')
    order = request.args.get('order', 'desc')
    return jsonify(ExpenseService.get_all(category, start_date, end_date, search, sort_by, order))


@expenses_bp.route('/<int:expense_id>', methods=['GET'])
def get_expense(expense_id):
    return jsonify(ExpenseService.get_by_id(expense_id))


@expenses_bp.route('/', methods=['POST'])
def create_expense():
    data = request.get_json()
    if not data or not all(k in data for k in ('amount', 'description', 'category', 'date')):
        return jsonify({'error': 'Missing required fields: amount, description, category, date'}), 400
    return jsonify(ExpenseService.create(data)), 201


@expenses_bp.route('/<int:expense_id>', methods=['PUT'])
def update_expense(expense_id):
    data = request.get_json()
    return jsonify(ExpenseService.update(expense_id, data))


@expenses_bp.route('/<int:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    return jsonify(ExpenseService.delete(expense_id))


@expenses_bp.route('/categories', methods=['GET'])
def list_categories():
    return jsonify(ExpenseService.get_categories())


@expenses_bp.route('/categories', methods=['POST'])
def create_category():
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': 'Category name is required'}), 400
    return jsonify(ExpenseService.create_category(data)), 201


@expenses_bp.route('/budgets', methods=['GET'])
def list_budgets():
    return jsonify(ExpenseService.get_budgets())


@expenses_bp.route('/budgets', methods=['POST'])
def set_budget():
    data = request.get_json()
    if not data or not all(k in data for k in ('category', 'limit_amount')):
        return jsonify({'error': 'category and limit_amount are required'}), 400
    return jsonify(ExpenseService.set_budget(data)), 201


@expenses_bp.route('/budgets/<int:budget_id>', methods=['DELETE'])
def delete_budget(budget_id):
    return jsonify(ExpenseService.delete_budget(budget_id))


@expenses_bp.route('/seed', methods=['POST'])
def seed_data():
    result = seed_sample_expenses()
    return jsonify(result), 201


@expenses_bp.route('/clear/preview', methods=['POST'])
def preview_clear():
    """Return how many expenses WOULD be deleted for the given filter — no data changed."""
    from database.models import Expense
    data = request.get_json() or {}
    mode = data.get('mode', 'all')
    try:
        query = Expense.query
        if mode == 'date_range':
            date_from = data.get('date_from')
            date_to   = data.get('date_to')
            if date_from:
                query = query.filter(Expense.date >= date.fromisoformat(date_from))
            if date_to:
                query = query.filter(Expense.date <= date.fromisoformat(date_to))
        elif mode == 'category':
            cats = data.get('categories', [])
            if cats:
                query = query.filter(Expense.category.in_(cats))
            else:
                return jsonify({'count': 0, 'note': 'No categories selected'})
        elif mode == 'single_date':
            single = data.get('single_date')
            if single:
                query = query.filter(Expense.date == date.fromisoformat(single))
        return jsonify({'count': query.count()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@expenses_bp.route('/clear', methods=['DELETE'])
def clear_all_data():
    """
    Delete expenses (and optionally budgets) based on a filter mode.

    Body JSON:
        mode          : "all" | "date_range" | "single_date" | "category"
        date_from     : "YYYY-MM-DD"  (for date_range)
        date_to       : "YYYY-MM-DD"  (for date_range)
        single_date   : "YYYY-MM-DD"  (for single_date)
        categories    : ["Food & Dining", ...]  (for category)
        clear_budgets : true | false  (only respected when mode == "all")
    """
    from database.models import Expense, Budget
    data = request.get_json() or {}
    mode = data.get('mode', 'all')

    try:
        budgets_deleted = 0

        if mode == 'all':
            expense_count = Expense.query.count()
            Expense.query.delete()
            if data.get('clear_budgets', True):
                budgets_deleted = Budget.query.count()
                Budget.query.delete()
            db.session.commit()
            return jsonify({
                'message': 'All data cleared successfully',
                'expenses_deleted': expense_count,
                'budgets_deleted':  budgets_deleted,
            })

        elif mode == 'date_range':
            date_from = data.get('date_from')
            date_to   = data.get('date_to')
            query = Expense.query
            if date_from:
                query = query.filter(Expense.date >= date.fromisoformat(date_from))
            if date_to:
                query = query.filter(Expense.date <= date.fromisoformat(date_to))
            expenses = query.all()
            count = len(expenses)
            for e in expenses:
                db.session.delete(e)
            db.session.commit()
            return jsonify({
                'message': f'Deleted {count} expense(s) in the selected date range',
                'expenses_deleted': count,
                'budgets_deleted': 0,
            })

        elif mode == 'single_date':
            single = data.get('single_date')
            if not single:
                return jsonify({'error': 'single_date is required'}), 400
            expenses = Expense.query.filter(Expense.date == date.fromisoformat(single)).all()
            count = len(expenses)
            for e in expenses:
                db.session.delete(e)
            db.session.commit()
            return jsonify({
                'message': f'Deleted {count} expense(s) on {single}',
                'expenses_deleted': count,
                'budgets_deleted': 0,
            })

        elif mode == 'category':
            cats = data.get('categories', [])
            if not cats:
                return jsonify({'error': 'No categories specified'}), 400
            expenses = Expense.query.filter(Expense.category.in_(cats)).all()
            count = len(expenses)
            for e in expenses:
                db.session.delete(e)
            db.session.commit()
            return jsonify({
                'message': f'Deleted {count} expense(s) from {len(cats)} categor{"y" if len(cats)==1 else "ies"}',
                'expenses_deleted': count,
                'budgets_deleted': 0,
            })

        else:
            return jsonify({'error': f'Unknown mode: {mode}'}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@expenses_bp.route('/upload', methods=['POST'])
def upload_csv():
    """
    Accept a CSV file and bulk-import expenses.

    Required columns : date, description, amount, category
    Optional columns : notes, is_recurring, currency

    Expected date format: YYYY-MM-DD
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded. Send the file as multipart/form-data with key "file".'}), 400

    file = request.files['file']
    if not file.filename or not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'Only CSV files are accepted (.csv extension required).'}), 400

    REQUIRED_COLS = {'date', 'description', 'amount', 'category'}

    try:
        stream  = io.StringIO(file.stream.read().decode('utf-8-sig'))
        df      = pd.read_csv(stream)

        # Normalise column names
        df.columns = [c.strip().lower() for c in df.columns]

        missing = REQUIRED_COLS - set(df.columns)
        if missing:
            return jsonify({
                'error': f'Missing required columns: {", ".join(sorted(missing))}',
                'required_columns': list(REQUIRED_COLS),
                'optional_columns': ['notes', 'is_recurring', 'currency'],
                'example_row': {
                    'date': '2024-01-15',
                    'description': 'Coffee at Starbucks',
                    'amount': '4.50',
                    'category': 'Food & Dining',
                    'notes': 'morning coffee',
                    'is_recurring': 'false',
                    'currency': 'USD',
                },
            }), 422

        # Fill optional columns with defaults
        if 'notes'        not in df.columns: df['notes']        = ''
        if 'is_recurring' not in df.columns: df['is_recurring'] = False
        if 'currency'     not in df.columns: df['currency']     = 'USD'

        imported   = 0
        skipped    = 0
        errors     = []

        for idx, row in df.iterrows():
            try:
                row_date = pd.to_datetime(str(row['date']).strip()).date()
                expense_data = {
                    'amount':       float(str(row['amount']).replace(',', '')),
                    'description':  str(row['description']).strip(),
                    'category':     str(row['category']).strip(),
                    'date':         row_date.isoformat(),
                    'notes':        str(row.get('notes', '') or '').strip(),
                    'is_recurring': str(row.get('is_recurring', 'false')).lower() in ('true', '1', 'yes'),
                    'currency':     str(row.get('currency', 'USD')).strip().upper() or 'USD',
                }
                if not expense_data['description'] or expense_data['amount'] <= 0:
                    skipped += 1
                    errors.append(f'Row {idx + 2}: skipped (empty description or non-positive amount)')
                    continue
                ExpenseService.create(expense_data)
                imported += 1
            except Exception as row_err:
                skipped += 1
                errors.append(f'Row {idx + 2}: {str(row_err)}')

        return jsonify({
            'message':  f'Import complete: {imported} imported, {skipped} skipped.',
            'imported': imported,
            'skipped':  skipped,
            'errors':   errors[:10],  # cap at 10 errors
        }), 201

    except Exception as e:
        return jsonify({'error': f'Failed to parse CSV: {str(e)}'}), 500
