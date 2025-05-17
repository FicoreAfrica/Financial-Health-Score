import os
import json
import logging
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import uuid
from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SelectField, DateField, SubmitField, SelectMultipleField, IntegerField, BooleanField
from wtforms.validators import DataRequired, Email, NumberRange, Optional
from flask_session import Session
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from translations import translations

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'ficore-africa-secret-key')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(app.instance_path, 'sessions')
app.config['SESSION_PERMANENT'] = False
Session(app)

DATA_FILE = 'bills.json'
os.makedirs(app.instance_path, exist_ok=True)
os.makedirs(os.path.join(app.instance_path, 'sessions'), exist_ok=True)
os.makedirs(os.path.join(app.root_path, 'templates'), exist_ok=True)

# Default spending limits per category (monthly, in ₦)
SPENDING_LIMITS = {
    'utilities': 20000,
    'rent': 50000,
    'subscription': 10000,
    'other': 15000
}

# Forms
class UserForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    email = StringField('Email', validators=[Optional(), Email()])
    language = SelectField('Language', choices=[('en', 'English'), ('ha', 'Hausa')], validators=[DataRequired()])
    submit = SubmitField('Next')

class BillForm(FlaskForm):
    description = StringField('Description', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0)])
    due_date = DateField('Due Date', validators=[DataRequired()])
    category = SelectField('Category', choices=[
        ('utilities', 'Utilities'),
        ('rent', 'Rent'),
        ('subscription', 'Subscription'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    recurrence = SelectField('Recurrence', choices=[
        ('one-time', 'One-time'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly')
    ], validators=[DataRequired()])
    reminders = SelectMultipleField('Reminders', choices=[
        ('3_days', '3 days before'),
        ('1_day', '1 day before'),
        ('due_date', 'On due date')
    ])
    status = SelectField('Status', choices=[('Unpaid', 'Unpaid'), ('Paid', 'Paid')], validators=[DataRequired()])
    record_id = StringField('Record ID')
    submit = SubmitField('Save Bill')

class NetWorthForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    email = StringField('Email', validators=[Optional(), Email()])
    language = SelectField('Language', choices=[('en', 'English'), ('ha', 'Hausa')], validators=[DataRequired()])
    cash = FloatField('Cash and Bank Balances', validators=[Optional(), NumberRange(min=0)], default=0)
    physical_assets = FloatField('Physical Assets', validators=[Optional(), NumberRange(min=0)], default=0)
    investments = FloatField('Investments & Other Assets', validators=[Optional(), NumberRange(min=0)], default=0)
    loans = FloatField('Loans', validators=[Optional(), NumberRange(min=0)], default=0)
    other_debts = FloatField('Other Debts', validators=[Optional(), NumberRange(min=0)], default=0)
    auto_email = BooleanField('Send Results to My Email', default=False)
    submit = SubmitField('Calculate Net Worth')

class EmergencyFundForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    email = StringField('Email', validators=[Optional(), Email()])
    language = SelectField('Language', choices=[('en', 'English'), ('ha', 'Hausa')], validators=[DataRequired()])
    monthly_expenses = FloatField('Monthly Expenses', validators=[DataRequired(), NumberRange(min=0)])
    monthly_income = FloatField('Monthly Income', validators=[Optional(), NumberRange(min=0)], default=0)
    current_savings = FloatField('Current Savings', validators=[Optional(), NumberRange(min=0)], default=0)
    risk_tolerance_level = SelectField('Risk Tolerance Level', choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], validators=[DataRequired()])
    dependents = IntegerField('Number of Dependents', validators=[Optional(), NumberRange(min=0)], default=0)
    timeline = SelectField('How long are you willing to save for?', choices=[('6', '6 Months'), ('12', '12 Months'), ('18', '18 Months')], validators=[DataRequired()])
    auto_email = BooleanField('Send Results to My Email', default=False)
    submit = SubmitField('Calculate Fund')

# Bill storage
def load_bills():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading bills: {e}")
            return []
    return []

def save_bills(bills):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(bills, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving bills: {e}")

# Generate recurring bills
def generate_recurring_bills(bill, current_date):
    bills = []
    due_date = datetime.strptime(bill['DueDate'], '%Y-%m-%d')
    recurrence = bill['Recurrence']
    base_id = bill['RecordID']
    
    if recurrence == 'one-time':
        return [bill]
    
    for i in range(12):
        if recurrence == 'weekly':
            next_date = due_date + timedelta(days=7 * (i + 1))
        elif recurrence == 'monthly':
            next_date = due_date + timedelta(days=30 * (i + 1))
        elif recurrence == 'quarterly':
            next_date = due_date + timedelta(days=90 * (i + 1))
        
        if next_date.date() > current_date.date() + timedelta(days=365):
            break
        
        new_bill = bill.copy()
        new_bill['DueDate'] = next_date.strftime('%Y-%m-%d')
        new_bill['RecordID'] = f"{base_id}_{i + 1}"
        new_bill['Status'] = 'Unpaid'
        bills.append(new_bill)
    
    return [bill] + bills

# Email sending
def send_email(to_email, subject, template, lang, **kwargs):
    msg = MIMEMultipart()
    msg['From'] = os.environ.get('EMAIL_USER', 'your_email@gmail.com')
    msg['To'] = to_email.lower()
    msg['Subject'] = subject
    
    try:
        html = render_template(template, translations=translations[lang], **kwargs)
        msg.attach(MIMEText(html, 'html'))
    except Exception as e:
        logger.error(f"Error rendering email template {template}: {e}")
        return False
    
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(msg['From'], os.environ.get('EMAIL_PASSWORD', 'your_app_password'))
            server.sendmail(msg['From'], msg['To'], msg.as_string())
        logger.info(f"Sent email to {to_email} with subject '{subject}'")
        return True
    except Exception as e:
        logger.error(f"Email sending failed to {to_email}: {e}")
        return False

# Scheduler for bill reminders
scheduler = BackgroundScheduler()
scheduler.start()

def schedule_reminders(bill, email, user_name, lang):
    due_date = datetime.strptime(bill['DueDate'], '%Y-%m-%d')
    reminders = bill.get('Reminders', [])
    scheduled_jobs = bill.get('ScheduledJobs', [])
    
    for reminder in reminders:
        if reminder == '3_days':
            send_date = due_date - timedelta(days=3)
        elif reminder == '1_day':
            send_date = due_date - timedelta(days=1)
        else:  # due_date
            send_date = due_date
        
        if send_date >= datetime.now():
            job_id = f"bill_{bill['RecordID']}_{reminder}"
            scheduler.add_job(
                send_email,
                trigger=DateTrigger(run_date=send_date),
                args=[email, translations[lang]['Bill Reminder'], 'reminder_email.html', lang, 
                      {'user_name': user_name, 'bill': bill}],
                id=job_id
            )
            scheduled_jobs.append({
                'job_id': job_id,
                'send_date': send_date.strftime('%Y-%m-%d %H:%M:%S'),
                'reminder_type': reminder
            })
    
    bill['ScheduledJobs'] = scheduled_jobs

def cancel_bill_reminders(record_id):
    try:
        for job in scheduler.get_jobs():
            if job.id.startswith(f"bill_{record_id}_"):
                job.remove()
        logger.info(f"Cancelled reminders for bill {record_id}")
    except Exception as e:
        logger.error(f"Error cancelling reminders for bill {record_id}: {e}")

def reload_scheduled_jobs():
    bills = load_bills()
    for bill in bills:
        email = bill.get('Email')
        user_name = bill.get('UserName', 'User')
        lang = bill.get('Language', 'en')
        for job in bill.get('ScheduledJobs', []):
            send_date = datetime.strptime(job['send_date'], '%Y-%m-%d %H:%M:%S')
            if send_date >= datetime.now():
                scheduler.add_job(
                    send_email,
                    trigger=DateTrigger(run_date=send_date),
                    args=[email, translations[lang]['Bill Reminder'], 'reminder_email.html', lang, 
                          {'user_name': user_name, 'bill': bill}],
                    id=job['job_id']
                )
                logger.info(f"Reloaded job {job['job_id']} for bill {bill['RecordID']}")

# Routes
@app.route('/', methods=['GET'])
def index():
    lang = session.get('language', 'en')
    return render_template('index.html', translations=translations[lang], language=lang)

@app.route('/start_tool', methods=['POST'])
def start_tool():
    form = UserForm()
    lang = session.get('language', 'en')
    tool = request.form.get('tool')
    
    if form.validate_on_submit():
        try:
            session['first_name'] = form.first_name.data
            session['email'] = form.email.data.lower() if form.email.data else None
            session['language'] = form.language.data
            logger.info(f"Session updated: first_name={session['first_name']}, email={session['email']}, language={session['language']}")
            if tool == 'bill_planner':
                return redirect(url_for('bill_form'))
            elif tool == 'net_worth':
                return redirect(url_for('net_worth'))
            elif tool == 'emergency_fund':
                return redirect(url_for('emergency_fund'))
            return redirect(url_for('dashboard'))
        except Exception as e:
            logger.error(f"Error updating session: {e}")
            flash(translations[lang]['Error saving user data'], 'danger')
    
    return render_template('bill_form.html', form=form, translations=translations[lang], tool=tool)

@app.route('/bill_form', methods=['GET', 'POST'])
def bill_form():
    form = UserForm()
    lang = session.get('language', 'en')
    if form.validate_on_submit():
        session['first_name'] = form.first_name.data
        session['email'] = form.email.data.lower() if form.email.data else None
        session['language'] = form.language.data
        return redirect(url_for('view_edit_bills'))
    return render_template('bill_form.html', form=form, translations=translations[lang], language=lang)

@app.route('/view_edit_bills', methods=['GET', 'POST'])
def view_edit_bills():
    form = BillForm()
    lang = session.get('language', 'en')
    email = session.get('email')
    user_name = session.get('first_name', 'User')
    category = request.args.get('category', 'all')
    
    bills = load_bills()
    filtered_bills = [b for b in bills if category == 'all' or b['Category'] == category]
    
    if form.validate_on_submit():
        due_date = form.due_date.data
        if due_date < datetime.now().date():
            flash(translations[lang]['Due date must be today or in the future'], 'danger')
            return render_template('view_edit_bills.html',
                                form=form,
                                bills=filtered_bills,
                                category=category,
                                translations=translations[lang])
        
        bill = {
            'Description': form.description.data,
            'Amount': form.amount.data,
            'DueDate': form.due_date.data.strftime('%Y-%m-%d'),
            'Category': form.category.data,
            'Recurrence': form.recurrence.data,
            'Status': form.status.data,
            'Reminders': form.reminders.data,
            'Email': email,
            'UserName': user_name,
            'Language': lang
        }
        
        record_id = form.record_id.data
        if record_id:
            for i, b in enumerate(bills):
                if b.get('RecordID') == record_id:
                    bills[i] = bill
                    bills[i]['RecordID'] = record_id
                    break
        else:
            bill['RecordID'] = str(uuid.uuid4())
            recurring_bills = generate_recurring_bills(bill, datetime.now())
            bills.extend(recurring_bills)
            for b in recurring_bills:
                schedule_reminders(b, email, user_name, lang)
        
        if record_id:
            schedule_reminders(bill, email, user_name, lang)
        
        save_bills(bills)
        flash(translations[lang]['Save Bill'], 'success')
        return redirect(url_for('view_edit_bills', category=category))
    
    record_id = request.args.get('record_id')
    if record_id:
        for bill in bills:
            if bill.get('RecordID') == record_id:
                form.description.data = bill['Description']
                form.amount.data = bill['Amount']
                form.due_date.data = datetime.strptime(bill['DueDate'], '%Y-%m-%d')
                form.category.data = bill['Category']
                form.recurrence.data = bill['Recurrence']
                form.reminders.data = bill.get('Reminders', [])
                form.status.data = bill['Status']
                form.record_id.data = record_id
                break
    
    return render_template('view_edit_bills.html',
                          form=form,
                          bills=filtered_bills,
                          category=category,
                          translations=translations[lang])

@app.route('/toggle_status/<record_id>')
def toggle_status(record_id):
    bills = load_bills()
    for bill in bills:
        if bill.get('RecordID') == record_id:
            bill['Status'] = 'Paid' if bill['Status'] == 'Unpaid' else 'Unpaid'
            break
    save_bills(bills)
    return redirect(url_for('view_edit_bills'))

@app.route('/delete_bill/<record_id>')
def delete_bill(record_id):
    bills = load_bills()
    lang = session.get('language', 'en')
    for i, bill in enumerate(bills):
        if bill.get('RecordID') == record_id:
            bills.pop(i)
            cancel_bill_reminders(record_id)
            save_bills(bills)
            flash(translations[lang]['Bill Deleted'], 'success')
            break
    return redirect(url_for('view_edit_bills'))

@app.route('/dashboard')
def dashboard():
    lang = session.get('language', 'en')
    bills = load_bills()
    
    if not bills:
        return render_template('dashboard.html',
                            paid_count=0,
                            unpaid_count=0,
                            total_paid=0,
                            total_unpaid=0,
                            overdue_count=0,
                            total_overdue=0,
                            total_bills=0,
                            categories={},
                            due_today=[],
                            due_week=[],
                            due_month=[],
                            upcoming_bills=[],
                            spending_alerts=[],
                            tips=[
                                translations[lang]['Pay bills early to avoid late fees. Use mobile money for quick payments.'],
                                translations[lang]['Switch to energy-efficient utilities to save money.'],
                                translations[lang]['Plan monthly bills to manage your budget better.']
                            ],
                            bills=[],
                            translations=translations[lang],
                            error=translations[lang]['No bills found'])
    
    today = datetime.now().date()
    week_end = today + timedelta(days=7)
    month_end = today.replace(day=28) + timedelta(days=4)
    
    paid_bills = [b for b in bills if b['Status'] == 'Paid']
    unpaid_bills = [b for b in bills if b['Status'] == 'Unpaid']
    overdue_bills = [b for b in bills if b['Status'] == 'Unpaid' and datetime.strptime(b['DueDate'], '%Y-%m-%d').date() < today]
    
    paid_count = len(paid_bills)
    unpaid_count = len(unpaid_bills)
    overdue_count = len(overdue_bills)
    
    total_paid = sum(b['Amount'] for b in paid_bills)
    total_unpaid = sum(b['Amount'] for b in unpaid_bills)
    total_overdue = sum(b['Amount'] for b in overdue_bills)
    total_bills = sum(b['Amount'] for b in bills)
    
    categories = {}
    for bill in bills:
        cat = bill['Category']
        categories[cat] = categories.get(cat, 0) + bill['Amount']
    
    due_today = [b for b in bills if b['DueDate'] == today.strftime('%Y-%m-%d')]
    due_week = [b for b in bills if today.strftime('%Y-%m-%d') <= b['DueDate'] <= week_end.strftime('%Y-%m-%d')]
    due_month = [b for b in bills if today.strftime('%Y-%m-%d') <= b['DueDate'] <= month_end.strftime('%Y-%m-%d')]
    
    upcoming_bills = sorted(
        [b for b in bills if datetime.strptime(b['DueDate'], '%Y-%m-%d').date() >= today],
        key=lambda x: datetime.strptime(x['DueDate'], '%Y-%m-%d')
    )[:5]
    
    spending_alerts = []
    monthly_spending = {}
    current_month = today.strftime('%Y-%m')
    for bill in bills:
        bill_month = bill['DueDate'][:7]
        if bill_month == current_month:
            cat = bill['Category']
            monthly_spending[cat] = monthly_spending.get(cat, 0) + bill['Amount']
    
    for cat, amount in monthly_spending.items():
        limit = SPENDING_LIMITS.get(cat, 10000)
        if amount > limit:
            alert = translations[lang]['Spending Limit Exceeded'].format(
                limit=limit,
                category=translations[lang][cat.capitalize()]
            )
            spending_alerts.append(alert)
    
    tips = [
        translations[lang]['Pay bills early to avoid late fees. Use mobile money for quick payments.'],
        translations[lang]['Switch to energy-efficient utilities to save money.'],
        translations[lang]['Plan monthly bills to manage your budget better.']
    ]
    
    return render_template('dashboard.html',
                          paid_count=paid_count,
                          unpaid_count=unpaid_count,
                          total_paid=total_paid,
                          total_unpaid=total_unpaid,
                          overdue_count=overdue_count,
                          total_overdue=total_overdue,
                          total_bills=total_bills,
                          categories=categories,
                          due_today=due_today,
                          due_week=due_week,
                          due_month=due_month,
                          upcoming_bills=upcoming_bills,
                          spending_alerts=spending_alerts,
                          tips=tips,
                          bills=bills,
                          translations=translations[lang])

@app.route('/net_worth', methods=['GET', 'POST'])
def net_worth():
    form = NetWorthForm()
    lang = session.get('language', 'en')
    step = request.args.get('step', '1')
    
    if form.validate_on_submit():
        session['net_worth_data'] = {
            'first_name': form.first_name.data,
            'email': form.email.data.lower() if form.email.data else None,
            'language': form.language.data,
            'cash': form.cash.data or 0,
            'physical_assets': form.physical_assets.data or 0,
            'investments': form.investments.data or 0,
            'loans': form.loans.data or 0,
            'other_debts': form.other_debts.data or 0,
            'auto_email': form.auto_email.data
        }
        
        bills = load_bills()
        outstanding_bills = sum(b['Amount'] for b in bills if b['Status'] == 'Unpaid')
        total_assets = (session['net_worth_data']['cash'] +
                       session['net_worth_data']['physical_assets'] +
                       session['net_worth_data']['investments'])
        total_liabilities = (session['net_worth_data']['loans'] +
                           session['net_worth_data']['other_debts'] +
                           outstanding_bills)
        net_worth = total_assets - total_liabilities
        
        insights = []
        if net_worth >= 0:
            insights.append(translations[lang]['Positive Net Worth'])
        else:
            insights.append(translations[lang]['Negative Net Worth'])
        
        asset_types = {
            'cash': session['net_worth_data']['cash'],
            'physical_assets': session['net_worth_data']['physical_assets'],
            'investments': session['net_worth_data']['investments']
        }
        total_assets_nonzero = sum(v for v in asset_types.values() if v > 0)
        for asset, value in asset_types.items():
            if total_assets_nonzero > 0 and value / total_assets_nonzero > 0.7:
                insights.append(translations[lang]['Asset Concentration Warning'].format(
                    asset_type=translations[lang][asset.capitalize()]
                ))
        
        if total_assets > 0 and total_liabilities / total_assets > 0.6:
            insights.append(translations[lang]['High Debt Ratio'])
        
        badge = translations[lang]['Net Worth Milestone'] if net_worth >= 0 else None
        
        if session['net_worth_data']['auto_email'] and session['net_worth_data']['email']:
            send_email(
                session['net_worth_data']['email'],
                translations[lang]['Net Worth Calculator'],
                'networth_email.html',
                lang,
                user_name=session['net_worth_data']['first_name'],
                total_assets=total_assets,
                total_liabilities=total_liabilities,
                outstanding_bills=outstanding_bills,
                net_worth=net_worth,
                insights=insights,
                badge=badge
            )
        
        return render_template('net_worth_dashboard.html',
                             total_assets=total_assets,
                             total_liabilities=total_liabilities,
                             outstanding_bills=outstanding_bills,
                             net_worth=net_worth,
                             asset_data=asset_types,
                             liability_data={
                                 'loans': session['net_worth_data']['loans'],
                                 'other_debts': session['net_worth_data']['other_debts'],
                                 'outstanding_bills': outstanding_bills
                             },
                             insights=insights,
                             badge=badge,
                             translations=translations[lang])
    
    return render_template('net_worth_form.html',
                          form=form,
                          step=step,
                          translations=translations[lang])

@app.route('/net_worth_share', methods=['POST'])
def net_worth_share():
    lang = session.get('language', 'en')
    email = request.form.get('email')
    if not email:
        flash(translations[lang]['Enter your email'], 'danger')
        return redirect(url_for('net_worth'))
    
    data = session.get('net_worth_data', {})
    bills = load_bills()
    outstanding_bills = sum(b['Amount'] for b in bills if b['Status'] == 'Unpaid')
    total_assets = sum(data.get(k, 0) for k in ['cash', 'physical_assets', 'investments'])
    total_liabilities = sum(data.get(k, 0) for k in ['loans', 'other_debts']) + outstanding_bills
    net_worth = total_assets - total_liabilities
    insights = []
    if net_worth >= 0:
        insights.append(translations[lang]['Positive Net Worth'])
    else:
        insights.append(translations[lang]['Negative Net Worth'])
    badge = translations[lang]['Net Worth Milestone'] if net_worth >= 0 else None
    
    if send_email(
        email,
        translations[lang]['Net Worth Calculator'],
        'networth_email.html',
        lang,
        user_name=data.get('first_name', 'User'),
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        outstanding_bills=outstanding_bills,
        net_worth=net_worth,
        insights=insights,
        badge=badge
    ):
        flash(translations[lang]['Share Results'], 'success')
    else:
        flash(translations[lang]['Error sending email'], 'danger')
    
    return redirect(url_for('net_worth'))

@app.route('/emergency_fund', methods=['GET', 'POST'])
def emergency_fund():
    form = EmergencyFundForm()
    lang = session.get('language', 'en')
    step = request.args.get('step', '1')
    
    bills = load_bills()
    monthly_expenses = sum(b['Amount'] for b in bills if b['Status'] == 'Unpaid' and b['Recurrence'] in ['monthly', 'weekly'])
    
    if form.validate_on_submit():
        session['emergency_fund_data'] = {
            'first_name': form.first_name.data,
            'email': form.email.data.lower() if form.email.data else None,
            'language': form.language.data,
            'monthly_expenses': form.monthly_expenses.data,
            'monthly_income': form.monthly_income.data or 0,
            'current_savings': form.current_savings.data or 0,
            'risk_tolerance_level': form.risk_tolerance_level.data,
            'dependents': form.dependents.data or 0,
            'timeline': int(form.timeline.data),
            'auto_email': form.auto_email.data
        }
        
        months = {'low': 3, 'medium': 6, 'high': 9}[session['emergency_fund_data']['risk_tolerance_level']]
        months += session['emergency_fund_data']['dependents']
        target_fund = session['emergency_fund_data']['monthly_expenses'] * months
        savings_gap = target_fund - session['emergency_fund_data']['current_savings']
        monthly_savings = savings_gap / session['emergency_fund_data']['timeline'] if savings_gap > 0 else 0
        
        insights = []
        if monthly_savings > session['emergency_fund_data']['monthly_income'] * 0.3:
            insights.append(translations[lang]['High Savings Requirement'])
        if target_fund <= session['emergency_fund_data']['current_savings']:
            insights.append(translations[lang]['Sufficient Emergency Fund'])
        
        badge = translations[lang]['Emergency Fund Milestone'] if target_fund <= session['emergency_fund_data']['current_savings'] else None
        
        if session['emergency_fund_data']['auto_email'] and session['emergency_fund_data']['email']:
            send_email(
                session['emergency_fund_data']['email'],
                translations[lang]['Emergency Fund Calculator'],
                'emergencyfund_email.html',
                lang,
                user_name=session['emergency_fund_data']['first_name'],
                target_fund=target_fund,
                savings_gap=savings_gap,
                monthly_savings=monthly_savings,
                current_savings=session['emergency_fund_data']['current_savings'],
                months=months,
                insights=insights,
                badge=badge
            )
        
        return render_template('emergency_fund_dashboard.html',
                             target_fund=target_fund,
                             savings_gap=savings_gap,
                             monthly_savings=monthly_savings,
                             current_savings=session['emergency_fund_data']['current_savings'],
                             months=months,
                             insights=insights,
                             badge=badge,
                             translations=translations[lang])
    
    return render_template('emergency_fund_form.html',
                          form=form,
                          step=step,
                          monthly_expenses=monthly_expenses,
                          translations=translations[lang])

@app.route('/emergency_fund_share', methods=['POST'])
def emergency_fund_share():
    lang = session.get('language', 'en')
    email = request.form.get('email')
    if not email:
        flash(translations[lang]['Enter your email'], 'danger')
        return redirect(url_for('emergency_fund'))
    
    data = session.get('emergency_fund_data', {})
    months = {'low': 3, 'medium': 6, 'high': 9}[data.get('risk_tolerance_level', 'medium')] + data.get('dependents', 0)
    target_fund = data.get('monthly_expenses', 0) * months
    savings_gap = target_fund - data.get('current_savings', 0)
    monthly_savings = savings_gap / data.get('timeline', 12) if savings_gap > 0 else 0
    insights = []
    if monthly_savings > data.get('monthly_income', 0) * 0.3:
        insights.append(translations[lang]['High Savings Requirement'])
    if target_fund <= data.get('current_savings', 0):
        insights.append(translations[lang]['Sufficient Emergency Fund'])
    badge = translations[lang]['Emergency Fund Milestone'] if target_fund <= data.get('current_savings', 0) else None
    
    if send_email(
        email,
        translations[lang]['Emergency Fund Calculator'],
        'emergencyfund_email.html',
        lang,
        user_name=data.get('first_name', 'User'),
        target_fund=target_fund,
        savings_gap=savings_gap,
        monthly_savings=monthly_savings,
        current_savings=data.get('current_savings', 0),
        months=months,
        insights=insights,
        badge=badge
    ):
        flash(translations[lang]['Share Results'], 'success')
    else:
        flash(translations[lang]['Error sending email'], 'danger')
    
    return redirect(url_for('emergency_fund'))

@app.route('/logout', methods=['GET'])
def logout():
    session.clear()
    lang = session.get('language', 'en')
    flash(translations[lang]['You have been logged out'], 'success')
    return redirect(url_for('index'))

@app.route('/change_language', methods=['GET', 'POST'])
def change_language():
    lang = session.get('language', 'en')
    supported_languages = ['en', 'ha']
    
    if request.method == 'POST':
        new_lang = request.form.get('language')
    else:
        new_lang = request.args.get('language')
    
    if new_lang in supported_languages:
        session['language'] = new_lang
        flash(translations[new_lang]['Language changed successfully'], 'success')
    else:
        flash(translations[lang]['Invalid language selected'], 'danger')
    
    # Redirect to the previous page or index
    referer = request.headers.get('Referer')
    return redirect(referer if referer else url_for('index'))

if __name__ == '__main__':
    reload_scheduled_jobs()
    app.run(debug=True)
