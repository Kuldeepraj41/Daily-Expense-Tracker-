from database.db import db
from database.models import Expense, Category, Budget
from datetime import date, datetime


class ExpenseService:

    @staticmethod
    def get_all(category=None, start_date=None, end_date=None, search=None, sort_by='date', order='desc'):
        query = Expense.query

        if category and category != 'all':
            query = query.filter(Expense.category == category)
        if start_date:
            query = query.filter(Expense.date >= start_date)
        if end_date:
            query = query.filter(Expense.date <= end_date)
        if search:
            query = query.filter(Expense.description.ilike(f'%{search}%'))

        sort_col = getattr(Expense, sort_by, Expense.date)
        if order == 'desc':
            query = query.order_by(sort_col.desc())
        else:
            query = query.order_by(sort_col.asc())

        return [e.to_dict() for e in query.all()]

    @staticmethod
    def get_by_id(expense_id):
        expense = Expense.query.get_or_404(expense_id)
        return expense.to_dict()

    @staticmethod
    def create(data):
        expense = Expense(
            amount=float(data['amount']),
            description=data['description'].strip(),
            category=data['category'],
            date=date.fromisoformat(data['date']) if isinstance(data['date'], str) else data['date'],
            notes=data.get('notes', ''),
            is_recurring=data.get('is_recurring', False),
            currency=data.get('currency', 'USD'),
        )
        db.session.add(expense)
        db.session.commit()
        return expense.to_dict()

    @staticmethod
    def update(expense_id, data):
        expense = Expense.query.get_or_404(expense_id)
        if 'amount' in data:
            expense.amount = float(data['amount'])
        if 'description' in data:
            expense.description = data['description'].strip()
        if 'category' in data:
            expense.category = data['category']
        if 'date' in data:
            expense.date = date.fromisoformat(data['date']) if isinstance(data['date'], str) else data['date']
        if 'notes' in data:
            expense.notes = data['notes']
        if 'is_recurring' in data:
            expense.is_recurring = data['is_recurring']
        if 'currency' in data:
            expense.currency = data['currency']
        expense.updated_at = datetime.utcnow()
        db.session.commit()
        return expense.to_dict()

    @staticmethod
    def delete(expense_id):
        expense = Expense.query.get_or_404(expense_id)
        db.session.delete(expense)
        db.session.commit()
        return {'message': 'Expense deleted successfully'}

    @staticmethod
    def get_categories():
        return [c.to_dict() for c in Category.query.order_by(Category.name).all()]

    @staticmethod
    def create_category(data):
        cat = Category(
            name=data['name'],
            color=data.get('color', '#6366f1'),
            icon=data.get('icon', '💰'),
        )
        db.session.add(cat)
        db.session.commit()
        return cat.to_dict()

    @staticmethod
    def get_budgets():
        return [b.to_dict() for b in Budget.query.all()]

    @staticmethod
    def set_budget(data):
        existing = Budget.query.filter_by(
            category=data['category'],
            period=data.get('period', 'monthly')
        ).first()
        if existing:
            existing.limit_amount = float(data['limit_amount'])
            db.session.commit()
            return existing.to_dict()
        budget = Budget(
            category=data['category'],
            limit_amount=float(data['limit_amount']),
            period=data.get('period', 'monthly'),
            month=data.get('month'),
            year=data.get('year'),
        )
        db.session.add(budget)
        db.session.commit()
        return budget.to_dict()

    @staticmethod
    def delete_budget(budget_id):
        budget = Budget.query.get_or_404(budget_id)
        db.session.delete(budget)
        db.session.commit()
        return {'message': 'Budget deleted successfully'}
