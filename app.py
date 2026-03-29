from flask import Flask, render_template, jsonify
from flask_cors import CORS
from config import Config
from database.db import init_db
from routes.expenses import expenses_bp
from routes.analytics import analytics_bp
from routes.ml import ml_bp
from routes.rag import rag_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(app)
    init_db(app)

    app.register_blueprint(expenses_bp,  url_prefix='/api/expenses')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    app.register_blueprint(ml_bp,        url_prefix='/api/ml')
    app.register_blueprint(rag_bp,       url_prefix='/api/rag')

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({'error': 'Internal server error', 'detail': str(e)}), 500

    return app


if __name__ == '__main__':
    app = create_app()
    print("\n🚀  Daily Expense Tracker is running!")
    print("📊  Open your browser at: http://localhost:5000\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
