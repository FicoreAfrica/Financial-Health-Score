from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SelectField, DateField, SubmitField, SelectMultipleField
from wtforms.validators import DataRequired, Email, NumberRange
from flask_session import Session
import json
import os
import logging
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger

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

# Translations
translations = {
    'en': {
        'Bill Planner': 'Bill Planner',
        'Financial growth passport for Africa': 'Financial growth passport for Africa',
        'Enter your first name': 'Enter your first name',
        'Enter your email': 'Enter your email',
        'Choose your language': 'Choose your language',
        'Next': 'Next',
        'View and Edit Bills': 'View and Edit Bills',
        'Select Category': 'Select Category',
        'All': 'All',
        'Utilities': 'Utilities',
        'Rent': 'Rent',
        'Subscription': 'Subscription',
        'Other': 'Other',
        'Description': 'Description',
        'Amount': 'Amount',
        'Due Date': 'Due Date',
        'Status': 'Status',
        'Paid': 'Paid',
        'Unpaid': 'Unpaid',
        'Add New Bill': 'Add New Bill',
        'What is this bill for?': 'What is this bill for?',
        'How much is the bill? (₦)': 'How much is the bill? (₦)',
        'When is this bill due?': 'When is this bill due?',
        'How often does this bill occur?': 'How often does this bill occur?',
        'One-time': 'One-time',
        'Weekly': 'Weekly',
        'Monthly': 'Monthly',
        'Quarterly': 'Quarterly',
        'Send me reminders': 'Send me reminders',
        '3 days before': '3 days before',
        '1 day before': '1 day before',
        'On due date': 'On due date',
        'Save Bill': 'Save Bill',
        'Edit': 'Edit',
        'Delete': 'Delete',
        'Confirm Delete': 'Are you sure you want to delete this bill?',
        'Bill Deleted': 'Bill deleted successfully',
        'Back': 'Back',
        'Go to Dashboard': 'Go to Dashboard',
        'Dashboard': 'Dashboard',
        'Paid Bills': 'Paid Bills',
        'Unpaid Bills': 'Unpaid Bills',
        'Total Bills': 'Total Bills',
        'Total Paid': 'Total Paid',
        'Total Unpaid': 'Total Unpaid',
        'Overdue Bills': 'Overdue Bills',
        'Upcoming Bills': 'Upcoming Bills',
        'Spending by Category': 'Spending by Category',
        'Bills Due': 'Bills Due',
        'Today': 'Today',
        'This Week': 'This Week',
        'This Month': 'This Month',
        'Tips for Managing Bills': 'Tips for Managing Bills',
        'Pay bills early to avoid late fees. Use mobile money for quick payments.': 'Pay bills early to avoid late fees. Use mobile money for quick payments.',
        'Switch to energy-efficient utilities to save money.': 'Switch to energy-efficient utilities to save money.',
        'Plan monthly bills to manage your budget better.': 'Plan monthly bills to manage your budget better.',
        'Dear': 'Dear',
        'Bill Reminder': 'Bill Reminder',
        'Your bill is due soon': 'Your bill is due soon',
        'Due': 'Due',
        'Pay now to avoid late fees': 'Pay now to avoid late fees',
        'Manage your bills': 'Manage your bills',
        'Thank you for using Ficore Africa': 'Thank you for using Ficore Africa',
        'Due date must be today or in the future': 'Due date must be today or in the future',
        'Spending Limit Exceeded': 'You’ve exceeded ₦{limit} on {category} this month'
    },
    'ha': {
        'Bill Planner': 'Tsara Kuɗin Biya',
        'Financial growth passport for Africa': 'Fasfo na ci gaban kuɗi don mutanen Afirka',
        'Enter your first name': 'Shigar da sunanka na farko',
        'Enter your email': 'Shigar da imel ɗinka',
        'Choose your language': 'Zaɓi yaren da akeso',
        'Next': 'Na gaba',
        'View and Edit Bills': 'Wajen Dubawa da Gyara Tsari',
        'Select Category': 'Zaɓi Rukuni',
        'All': 'Duka',
        'Utilities': 'Kayan Amfani',
        'Rent': 'Kudin Haya',
        'Subscription': 'Biyan Subscription',
        'Other': 'Abu Na Daban',
        'Description': 'Bayanan Tsari',
        'Amount': 'Adadin',
        'Due Date': 'Ranar Biya',
        'Status': 'Matsayi',
        'Paid': 'An Biya',
        'Unpaid': 'Ba a Biya ba',
        'Add New Bill': 'Sabon Kuɗin Biya',
        'What is this bill for?': 'Wannan kuɗin na me ne?',
        'How much is the bill? (₦)': 'Nawa ne kuɗin? (₦)',
        'When is this bill due?': 'Yaushe ne za,a biya wannan kuɗin?',
        'How often does this bill occur?': 'Sau nawa biyan wannan kuɗin yake faruwa?',
        'One-time': 'Lokaci ɗaya',
        'Weekly': 'Mako-mako',
        'Monthly': 'Kowane wata',
        'Quarterly': 'Kowane Wata Uku',
        'Send me reminders': 'Aiko mini da tunatarwa',
        '3 days before': 'Kwanaki 3 kafin',
        '1 day before': 'Rana 1 kafin',
        'On due date': 'A ranar Biya',
        'Save Bill': 'Adana Kuɗin Biya',
        'Edit': 'Gyara',
        'Delete': 'Goge',
        'Confirm Delete': 'Shin ka tabbatar kana so ka goge wannan kuɗin biyan?',
        'Bill Deleted': 'An goge kuɗin biyan cikin nasara',
        'Back': 'Koma baya',
        'Go to Dashboard': 'Je zuwa Dashboard',
        'Dashboard': 'Allon Bayanai',
        'Paid Bills': 'Kuɗin da aka biya',
        'Unpaid Bills': 'Kuɗin da ba a biya ba',
        'Total Bills': 'Jimlar Kuɗin Biya',
        'Total Paid': 'Jimlar wanda aka biya',
        'Total Unpaid': 'Jimlar wanda ba a biya ba',
        'Overdue Bills': 'Kuɗin da suka wuce kwanan watan biya',
        'Upcoming Bills': 'Kuɗin da ke zuwa nan gaba',
        'Spending by Category': 'Rukunin Kudin Kashewa',
        'Bills Due': 'Kuɗin da ranar biya ya masto kusa',
        'Today': 'Yau',
        'This Week': 'Wannan Mako',
        'This Month': 'Wannan Wata',
        'Tips for Managing Bills': 'Shawara don Sarrafa Kuɗin Biya',
        'Pay bills early to avoid late fees. Use mobile money for quick payments.': 'Biya kuɗi da wuri don guje wa kalubalen jinkiri kamar karin kudin ruwa. Yi amfani da wayar hannunku don biya cikin sauri.',
        'Switch to energy-efficient utilities to save money.': 'Canja zuwa kayan aiki masu amfani da makamashi don ajiyar kuɗi.',
        'Plan monthly bills to manage your budget better.': 'Tsara kuɗin kowane wata don sarrafa kasafin kuɗin ka mafi kyau.',
        'Dear': 'Barka',
        'Bill Reminder': 'Tunatarwar Kuɗi',
        'Your bill is due soon': 'Lokacin biyan Kudin yana kusa',
        'Due': 'Ya Iso',
        'Pay now to avoid late fees': 'Biya yanzu don guje wa kalubalen jinkiri',
        'Manage your bills': 'Sarrafa kuɗin ka',
        'Thank you for using Ficore Africa': 'Muna godiya da amfani da Ficore Afirka',
        'Due date must be today or in the future': 'Ranar Biya dole ne ta kasance yau ko a nan gaba',
        'Spending Limit Exceeded': 'Ka wuce ₦{limit} akan {category} a wannan wata'
    }
}

