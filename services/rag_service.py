"""
RAG (Retrieval-Augmented Generation) Service
=============================================
Pipeline:
  1. BUILD  — Convert expense records + financial KB → text documents
  2. INDEX  — TF-IDF vectorize all documents
  3. RETRIEVE — Cosine similarity search for top-K relevant documents
  4. GENERATE — Intent detection + template NLG using retrieved context
"""

import re
import math
import pandas as pd
import numpy as np
from datetime import date, timedelta
from collections import Counter

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


# ── Pre-loaded Financial Knowledge Base ──────────────────────────────────────

FINANCIAL_KB = [
    {
        'id': 'kb_001', 'type': 'rule',
        'text': 'The 50/30/20 budget rule recommends allocating 50% of after-tax income to needs like rent groceries and utilities, 30% to wants like entertainment dining out and shopping, and 20% to savings and debt repayment.',
    },
    {
        'id': 'kb_002', 'type': 'tip',
        'text': 'Small daily expenses like coffee snacks and impulse purchases accumulate significantly. A daily coffee habit at five dollars a day costs over 180 dollars a month.',
    },
    {
        'id': 'kb_003', 'type': 'tip',
        'text': 'Creating an emergency fund covering three to six months of expenses is a critical financial safety net before investing.',
    },
    {
        'id': 'kb_004', 'type': 'tip',
        'text': 'Tracking every expense helps identify spending leaks. Use budget categories to monitor where money goes each month.',
    },
    {
        'id': 'kb_005', 'type': 'strategy',
        'text': 'To reduce food dining expenses, meal prepping on weekends significantly cuts daily lunch costs. Cooking at home instead of eating out saves roughly 200 to 400 dollars per month.',
    },
    {
        'id': 'kb_006', 'type': 'strategy',
        'text': 'Subscription audit: Review monthly subscriptions like streaming services gym memberships and apps every quarter. Cancel unused subscriptions to save 50 to 150 dollars monthly.',
    },
    {
        'id': 'kb_007', 'type': 'strategy',
        'text': 'Transportation savings: Carpooling using public transit and combining trips reduces transportation costs by 20 to 40 percent. Consider the total cost of car ownership including insurance gas maintenance and depreciation.',
    },
    {
        'id': 'kb_008', 'type': 'rule',
        'text': 'The envelope method involves dividing cash into labeled envelopes for each spending category. When an envelope is empty spending for that category stops, enforcing strict budget discipline.',
    },
    {
        'id': 'kb_009', 'type': 'tip',
        'text': 'Impulse purchases can be controlled with a 24-hour waiting rule. Delaying non-essential purchases by one day often reduces impulse buys by 50 percent.',
    },
    {
        'id': 'kb_010', 'type': 'strategy',
        'text': 'Pay yourself first by automating savings transfers immediately after receiving income. Treating savings as a non-negotiable expense ensures consistent wealth building.',
    },
    {
        'id': 'kb_011', 'type': 'rule',
        'text': 'Zero-based budgeting assigns every dollar a specific purpose income minus expenses equals zero. This forces intentional spending and reveals exactly where money is going.',
    },
    {
        'id': 'kb_012', 'type': 'tip',
        'text': 'Shopping and entertainment overspending can be reduced by setting weekly spending caps using cash for discretionary categories and unsubscribing from promotional emails.',
    },
    {
        'id': 'kb_013', 'type': 'tip',
        'text': 'Housing should ideally cost no more than 30 percent of gross income. Higher housing costs leave less for savings and other expenses.',
    },
    {
        'id': 'kb_014', 'type': 'strategy',
        'text': 'Utility bills can be reduced by switching to LED lightbulbs using smart thermostats unplugging idle electronics and comparing internet and phone plan prices annually.',
    },
    {
        'id': 'kb_015', 'type': 'tip',
        'text': 'Seasonal sales and bulk buying for non-perishable items reduces shopping costs. Compare unit prices rather than package prices to find the best value.',
    },
]


