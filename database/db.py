from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import random

db = SQLAlchemy()


def init_db(app):
    db.init_app(app)
    with app.app_context():
        from .models import Expense, Budget, Category
        db.create_all()
        _seed_categories()


def _seed_categories():
    from .models import Category
    if Category.query.count() == 0:
        defaults = [
            Category(name='Food & Dining',    color='#f59e0b', icon='🍽️'),
            Category(name='Transportation',   color='#3b82f6', icon='🚗'),
            Category(name='Shopping',         color='#8b5cf6', icon='🛍️'),
            Category(name='Entertainment',    color='#ec4899', icon='🎬'),
            Category(name='Health & Fitness', color='#10b981', icon='💪'),
            Category(name='Utilities',        color='#6366f1', icon='⚡'),
            Category(name='Housing',          color='#ef4444', icon='🏠'),
            Category(name='Education',        color='#14b8a6', icon='📚'),
            Category(name='Travel',           color='#f97316', icon='✈️'),
            Category(name='Other',            color='#6b7280', icon='📦'),
        ]
        db.session.add_all(defaults)
        db.session.commit()


def seed_sample_expenses():
    from .models import Expense
    if Expense.query.count() > 0:
        return {'message': 'Sample data already exists', 'count': 0}

    from datetime import timedelta
    sample_data = [
        # Food & Dining
        ('Food & Dining',    'Starbucks coffee',         4.50,  -1),
        ('Food & Dining',    'Lunch at Subway',          9.75,  -2),
        ('Food & Dining',    'Grocery shopping',         62.30, -3),
        ('Food & Dining',    'Pizza delivery',           18.90, -5),
        ('Food & Dining',    'McDonald\'s breakfast',    7.20,  -6),
        ('Food & Dining',    'Dinner at restaurant',     45.00, -9),
        ('Food & Dining',    'Starbucks latte',          5.10,  -10),
        ('Food & Dining',    'Grocery weekly',           78.40, -11),
        ('Food & Dining',    'Sushi takeout',            32.00, -14),
        ('Food & Dining',    'Coffee shop',              3.80,  -15),
        ('Food & Dining',    'Grocery monthly stock',    110.50,-18),
        ('Food & Dining',    'Birthday dinner',          89.00, -20),
        # Transportation
        ('Transportation',  'Uber ride to office',       12.50, -1),
        ('Transportation',  'Gas station fill-up',       48.20, -4),
        ('Transportation',  'Metro monthly pass',        85.00, -7),
        ('Transportation',  'Uber to airport',           32.00, -12),
        ('Transportation',  'Gas refill',                50.10, -19),
        ('Transportation',  'Parking fee',               15.00, -22),
        # Shopping
        ('Shopping',        'Amazon order - headphones', 89.99, -2),
        ('Shopping',        'Clothes at H&M',            65.00, -8),
        ('Shopping',        'Online shopping misc',      34.50, -13),
        ('Shopping',        'Shoes purchase',            120.00,-21),
        ('Shopping',        'Home decor items',          55.00, -25),
        # Entertainment
        ('Entertainment',   'Netflix subscription',      15.99, -1),
        ('Entertainment',   'Movie tickets',             24.00, -5),
        ('Entertainment',   'Spotify premium',           9.99,  -1),
        ('Entertainment',   'Concert tickets',           75.00, -16),
        ('Entertainment',   'Gaming purchase',           59.99, -23),
        # Health & Fitness
        ('Health & Fitness','Gym membership',            49.99, -1),
        ('Health & Fitness','Pharmacy - vitamins',       22.50, -7),
        ('Health & Fitness','Doctor visit copay',        30.00, -15),
        ('Health & Fitness','Yoga class',                18.00, -10),
        # Utilities
        ('Utilities',       'Electricity bill',          95.40, -3),
        ('Utilities',       'Internet bill',             59.99, -3),
        ('Utilities',       'Water bill',                32.00, -8),
        ('Utilities',       'Phone bill',                75.00, -5),
        # Housing
        ('Housing',         'Rent payment',              1200.00,-1),
        ('Housing',         'Home insurance',            85.00, -2),
        # Education
        ('Education',       'Online course - Udemy',     19.99, -6),
        ('Education',       'Python book',               35.00, -11),
        # Travel
        ('Travel',          'Weekend hotel stay',        145.00,-17),
        ('Travel',          'Flight tickets',            320.00,-24),
    ]

    today = date.today()
    expenses = []
    for category, description, amount, day_offset in sample_data:
        expense_date = today + timedelta(days=day_offset)
        expenses.append(Expense(
            amount=amount,
            description=description,
            category=category,
            date=expense_date,
            notes='',
            is_recurring=False,
            currency='USD'
        ))

    db.session.add_all(expenses)
    db.session.commit()
    return {'message': 'Sample data seeded successfully', 'count': len(expenses)}