# Forms
class UserForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
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

# Email reminder
def send_email_reminder(to_email, user_name, bill, lang, reminder_type):
    msg = MIMEMultipart()
    msg['From'] = os.environ.get('EMAIL_USER', 'your_email@gmail.com')
    msg['To'] = to_email.lower()
    msg['Subject'] = translations[lang]['Bill Reminder']
    
    reminder_text = {
        '3_days': '3 days before due date',
        '1_day': '1 day before due date',
        'due_date': 'on due date'
    }[reminder_type]
    
    try:
        html = render_template('reminder_email.html',
                            user_name=user_name,
                            bill=bill,
                            reminder_text=reminder_text,
                            translations=translations[lang])
        msg.attach(MIMEText(html, 'html'))
    except Exception as e:
        logger.error(f"Error rendering reminder_email.html: {e}")
        return
    
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(msg['From'], os.environ.get('EMAIL_PASSWORD', 'your_app_password'))
            server.sendmail(msg['From'], msg['To'], msg.as_string())
        logger.info(f"Sent reminder email to {to_email} for bill {bill['RecordID']} ({reminder_type})")
    except Exception as e:
        logger.error(f"Email sending failed for {to_email}, bill {bill['RecordID']}: {e}")

# Scheduler for reminders
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
                send_email_reminder,
                trigger=DateTrigger(run_date=send_date),
                args=[email, user_name, bill, lang, reminder],
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

# Reload scheduled jobs on app start
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
                    send_email_reminder,
                    trigger=DateTrigger(run_date=send_date),
                    args=[email, user_name, bill, lang, job['reminder_type']],
                    id=job['job_id']
                )
                logger.info(f"Reloaded job {job['job_id']} for bill {bill['RecordID']}")

# Routes
@app.route('/', methods=['GET', 'POST'])
def fill_form():
    form = UserForm()
    lang = session.get('language', 'en')
    
    if form.validate_on_submit():
        try:
            session['first_name'] = form.first_name.data
            session['email'] = form.email.data.lower()
            session['language'] = form.language.data
            logger.info(f"Session updated: first_name={session['first_name']}, email={session['email']}, language={session['language']}")
        except Exception as e:
            logger.error(f"Error updating session: {e}")
            flash(translations[lang]['Error saving user data'], 'danger')
            return render_template('bill_form.html', form=form, translations=translations[lang])
        return redirect(url_for('view_edit_bills'))
    
    try:
        return render_template('bill_form.html',
                            form=form,
                            translations=translations[lang])
    except Exception as e:
        logger.error(f"Error rendering bill_form.html: {e}")
        raise

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
            bill['RecordID'] = str(len(bills) + 1)
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
    
    try:
        return render_template('view_edit_bills.html',
                            form=form,
                            bills=filtered_bills,
                            category=category,
                            translations=translations[lang])
    except Exception as e:
        logger.error(f"Error rendering view_edit_bills.html: {e}")
        raise

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
    
    try:
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
    except Exception as e:
        logger.error(f"Error rendering dashboard.html: {e}")
        raise

@app.route('/test_email')
def test_email():
    lang = session.get('language', 'en')
    email = session.get('email', 'test@example.com')
    user_name = session.get('first_name', 'Test User')
    bill = {
        'Description': 'Test Bill',
        'Amount': 1000.0,
        'DueDate': datetime.now().strftime('%Y-%m-%d'),
        'RecordID': 'test'
    }
    send_email_reminder(email, user_name, bill, lang, 'due_date')
    flash(translations[lang]['Test email sent'], 'success')
    return redirect(url_for('view_edit_bills'))

# Initialize scheduler
reload_scheduled_jobs()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