class RAGService:

    def __init__(self):
        self.documents = []
        self.doc_vectors = None
        self.vectorizer = None
        self.is_indexed = False
        self._expense_stats = {}

    # ── 1. BUILD ─────────────────────────────────────────────────────────────

    def build_knowledge_base(self, expenses, budgets):
        """Convert all data into text documents for retrieval."""
        self.documents = []

        # A. Financial knowledge base
        for kb in FINANCIAL_KB:
            self.documents.append({'id': kb['id'], 'type': 'knowledge', 'text': kb['text'], 'data': kb})

        # B. Individual expense documents
        for exp in expenses:
            text = (
                f"On {exp['date']} you spent {exp['amount']} dollars on {exp['category']} "
                f"for {exp['description']}. "
                f"Category {exp['category']} amount {exp['amount']}."
            )
            self.documents.append({'id': f"exp_{exp['id']}", 'type': 'expense', 'text': text, 'data': exp})

        # C. Summary documents derived from analytics
        self.documents.extend(self._generate_expense_summaries(expenses))
        self.documents.extend(self._generate_budget_docs(budgets, expenses))

        # D. Pre-compute stats for generation
        self._expense_stats = self._compute_stats(expenses, budgets)

        # ── 2. INDEX ────────────────────────────────────────────────────────
        self._build_index()

    def _generate_expense_summaries(self, expenses):
        docs = []
        if not expenses:
            return docs

        df = pd.DataFrame(expenses)
        df['date'] = pd.to_datetime(df['date'])
        df['amount'] = pd.to_numeric(df['amount'])

        # Monthly summaries
        for (year, month), grp in df.groupby([df['date'].dt.year, df['date'].dt.month]):
            total = grp['amount'].sum()
            top_cat = grp.groupby('category')['amount'].sum().idxmax()
            count = len(grp)
            month_name = pd.Timestamp(year=int(year), month=int(month), day=1).strftime('%B %Y')
            text = (
                f"In {month_name} total spending was {total:.2f} dollars across {count} transactions. "
                f"The highest spending category was {top_cat} with {grp.groupby('category')['amount'].sum()[top_cat]:.2f} dollars. "
                f"Monthly total {month_name} {total:.2f}."
            )
            docs.append({'id': f"summary_{year}_{month}", 'type': 'monthly_summary',
                          'text': text, 'data': {'year': year, 'month': month, 'total': total, 'top_cat': top_cat}})

        # Category summaries
        total_all = float(df['amount'].sum())
        for cat, grp in df.groupby('category'):
            cat_total = float(grp['amount'].sum())
            pct = (cat_total / total_all * 100) if total_all > 0 else 0
            avg = float(grp['amount'].mean())
            text = (
                f"You spent {cat_total:.2f} dollars on {cat} which is {pct:.1f} percent of total spending. "
                f"Average {cat} expense is {avg:.2f} dollars. "
                f"Category {cat} spending total {cat_total:.2f} average {avg:.2f}."
            )
            docs.append({'id': f"cat_{cat.replace(' ', '_')}", 'type': 'category_summary',
                          'text': text, 'data': {'category': cat, 'total': cat_total, 'pct': pct, 'avg': avg}})

        # Weekly trend
        today = pd.Timestamp.today()
        this_week = df[df['date'] >= today - pd.Timedelta(days=7)]
        last_week = df[(df['date'] >= today - pd.Timedelta(days=14)) & (df['date'] < today - pd.Timedelta(days=7))]
        if not this_week.empty:
            tw = float(this_week['amount'].sum())
            lw = float(last_week['amount'].sum()) if not last_week.empty else 0
            change = 'increased' if tw > lw else 'decreased'
            text = (
                f"This week spending was {tw:.2f} dollars. "
                f"Compared to last week {lw:.2f} dollars spending {change}. "
                f"Weekly comparison this week {tw:.2f} last week {lw:.2f}."
            )
            docs.append({'id': 'weekly_trend', 'type': 'trend', 'text': text,
                          'data': {'this_week': tw, 'last_week': lw}})

        return docs

    def _generate_budget_docs(self, budgets, expenses):
        docs = []
        if not budgets:
            return docs

        df = pd.DataFrame(expenses) if expenses else pd.DataFrame()
        today = pd.Timestamp.today()
        month_start = today.replace(day=1)

        for b in budgets:
            spent = 0.0
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['amount'] = pd.to_numeric(df['amount'])
                cat_df = df[(df['category'] == b['category']) & (df['date'] >= month_start)]
                spent = float(cat_df['amount'].sum())
            remaining = b['limit_amount'] - spent
            pct = (spent / b['limit_amount'] * 100) if b['limit_amount'] > 0 else 0
            status = 'over budget' if spent > b['limit_amount'] else 'within budget'
            text = (
                f"Budget for {b['category']} is {b['limit_amount']:.2f} dollars this month. "
                f"You have spent {spent:.2f} dollars which is {pct:.1f} percent. "
                f"Remaining budget for {b['category']} is {remaining:.2f} dollars. "
                f"Budget status {b['category']} {status}."
            )
            docs.append({'id': f"budget_{b['category'].replace(' ', '_')}", 'type': 'budget',
                          'text': text, 'data': {**b, 'spent': spent, 'remaining': remaining, 'pct': pct}})
        return docs

    def _compute_stats(self, expenses, budgets):
        if not expenses:
            return {}
        df = pd.DataFrame(expenses)
        df['date'] = pd.to_datetime(df['date'])
        df['amount'] = pd.to_numeric(df['amount'])

        today = pd.Timestamp.today()
        month_start = today.replace(day=1)
        this_month_df = df[df['date'] >= month_start]

        cat_totals = df.groupby('category')['amount'].sum().sort_values(ascending=False)
        top_cat = cat_totals.index[0] if len(cat_totals) > 0 else 'N/A'

        date_range = max((df['date'].max() - df['date'].min()).days + 1, 1)
        avg_daily = float(df['amount'].sum()) / date_range

        stats = {
            'total_spending': round(float(df['amount'].sum()), 2),
            'this_month': round(float(this_month_df['amount'].sum()), 2),
            'avg_daily': round(avg_daily, 2),
            'avg_per_expense': round(float(df['amount'].mean()), 2),
            'top_category': top_cat,
            'top_category_amount': round(float(cat_totals.iloc[0]), 2) if len(cat_totals) > 0 else 0,
            'expense_count': len(df),
            'category_breakdown': {cat: round(float(amt), 2) for cat, amt in cat_totals.items()},
            'budgets': {b['category']: b['limit_amount'] for b in budgets} if budgets else {},
        }

        # Month-over-month
        last_month_start = month_start - pd.DateOffset(months=1)
        last_month_df = df[(df['date'] >= last_month_start) & (df['date'] < month_start)]
        stats['last_month'] = round(float(last_month_df['amount'].sum()), 2)

        return stats

    # ── 2. INDEX (TF-IDF) ────────────────────────────────────────────────────

    def _build_index(self):
        if not self.documents:
            self.is_indexed = False
            return
        texts = [d['text'] for d in self.documents]
        if HAS_SKLEARN:
            self.vectorizer = TfidfVectorizer(
                max_features=8000,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=1,
                sublinear_tf=True,
            )
            self.doc_vectors = self.vectorizer.fit_transform(texts)
        else:
            # Fallback: simple word-count bag-of-words
            self._fallback_index(texts)
        self.is_indexed = True

    def _fallback_index(self, texts):
        """Simple TF-IDF without sklearn."""
        vocab = {}
        tf_list = []
        for text in texts:
            tokens = re.findall(r'\b\w+\b', text.lower())
            tf = Counter(tokens)
            tf_list.append(tf)
            for tok in tf:
                vocab[tok] = vocab.get(tok, 0) + 1

        N = len(texts)
        idf = {tok: math.log(N / (1 + cnt)) for tok, cnt in vocab.items()}

        def make_vec(tf):
            vec = {}
            for tok, cnt in tf.items():
                if tok in idf:
                    vec[tok] = cnt * idf[tok]
            return vec

        self._fallback_vecs = [make_vec(tf) for tf in tf_list]
        self._idf = idf

    # ── 3. RETRIEVE ──────────────────────────────────────────────────────────

    def retrieve(self, query: str, k: int = 6):
        if not self.is_indexed or not self.documents:
            return []

        if HAS_SKLEARN and self.vectorizer is not None:
            q_vec = self.vectorizer.transform([query])
            sims = cosine_similarity(q_vec, self.doc_vectors).flatten()
        else:
            q_tokens = Counter(re.findall(r'\b\w+\b', query.lower()))
            q_vec = {tok: cnt * self._idf.get(tok, 0) for tok, cnt in q_tokens.items()}
            sims = []
            for dv in self._fallback_vecs:
                common = set(q_vec) & set(dv)
                num = sum(q_vec[t] * dv[t] for t in common)
                denom = (math.sqrt(sum(v ** 2 for v in q_vec.values())) *
                         math.sqrt(sum(v ** 2 for v in dv.values())))
                sims.append(num / denom if denom else 0.0)
            sims = np.array(sims)

        top_k = sims.argsort()[::-1][:k]
        return [
            {**self.documents[i], 'score': round(float(sims[i]), 4)}
            for i in top_k if sims[i] > 0.005
        ]

    # ── 4. GENERATE (Intent-Aware NLG) ───────────────────────────────────────

    INTENT_KEYWORDS = {
        'spending_query':      ['how much', 'total', 'spent', 'spend', 'cost', 'paid', 'expense', 'amount'],
        'trend_query':         ['trend', 'increase', 'decrease', 'growing', 'compare', 'change', 'more', 'less', 'week', 'month'],
        'budget_query':        ['budget', 'limit', 'over', 'remaining', 'left', 'allowance'],
        'recommendation_query':['advice', 'suggest', 'recommend', 'save', 'reduce', 'improve', 'tip', 'help', 'cut'],
        'category_query':      ['category', 'categories', 'breakdown', 'most', 'highest', 'lowest', 'food', 'transport', 'shop'],
        'forecast_query':      ['predict', 'forecast', 'next', 'future', 'estimate', 'project', 'will', 'going'],
        'anomaly_query':       ['unusual', 'abnormal', 'spike', 'outlier', 'weird', 'unexpected', 'large', 'biggest'],
    }

    def detect_intent(self, query: str) -> str:
        q = query.lower()
        scores = {intent: sum(1 for kw in kws if kw in q) for intent, kws in self.INTENT_KEYWORDS.items()}
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else 'general_query'

    def generate(self, query: str, retrieved_docs: list) -> dict:
        intent = self.detect_intent(query)
        stats = self._expense_stats

        context_snippets = [d['text'] for d in retrieved_docs[:4]]
        context_data = [d.get('data', {}) for d in retrieved_docs[:4]]

        generators = {
            'spending_query':       self._gen_spending,
            'trend_query':          self._gen_trend,
            'budget_query':         self._gen_budget,
            'recommendation_query': self._gen_recommendation,
            'category_query':       self._gen_category,
            'forecast_query':       self._gen_forecast,
            'anomaly_query':        self._gen_anomaly,
            'general_query':        self._gen_general,
        }

        generator = generators.get(intent, self._gen_general)
        answer = generator(query, retrieved_docs, stats)

        sources = [
            {'id': d['id'], 'type': d['type'], 'relevance': d.get('score', 0)}
            for d in retrieved_docs[:3]
        ]

        return {
            'answer': answer,
            'intent': intent,
            'sources': sources,
            'retrieved_count': len(retrieved_docs),
        }

    def _gen_spending(self, query, docs, stats):
        if not stats:
            return "📭 No expense data found yet. Add some expenses to get spending insights!"

        q = query.lower()
        cat_breakdown = stats.get('category_breakdown', {})

        # Check if asking about specific category
        for cat in cat_breakdown:
            if cat.lower() in q:
                amt = cat_breakdown[cat]
                return (
                    f"💳 You've spent **${amt:,.2f}** on **{cat}** in total.\n\n"
                    f"This represents **{amt / stats['total_spending'] * 100:.1f}%** of your total spending of **${stats['total_spending']:,.2f}**.\n\n"
                    f"Your average daily overall spend is **${stats['avg_daily']:,.2f}/day**."
                )

        if 'month' in q or 'this month' in q:
            change = stats['this_month'] - stats['last_month']
            direction = '📈 up' if change > 0 else '📉 down'
            return (
                f"📅 **This Month's Spending:**\n\n"
                f"• Total: **${stats['this_month']:,.2f}**\n"
                f"• Last month: **${stats['last_month']:,.2f}**\n"
                f"• Change: {direction} **${abs(change):,.2f}**\n\n"
                f"Your top expense category this month is **{stats['top_category']}** "
                f"(${stats['top_category_amount']:,.2f})."
            )

        lines = '\n'.join([f"• {cat}: **${amt:,.2f}**" for cat, amt in list(cat_breakdown.items())[:5]])
        return (
            f"💰 **Total Spending: ${stats['total_spending']:,.2f}**\n\n"
            f"Across **{stats['expense_count']}** transactions, averaging **${stats['avg_per_expense']:.2f}** per expense.\n\n"
            f"**Top Categories:**\n{lines}\n\n"
            f"Average: **${stats['avg_daily']:.2f}/day**"
        )

    def _gen_trend(self, query, docs, stats):
        if not stats:
            return "📭 No expense data yet to analyse trends. Add expenses to see trends!"

        this_m = stats.get('this_month', 0)
        last_m = stats.get('last_month', 0)
        change = this_m - last_m
        pct = (change / last_m * 100) if last_m > 0 else 0
        direction = '📈 increased' if change > 0 else '📉 decreased'
        advice = (
            "You're spending more this month — consider reviewing discretionary categories."
            if change > 0 else
            "Great progress! Your spending is trending down."
        )

        # Get relevant trend data from retrieved docs
        trend_docs = [d for d in docs if d.get('type') in ('trend', 'monthly_summary')]
        extra = f"\n\n📝 Latest trend: _{trend_docs[0]['text']}_" if trend_docs else ''

        return (
            f"📊 **Spending Trend Analysis**\n\n"
            f"• This month: **${this_m:,.2f}**\n"
            f"• Last month: **${last_m:,.2f}**\n"
            f"• Change: {direction} by **${abs(change):,.2f}** ({abs(pct):.1f}%)\n\n"
            f"💡 {advice}{extra}"
        )

    def _gen_budget(self, query, docs, stats):
        budget_docs = [d for d in docs if d.get('type') == 'budget']
        if not budget_docs:
            return (
                "📋 No budgets are currently set. Go to the **Budget** section to set spending limits "
                "per category. I'll then help you track whether you're on track!"
            )

        lines = []
        for d in budget_docs[:5]:
            data = d.get('data', {})
            cat = data.get('category', '?')
            limit = data.get('limit_amount', 0)
            spent = data.get('spent', 0)
            pct = data.get('pct', 0)
            remaining = data.get('remaining', limit - spent)
            status = '🔴 Over budget!' if spent > limit else ('🟡 Close' if pct > 80 else '🟢 On track')
            lines.append(f"• **{cat}**: ${spent:.2f} / ${limit:.2f} ({pct:.0f}%) — {status} (${remaining:.2f} remaining)")

        return (
            f"📋 **Budget Status This Month**\n\n"
            + '\n'.join(lines)
            + "\n\n💡 Tip: Review over-budget categories and apply the 50/30/20 rule for better allocation."
        )

    def _gen_recommendation(self, query, docs, stats):
        cat_breakdown = stats.get('category_breakdown', {})
        total = stats.get('total_spending', 0)

        # Find top two categories
        top2 = list(cat_breakdown.items())[:2]

        tips_from_kb = [d['text'] for d in docs if d.get('type') == 'knowledge'][:2]
        tips_text = '\n'.join([f"• _{t}_" for t in tips_from_kb]) if tips_from_kb else ''

        recs = []
        if cat_breakdown:
            top_cat, top_amt = top2[0]
            top_pct = (top_amt / total * 100) if total > 0 else 0
            recs.append(f"**{top_cat}** is your biggest spend (${top_amt:.2f}, {top_pct:.0f}%). Look for ways to reduce it.")

        recs.append(f"Your daily average is **${stats.get('avg_daily', 0):.2f}**. Reducing by 10% saves **${stats.get('avg_daily', 0) * 0.1 * 30:.2f}/month**.")
        recs.append("Set category budgets to get real-time alerts when approaching limits.")

        rec_lines = '\n'.join([f"{i+1}. {r}" for i, r in enumerate(recs)])

        return (
            f"💡 **Personalised Recommendations**\n\n"
            f"{rec_lines}\n\n"
            f"**Financial Wisdom (from knowledge base):**\n{tips_text}"
        )

    def _gen_category(self, query, docs, stats):
        cat_breakdown = stats.get('category_breakdown', {})
        total = stats.get('total_spending', 0)
        if not cat_breakdown:
            return "📭 No expense data yet. Add some expenses to see category breakdowns!"

        lines = []
        for cat, amt in list(cat_breakdown.items())[:8]:
            pct = (amt / total * 100) if total > 0 else 0
            bar = '█' * int(pct / 5) + '░' * (20 - int(pct / 5))
            lines.append(f"• **{cat}**: ${amt:,.2f} ({pct:.1f}%)\n  `{bar}`")

        return (
            f"📂 **Spending by Category** (Total: ${total:,.2f})\n\n"
            + '\n'.join(lines)
            + f"\n\n🏆 Highest: **{list(cat_breakdown.keys())[0]}** (${list(cat_breakdown.values())[0]:,.2f})"
        )

    def _gen_forecast(self, query, docs, stats):
        avg_daily = stats.get('avg_daily', 0)
        if avg_daily == 0:
            return "📭 Not enough data to forecast. Add at least a week of expenses first."

        projected_week = avg_daily * 7
        projected_month = avg_daily * 30
        return (
            f"🔮 **Spending Forecast**\n\n"
            f"Based on your average daily spend of **${avg_daily:.2f}**:\n\n"
            f"• **Next 7 days**: ~**${projected_week:.2f}**\n"
            f"• **Next 30 days**: ~**${projected_month:.2f}**\n"
            f"• **Next 3 months**: ~**${projected_month * 3:.2f}**\n\n"
            f"💡 Go to the **Analytics** tab for a detailed ML-powered day-by-day forecast chart. "
            f"Reducing daily spend by $5 would save **${5 * 30:.2f}/month**."
        )

    def _gen_anomaly(self, query, docs, stats):
        avg = stats.get('avg_per_expense', 0)
        expense_docs = [d for d in docs if d.get('type') == 'expense']
        high = [d for d in expense_docs if d.get('data', {}).get('amount', 0) > avg * 2]

        if not high:
            return (
                f"✅ **No unusual spending detected!**\n\n"
                f"Your average expense is **${avg:.2f}**. All recent transactions appear within normal range.\n\n"
                f"Go to **Analytics → Anomaly Detection** for a full ML-powered scan."
            )

        lines = [
            f"• {d['data']['description']}: **${d['data']['amount']:.2f}** on {d['data']['date']}"
            for d in high[:3]
        ]
        return (
            f"⚠️ **Potentially Unusual Expenses**\n\n"
            f"Your average expense is **${avg:.2f}**. These look high:\n\n"
            + '\n'.join(lines)
            + "\n\n💡 Check **Analytics → Anomaly Detection** for an ML-powered outlier analysis."
        )

    def _gen_general(self, query, docs, stats):
        if not stats:
            return (
                "👋 **Welcome to your AI Finance Assistant!**\n\n"
                "I use a RAG (Retrieval-Augmented Generation) system to answer questions about your expenses.\n\n"
                "Try asking:\n"
                "• _How much did I spend this month?_\n"
                "• _What's my top spending category?_\n"
                "• _Am I over budget?_\n"
                "• _Give me savings tips_\n"
                "• _Forecast my spending_"
            )

        context = '\n'.join([f"• {d['text'][:120]}..." for d in docs[:3]])
        total = stats.get('total_spending', 0)
        top_cat = stats.get('top_category', 'N/A')
        this_month = stats.get('this_month', 0)

        return (
            f"🤖 **Here's what I found related to your question:**\n\n"
            f"**Your Financial Snapshot:**\n"
            f"• Total spending: **${total:,.2f}**\n"
            f"• This month: **${this_month:,.2f}**\n"
            f"• Top category: **{top_cat}**\n"
            f"• Daily average: **${stats.get('avg_daily', 0):.2f}**\n\n"
            f"**Relevant context retrieved:**\n{context}\n\n"
            f"_Ask me a more specific question for detailed insights!_"
        )

    # ── Main Query Entry Point ────────────────────────────────────────────────

    def query(self, user_query: str, expenses: list, budgets: list) -> dict:
        self.build_knowledge_base(expenses, budgets)
        retrieved = self.retrieve(user_query, k=8)
        result = self.generate(user_query, retrieved)
        return result

    def get_suggested_questions(self, stats: dict) -> list:
        questions = [
            "How much have I spent this month?",
            "What is my top spending category?",
            "Am I over budget in any category?",
            "Give me tips to reduce my food expenses.",
            "Forecast my spending for next month.",
            "Are there any unusual expenses?",
            "Compare my spending this month vs last month.",
            "What percentage of my spending goes to transportation?",
        ]
        if stats.get('top_category'):
            questions.insert(0, f"How much did I spend on {stats['top_category']}?")
        return questions[:8]
