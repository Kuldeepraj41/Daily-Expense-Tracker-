import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-expense-tracker-2025')
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    os.makedirs(DATA_DIR, exist_ok=True)
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(DATA_DIR, 'expenses.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = True
