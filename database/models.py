from .db import db
from datetime import datetime, date


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    color = db.Column(db.String(7), default='#6366f1')
    icon = db.Column(db.String(10), default='💰')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'icon': self.icon,
        }


class Expense(db.Model):
    __tablename__ = 'expenses'

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    notes = db.Column(db.Text, default='')
    is_recurring = db.Column(db.Boolean, default=False)
    currency = db.Column(db.String(3), default='USD')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'amount': self.amount,
            'description': self.description,
            'category': self.category,
            'date': self.date.isoformat(),
            'notes': self.notes or '',
            'is_recurring': self.is_recurring,
            'currency': self.currency,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Budget(db.Model):
    __tablename__ = 'budgets'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    limit_amount = db.Column(db.Float, nullable=False)
    period = db.Column(db.String(20), default='monthly')
    month = db.Column(db.Integer)
    year = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'limit_amount': self.limit_amount,
            'period': self.period,
            'month': self.month,
            'year': self.year,
        }
