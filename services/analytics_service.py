import pandas as pd
import numpy as np
from database.models import Expense, Budget
from datetime import date, timedelta
from collections import defaultdict


class AnalyticsService:

    @staticmethod
    def _get_dataframe():
        expenses = Expense.query.all()
        if not expenses:
            return pd.DataFrame(columns=['id', 'amount', 'description', 'category', 'date', 'currency'])
        data = [e.to_dict() for e in expenses]
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df['amount'] = pd.to_numeric(df['amount'])
        return df

    @staticmethod
    def get_summary():
        df = AnalyticsService._get_dataframe()
        if df.empty:
            return {
                'total_expenses': 0, 'total_amount': 0, 'avg_per_day': 0,
                'avg_per_expense': 0, 'this_month': 0, 'last_month': 0,
                'this_week': 0, 'top_category': None, 'expense_count': 0,
                'month_change_pct': 0,
            }

        today = pd.Timestamp.today()
        this_month_start = today.replace(day=1)
        last_month_start = (this_month_start - pd.DateOffset(months=1))
        last_month_end = this_month_start - pd.Timedelta(days=1)
        week_start = today - pd.Timedelta(days=7)

        this_month_df = df[df['date'] >= this_month_start]
        last_month_df = df[(df['date'] >= last_month_start) & (df['date'] <= last_month_end)]
        this_week_df = df[df['date'] >= week_start]

        top_cat = df.groupby('category')['amount'].sum().idxmax() if len(df) > 0 else None
        total = float(df['amount'].sum())
        date_range = max((df['date'].max() - df['date'].min()).days + 1, 1)
        avg_per_day = total / date_range

        this_month_total = float(this_month_df['amount'].sum())
        last_month_total = float(last_month_df['amount'].sum())
        month_change_pct = 0
        if last_month_total > 0:
            month_change_pct = ((this_month_total - last_month_total) / last_month_total) * 100

        return {
            'total_expenses': len(df),
            'total_amount': round(total, 2),
            'avg_per_day': round(avg_per_day, 2),
            'avg_per_expense': round(float(df['amount'].mean()), 2),
            'this_month': round(this_month_total, 2),
            'last_month': round(last_month_total, 2),
            'this_week': round(float(this_week_df['amount'].sum()), 2),
            'top_category': top_cat,
            'expense_count': len(df),
            'month_change_pct': round(month_change_pct, 1),
        }

    @staticmethod
    def by_category():
        df = AnalyticsService._get_dataframe()
        if df.empty:
            return []
        cat_groups = df.groupby('category').agg(
            total=('amount', 'sum'),
            count=('amount', 'count'),
            avg=('amount', 'mean'),
        ).reset_index()
        total_all = cat_groups['total'].sum()
        cat_groups['percentage'] = (cat_groups['total'] / total_all * 100).round(1)
        cat_groups['total'] = cat_groups['total'].round(2)
        cat_groups['avg'] = cat_groups['avg'].round(2)
        return cat_groups.sort_values('total', ascending=False).to_dict(orient='records')

    @staticmethod
    def by_date(period='daily', days=30):
        df = AnalyticsService._get_dataframe()
        if df.empty:
            return []
        cutoff = pd.Timestamp.today() - pd.Timedelta(days=days)
        df = df[df['date'] >= cutoff]
        if df.empty:
            return []

        if period == 'daily':
            df['period'] = df['date'].dt.date
        elif period == 'weekly':
            df['period'] = df['date'].dt.to_period('W').apply(lambda r: str(r.start_time.date()))
        elif period == 'monthly':
            df['period'] = df['date'].dt.to_period('M').apply(lambda r: str(r.start_time.date()))

        grouped = df.groupby('period')['amount'].sum().reset_index()
        grouped.columns = ['date', 'total']
        grouped['total'] = grouped['total'].round(2)
        return grouped.sort_values('date').to_dict(orient='records')

    @staticmethod
    def monthly_breakdown():
        df = AnalyticsService._get_dataframe()
        if df.empty:
            return []
        df['month'] = df['date'].dt.to_period('M')
        grouped = df.groupby(['month', 'category'])['amount'].sum().reset_index()
        grouped['month'] = grouped['month'].astype(str)
        grouped['amount'] = grouped['amount'].round(2)
        return grouped.sort_values('month').to_dict(orient='records')

    @staticmethod
    def budget_vs_actual():
        df = AnalyticsService._get_dataframe()
        budgets = Budget.query.all()
        if not budgets:
            return []

        today = pd.Timestamp.today()
        this_month_start = today.replace(day=1)
        this_month_df = df[df['date'] >= this_month_start] if not df.empty else df

        results = []
        for b in budgets:
            cat_spent = 0.0
            if not this_month_df.empty:
                cat_df = this_month_df[this_month_df['category'] == b.category]
                cat_spent = float(cat_df['amount'].sum())
            pct_used = (cat_spent / b.limit_amount * 100) if b.limit_amount > 0 else 0
            results.append({
                'category': b.category,
                'budget': b.limit_amount,
                'spent': round(cat_spent, 2),
                'remaining': round(max(b.limit_amount - cat_spent, 0), 2),
                'pct_used': round(pct_used, 1),
                'over_budget': cat_spent > b.limit_amount,
                'budget_id': b.id,
            })
        return sorted(results, key=lambda x: x['pct_used'], reverse=True)

    @staticmethod
    def recent_expenses(limit=10):
        expenses = Expense.query.order_by(Expense.date.desc(), Expense.created_at.desc()).limit(limit).all()
        return [e.to_dict() for e in expenses]
