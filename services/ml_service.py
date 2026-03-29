import pandas as pd
import numpy as np
from datetime import date, timedelta
from database.models import Expense

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.pipeline import Pipeline
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import LabelEncoder
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class MLService:

    # ── Auto-Categorisation ──────────────────────────────────────────────────

    @staticmethod
    def suggest_category(description: str):
        """Train a TF-IDF + Naive Bayes classifier on existing expenses and predict category."""
        expenses = Expense.query.all()
        if not HAS_SKLEARN or len(expenses) < 5:
            return MLService._rule_based_category(description)

        texts = [e.description for e in expenses]
        labels = [e.category for e in expenses]

        unique_labels = list(set(labels))
        if len(unique_labels) < 2:
            return {'category': labels[0], 'confidence': 0.95, 'method': 'single_class'}

        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4), max_features=3000)),
            ('clf', MultinomialNB(alpha=0.5)),
        ])
        pipeline.fit(texts, labels)

        proba = pipeline.predict_proba([description])[0]
        classes = pipeline.classes_
        top_idx = np.argsort(proba)[::-1][:3]

        suggestions = [
            {'category': classes[i], 'confidence': round(float(proba[i]), 3)}
            for i in top_idx if proba[i] > 0.01
        ]
        return {
            'top_category': suggestions[0]['category'] if suggestions else 'Other',
            'confidence': suggestions[0]['confidence'] if suggestions else 0,
            'suggestions': suggestions,
            'method': 'ml_naive_bayes',
        }

    @staticmethod
    def _rule_based_category(description: str):
        desc = description.lower()
        rules = [
            ('Food & Dining',    ['food', 'restaurant', 'cafe', 'coffee', 'lunch', 'dinner', 'breakfast',
                                   'pizza', 'burger', 'sushi', 'grocery', 'groceries', 'supermarket',
                                   'starbucks', 'mcdonald', 'subway', 'eat', 'snack', 'meal']),
            ('Transportation',  ['uber', 'lyft', 'taxi', 'bus', 'metro', 'train', 'gas', 'petrol',
                                  'parking', 'transport', 'fuel', 'ride', 'fare']),
            ('Shopping',        ['amazon', 'shop', 'store', 'clothes', 'shirt', 'shoes', 'online',
                                  'purchase', 'buy', 'mall', 'market', 'h&m', 'zara', 'ebay']),
            ('Entertainment',   ['netflix', 'spotify', 'movie', 'cinema', 'concert', 'game', 'gaming',
                                  'stream', 'show', 'ticket', 'music', 'hulu', 'disney']),
            ('Health & Fitness',['gym', 'fitness', 'doctor', 'hospital', 'pharmacy', 'medicine',
                                  'health', 'yoga', 'vitamin', 'dental', 'clinic', 'workout']),
            ('Utilities',       ['electricity', 'electric', 'water', 'internet', 'wifi', 'phone',
                                  'bill', 'utility', 'gas bill', 'mobile', 'broadband']),
            ('Housing',         ['rent', 'mortgage', 'insurance', 'repair', 'maintenance', 'home',
                                  'house', 'apartment', 'lease', 'landlord']),
            ('Education',       ['course', 'book', 'school', 'university', 'college', 'tuition',
                                  'udemy', 'coursera', 'class', 'lesson', 'study', 'tutorial']),
            ('Travel',          ['hotel', 'flight', 'airbnb', 'holiday', 'vacation', 'travel',
                                  'trip', 'airfare', 'airline', 'booking', 'tour']),
        ]
        for category, keywords in rules:
            if any(kw in desc for kw in keywords):
                return {'top_category': category, 'confidence': 0.75, 'suggestions': [{'category': category, 'confidence': 0.75}], 'method': 'rule_based'}
        return {'top_category': 'Other', 'confidence': 0.5, 'suggestions': [{'category': 'Other', 'confidence': 0.5}], 'method': 'rule_based'}

    # ── Spending Forecast ────────────────────────────────────────────────────

    @staticmethod
    def forecast_spending(days_ahead=30):
        """Linear regression on past daily totals → predict next N days."""
        expenses = Expense.query.all()
        if not expenses:
            return {'forecast': [], 'method': 'no_data'}

        df = pd.DataFrame([e.to_dict() for e in expenses])
        df['date'] = pd.to_datetime(df['date'])
        df['amount'] = pd.to_numeric(df['amount'])

        daily = df.groupby('date')['amount'].sum().reset_index()
        daily = daily.sort_values('date')

        if len(daily) < 3:
            avg = float(daily['amount'].mean())
            today = date.today()
            forecast = [{'date': str(today + timedelta(days=i)), 'predicted': round(avg, 2)} for i in range(1, days_ahead + 1)]
            return {'forecast': forecast, 'method': 'average', 'avg_daily': round(avg, 2)}

        # Build a simple time-index regression
        min_date = daily['date'].min()
        daily['day_num'] = (daily['date'] - min_date).dt.days

        X = daily[['day_num']].values
        y = daily['amount'].values

        if HAS_SKLEARN and len(daily) >= 5:
            model = LinearRegression()
            model.fit(X, y)
            max_day = int(daily['day_num'].max())
            today_num = int((pd.Timestamp.today() - min_date).days)
            forecast = []
            for i in range(1, days_ahead + 1):
                pred = float(model.predict([[today_num + i]])[0])
                pred = max(pred, 0)
                forecast.append({
                    'date': str(date.today() + timedelta(days=i)),
                    'predicted': round(pred, 2),
                })
            avg_daily = round(float(np.mean(y)), 2)
            return {'forecast': forecast, 'method': 'linear_regression', 'avg_daily': avg_daily}
        else:
            avg = float(np.mean(y))
            forecast = [{'date': str(date.today() + timedelta(days=i)), 'predicted': round(avg, 2)} for i in range(1, days_ahead + 1)]
            return {'forecast': forecast, 'method': 'average', 'avg_daily': round(avg, 2)}

    # ── Anomaly Detection ────────────────────────────────────────────────────

    @staticmethod
    def detect_anomalies():
        """IsolationForest on expense amounts — flags statistical outliers."""
        expenses = Expense.query.order_by(Expense.date.desc()).limit(200).all()
        if len(expenses) < 10:
            return {'anomalies': [], 'method': 'insufficient_data', 'threshold': None}

        data = [{'id': e.id, 'amount': e.amount, 'description': e.description,
                  'category': e.category, 'date': e.date.isoformat()} for e in expenses]
        amounts = np.array([[d['amount']] for d in data])

        if HAS_SKLEARN:
            clf = IsolationForest(contamination=0.1, random_state=42)
            preds = clf.fit_predict(amounts)
            anomalies = [data[i] for i, p in enumerate(preds) if p == -1]
        else:
            mean_a = float(np.mean(amounts))
            std_a = float(np.std(amounts))
            threshold = mean_a + 2 * std_a
            anomalies = [d for d in data if d['amount'] > threshold]

        return {
            'anomalies': anomalies,
            'total_checked': len(data),
            'anomaly_count': len(anomalies),
            'method': 'isolation_forest' if HAS_SKLEARN else 'z_score',
        }

    # ── Budget Burn Rate ─────────────────────────────────────────────────────

    @staticmethod
    def budget_burn_rate():
        """Estimate budget exhaustion based on current spending velocity."""
        from database.models import Budget as BudgetModel
        budgets = BudgetModel.query.all()
        if not budgets:
            return []

        expenses = Expense.query.all()
        if not expenses:
            return []

        df = pd.DataFrame([e.to_dict() for e in expenses])
        df['date'] = pd.to_datetime(df['date'])
        df['amount'] = pd.to_numeric(df['amount'])

        today = pd.Timestamp.today()
        month_start = today.replace(day=1)
        days_elapsed = max((today - month_start).days + 1, 1)
        days_in_month = 30

        results = []
        for b in budgets:
            cat_df = df[(df['category'] == b.category) & (df['date'] >= month_start)]
            spent = float(cat_df['amount'].sum()) if not cat_df.empty else 0.0
            daily_rate = spent / days_elapsed
            days_to_exhaust = (b.limit_amount / daily_rate) if daily_rate > 0 else float('inf')
            projected_month_total = daily_rate * days_in_month

            results.append({
                'category': b.category,
                'budget': b.limit_amount,
                'spent_so_far': round(spent, 2),
                'daily_rate': round(daily_rate, 2),
                'days_to_exhaust': round(days_to_exhaust, 1) if days_to_exhaust != float('inf') else None,
                'projected_month_total': round(projected_month_total, 2),
                'will_exceed': projected_month_total > b.limit_amount,
                'pct_elapsed': round(days_elapsed / days_in_month * 100, 1),
                'pct_spent': round(spent / b.limit_amount * 100, 1) if b.limit_amount > 0 else 0,
            })
        return results

    # ── Spending Insights ────────────────────────────────────────────────────

    @staticmethod
    def generate_insights():
        """Rule-based insights derived from spending patterns."""
        expenses = Expense.query.all()
        if not expenses:
            return []

        df = pd.DataFrame([e.to_dict() for e in expenses])
        df['date'] = pd.to_datetime(df['date'])
        df['amount'] = pd.to_numeric(df['amount'])

        insights = []
        today = pd.Timestamp.today()

        # Top spending category
        if len(df) > 0:
            cat_totals = df.groupby('category')['amount'].sum()
            top_cat = cat_totals.idxmax()
            top_pct = round((cat_totals[top_cat] / cat_totals.sum()) * 100, 1)
            insights.append({
                'type': 'info',
                'title': 'Top Spending Category',
                'message': f'{top_cat} accounts for {top_pct}% of your total spending (${cat_totals[top_cat]:.2f}).',
                'icon': '📊',
            })

        # Month-over-month comparison
        this_month_df = df[df['date'] >= today.replace(day=1)]
        last_month_start = (today.replace(day=1) - pd.DateOffset(months=1))
        last_month_end = today.replace(day=1) - pd.Timedelta(days=1)
        last_month_df = df[(df['date'] >= last_month_start) & (df['date'] <= last_month_end)]

        if not last_month_df.empty and not this_month_df.empty:
            this_total = this_month_df['amount'].sum()
            last_total = last_month_df['amount'].sum()
            change_pct = ((this_total - last_total) / last_total) * 100
            direction = 'up' if change_pct > 0 else 'down'
            icon = '📈' if change_pct > 0 else '📉'
            type_ = 'warning' if change_pct > 10 else 'success'
            insights.append({
                'type': type_,
                'title': 'Month-over-Month Trend',
                'message': f'Your spending is {direction} {abs(change_pct):.1f}% compared to last month.',
                'icon': icon,
            })

        # High single expense
        if len(df) > 5:
            mean_a = df['amount'].mean()
            std_a = df['amount'].std()
            high_threshold = mean_a + 2 * std_a
            high_expenses = df[df['amount'] > high_threshold]
            if not high_expenses.empty:
                biggest = high_expenses.nlargest(1, 'amount').iloc[0]
                insights.append({
                    'type': 'warning',
                    'title': 'Unusually Large Expense',
                    'message': f'"{biggest["description"]}" (${biggest["amount"]:.2f}) was significantly above your average spend of ${mean_a:.2f}.',
                    'icon': '⚠️',
                })

        # Daily average
        if len(df) > 0:
            date_range = max((df['date'].max() - df['date'].min()).days + 1, 1)
            avg_daily = df['amount'].sum() / date_range
            insights.append({
                'type': 'info',
                'title': 'Daily Average',
                'message': f'You spend an average of ${avg_daily:.2f} per day. That\'s ${avg_daily * 30:.2f} projected for 30 days.',
                'icon': '💡',
            })

        return insights
