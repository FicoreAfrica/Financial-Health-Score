from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SelectField, DateField, SubmitField, SelectMultipleField, IntegerField
from wtforms.validators import DataRequired, Email, NumberRange, Optional
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
import uuid

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

# Translations (English and Hausa only)
translations = {
    'en': {
        'Bill Planner': 'Bill Planner',
        'Financial growth passport for Africa': 'Financial growth passport for Africa',
        'Enter your first name': 'Enter your first name',
        'Enter your email': 'Enter your email',
        'Choose your language': 'Choose your language',
        'English': 'English',
        'Hausa': 'Hausa',
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
        'Category': 'Category',
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
        'Spending Limit Exceeded': 'You’ve exceeded ₦{limit} on {category} this month',
        'Net Worth Calculator': 'Net Worth Calculator',
        'Know Your Net Worth': 'Know Your Net Worth',
        'Personal Information': 'Personal Information',
        'Assets': 'Assets',
        'Cash and Bank Balances': 'Cash and Bank Balances',
        'Investments': 'Investments',
        'Real Estate': 'Real Estate',
        'Vehicles': 'Vehicles',
        'Business Ownership': 'Business Ownership',
        'Other Assets': 'Other Assets',
        'Liabilities': 'Liabilities',
        'Credit Card Debt': 'Credit Card Debt',
        'Loans': 'Loans',
        'Outstanding Bills': 'Outstanding Bills',
        'Other Debts': 'Other Debts',
        'Calculate Net Worth': 'Calculate Net Worth',
        'Total Assets': 'Total Assets',
        'Total Liabilities': 'Total Liabilities',
        'Net Worth': 'Net Worth',
        'Positive Net Worth': 'Great! Let’s grow it.',
        'Negative Net Worth': 'Focus on reducing high-interest debt.',
        'Asset Concentration Warning': 'Over-reliance on {asset_type}. Consider diversifying.',
        'High Debt Ratio': 'Debt exceeds 60% of assets. Reduce debt for stability.',
        'Share Results': 'Share Results',
        'Net Worth Milestone': 'Net Worth Milestone! Positive net worth achieved!',
        'Emergency Fund Calculator': 'Emergency Fund Calculator',
        'Plan Emergency Fund': 'Plan Emergency Fund',
        'Financial Details': 'Financial Details',
        'Monthly Expenses': 'Monthly Expenses',
        'Monthly Income': 'Monthly Income',
        'Current Savings': 'Current Savings',
        'Risk Level': 'Risk Level',
        'Low': 'Low',
        'Medium': 'Medium',
        'High': 'High',
        'Number of Dependents': 'Number of Dependents',
        'Savings Timeline': 'Savings Timeline',
        '6 Months': '6 Months',
        '12 Months': '12 Months',
        '18 Months': '18 Months',
        'Auto Email Results': 'Send results to my email',
        'Calculate Fund': 'Calculate Fund',
        'Target Fund Size': 'Target Fund Size',
        'Savings Gap': 'Savings Gap',
        'Monthly Savings Goal': 'Monthly Savings Goal',
        'Timeline': 'Timeline',
        'Fund Builder': 'Fund Builder! Emergency fund plan created!',
        'Based on your bills, save ₦{amount}/month to reach your emergency fund goal in {months} months.': 'Based on your bills, save ₦{amount}/month to reach your emergency fund goal in {months} months.',
        'Error sending email': 'Error sending email'
    },
    'ha': {
        'Bill Planner': 'Mai Tsara Kuɗi',
        'Financial growth passport for Africa': 'Fasfo na ci gaban kuɗi don Afirka',
        'Enter your first name': 'Shigar da sunanka na farko',
        'Enter your email': 'Shigar da imel ɗinka',
        'Choose your language': 'Zaɓi yarenka',
        'English': 'Turanci',
        'Hausa': 'Hausa',
        'Next': 'Na gaba',
        'View and Edit Bills': 'Duba da Gyara Kuɗi',
        'Select Category': 'Zaɓi Rukuni',
        'All': 'Duk',
        'Utilities': 'Kayan aiki',
        'Rent': 'Haya',
        'Subscription': 'Biyan kuɗi',
        'Other': 'Sauran',
        'Description': 'Bayanin',
        'Amount': 'Adadin',
        'Due Date': 'Ranar Karewa',
        'Status': 'Matsayi',
        'Paid': 'An Biya',
        'Unpaid': 'Ba a Biya ba',
        'Add New Bill': 'Ƙara Sabon Kuɗi',
        'What is this bill for?': 'Wannan kuɗin na me ne?',
        'How much is the bill? (₦)': 'Nawa ne kuɗin? (₦)',
        'When is this bill due?': 'Yaushe ne wannan kuɗin zai kare?',
        'Category': 'Rukuni',
        'How often does this bill occur?': 'Sau nawa wannan kuɗin yake faruwa?',
        'One-time': 'Lokaci ɗaya',
        'Weekly': 'Mako-mako',
        'Monthly': 'Kowane wata',
        'Quarterly': 'Kowane kwata',
        'Send me reminders': 'Aiko mini da tunatarwa',
        '3 days before': 'Kwanaki 3 kafin',
        '1 day before': 'Rana 1 kafin',
        'On due date': 'A ranar karewa',
        'Save Bill': 'Ajiye Kuɗi',
        'Edit': 'Gyara',
        'Delete': 'Goge',
        'Confirm Delete': 'Shin ka tabbata kana so ka goge wannan kuɗin?',
        'Bill Deleted': 'An goge kuɗin cikin nasara',
        'Back': 'Koma baya',
        'Go to Dashboard': 'Je zuwa Dashboard',
        'Dashboard': 'Dashboard',
        'Paid Bills': 'Kuɗin da aka biya',
        'Unpaid Bills': 'Kuɗin da ba a biya ba',
        'Total Bills': 'Jimlar Kuɗi',
        'Total Paid': 'Jimlar da aka biya',
        'Total Unpaid': 'Jimlar da ba a biya ba',
        'Overdue Bills': 'Kuɗin da suka wuce kwanan wata',
        'Upcoming Bills': 'Kuɗin da ke zuwa',
        'Spending by Category': 'Kashewa ta Rukuni',
        'Bills Due': 'Kuɗin da za a biya',
        'Today': 'Yau',
        'This Week': 'Wannan Mako',
        'This Month': 'Wannan Wata',
        'Tips for Managing Bills': 'Shawara don Sarrafa Kuɗi',
        'Pay bills early to avoid late fees. Use mobile money for quick payments.': 'Biya kuɗi da wuri don guje wa jaruman jinkiri. Yi amfani da kuɗin wayar hannu don biya cikin sauri.',
        'Switch to energy-efficient utilities to save money.': 'Canja zuwa kayan aiki masu amfani da makamashi don ajiyar kuɗi.',
        'Plan monthly bills to manage your budget better.': 'Tsara kuɗin kowane wata don sarrafa kasafin kuɗin ka mafi kyau.',
        'Dear': 'Masoyi',
        'Bill Reminder': 'Tunatarwar Kuɗi',
        'Your bill is due soon': 'Kuɗin ka yana kusa da karewa',
        'Due': 'Karewa',
        'Pay now to avoid late fees': 'Biya yanzu don guje wa jaruman jinkiri',
        'Manage your bills': 'Sarrafa kuɗin ka',
        'Thank you for using Ficore Africa': 'Na godiya da amfani da Ficore Afirka',
        'Due date must be today or in the future': 'Ranar karewa dole ne ta kasance yau ko a nan gaba',
        'Spending Limit Exceeded': 'Ka wuce ₦{limit} akan {category} a wannan wata',
        'Net Worth Calculator': 'Kalkuleta na Darajar Kuɗi',
        'Know Your Net Worth': 'San Darajar Kuɗinka',
        'Personal Information': 'Bayanan Kai',
        'Assets': 'Kaddarori',
        'Cash and Bank Balances': 'Kuɗi da Ma’ajiyar Banki',
        'Investments': 'Jari',
        'Real Estate': 'Ƙasa da Gidaje',
        'Vehicles': 'Motoci',
        'Business Ownership': 'Mallakar Kasuwanci',
        'Other Assets': 'Sauran Kaddarori',
        'Liabilities': 'Bashi',
        'Credit Card Debt': 'Bashin Katin Kiredit',
        'Loans': 'Rancen Kuɗi',
        'Outstanding Bills': 'Kuɗin da ba a biya ba',
        'Other Debts': 'Sauran Basussuka',
        'Calculate Net Worth': 'Ƙididdige Darajar Kuɗi',
        'Total Assets': 'Jimlar Kaddarori',
        'Total Liabilities': 'Jimlar Bashi',
        'Net Worth': 'Darajar Kuɗi',
        'Positive Net Worth': 'Yabanya! Bari mu ƙara girma.',
        'Negative Net Worth': 'Mayar da hankali kan rage bashi mai yawan riba.',
        'Asset Concentration Warning': 'Dogaro da yawa akan {asset_type}. Yi la’akari da rarrabawa.',
        'High Debt Ratio': 'Bashi ya wuce 60% na kaddarori. Rage bashi don kwanciyar hankali.',
        'Share Results': 'Raba Sakamakon',
        'Net Worth Milestone': 'Alamar Darajar Kuɗi! An samu darajar kuɗi mai kyau!',
        'Emergency Fund Calculator': 'Kalkuleta na Asusun Gaggawa',
        'Plan Emergency Fund': 'Shirya Asusun Gaggawa',
        'Financial Details': 'Bayanan Kuɗi',
        'Monthly Expenses': 'Kashewar Wata-wata',
        'Monthly Income': 'Kudaden shiga na Wata-wata',
        'Current Savings': 'Ajiyar Yanzu',
        'Risk Level': 'Matsayin Haɗari',
        'Low': 'Ƙarami',
        'Medium': 'Matsakaici',
        'High': 'Mai Yawa',
        'Number of Dependents': 'Yawan Masu Dogaro',
        'Savings Timeline': 'Jadawalin Ajiya',
        '6 Months': 'Watanni 6',
        '12 Months': 'Watanni 12',
        '18 Months': 'Watanni 18',
        'Auto Email Results': 'Aika sakamakon zuwa imel dina',
        'Calculate Fund': 'Ƙididdige Asusun',
        'Target Fund Size': 'Girman Asusun da ake Nema',
        'Savings Gap': 'Gibin Ajiya',
        'Monthly Savings Goal': 'Manzon Ajiyar Wata-wata',
        'Timeline': 'Jadawali',
        'Fund Builder': 'Mai Gina Asusun! An ƙirƙiri shirin asusun gaggawa!',
        'Based on your bills, save ₦{amount}/month to reach your emergency fund goal in {months} months.': 'Bisa kuɗin ka, ajiye ₦{amount}/wata don isa burin asusun gaggawa a cikin watanni {months}.',
        'Error sending email': 'Kuskure wajen aikawa da imel'
    }
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
    # Step 1: Personal Information
    first_name = StringField('First Name', validators=[DataRequired()])
    email = StringField('Email', validators=[Optional(), Email()])
    language = SelectField('Language', choices=[('en', 'English'), ('ha', 'Hausa')], validators=[DataRequired()])
    # Step 2: Assets
    cash = FloatField('Cash and Bank Balances', validators=[Optional(), NumberRange(min=0)], default=0)
    investments = FloatField('Investments', validators=[Optional(), NumberRange(min=0)], default=0)
    real_estate = FloatField('Real Estate', validators=[Optional(), NumberRange(min=0)], default=0)
    vehicles = FloatField('Vehicles', validators=[Optional(), NumberRange(min=0)], default=0)
    business = FloatField('Business Ownership', validators=[Optional(), NumberRange(min=0)], default=0)
    other_assets = FloatField('Other Assets', validators=[Optional(), NumberRange(min=0)], default=0)
    # Step 3: Liabilities
    credit_card = FloatField('Credit Card Debt', validators=[Optional(), NumberRange(min=0)], default=0)
    loans = FloatField('Loans', validators=[Optional(), NumberRange(min=0)], default=0)
    other_debts = FloatField('Other Debts', validators=[Optional(), NumberRange(min=0)], default=0)
    auto_email = SelectField('Auto Email Results', choices=[('yes', 'Yes'), ('no', 'No')], default='no')
    submit = SubmitField('Calculate Net Worth')

class EmergencyFundForm(FlaskForm):
    # Step 1: Personal Information
    first_name = StringField('First Name', validators=[DataRequired()])
    email = StringField('Email', validators=[Optional(), Email()])
    language = SelectField('Language', choices=[('en', 'English'), ('ha', 'Hausa')], validators=[DataRequired()])
    # Step 2: Financial Details
    monthly_expenses = FloatField('Monthly Expenses', validators=[DataRequired(), NumberRange(min=0)])
    monthly_income = FloatField('Monthly Income', validators=[Optional(), NumberRange(min=0)], default=0)
    current_savings = FloatField('Current Savings', validators=[Optional(), NumberRange(min=0)], default=0)
    risk_level = SelectField('Risk Level', choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], validators=[DataRequired()])
    dependents = IntegerField('Number of Dependents', validators=[Optional(), NumberRange(min=0)], default=0)
    # Step 3: Savings Timeline
    timeline = SelectField('Savings Timeline', choices=[('6', '6 Months'), ('12', '12 Months'), ('18', '18 Months')], validators=[DataRequired()])
    auto_email = SelectField('Auto Email Results', choices=[('yes', 'Yes'), ('no', 'No')], default='no')
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
@app.route('/', methods=['GET', 'POST'])
def fill_form():
    form = UserForm()
    lang = session.get('language', 'en')
    
    if form.validate_on_submit():
        try:
            session['first_name'] = form.first_name.data
            session['email'] = form.email.data.lower() if form.email.data else None
            session['language'] = form.language.data
            logger.info(f"Session updated: first_name={session['first_name']}, email={session['email']}, language={session['language']}")
            return redirect(url_for('dashboard'))
        except Exception as e:
            logger.error(f"Error updating session: {e}")
            flash(translations[lang]['Error saving user data'], 'danger')
    
    return render_template('bill_form.html', form=form, translations=translations[lang])

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
            'investments': form.investments.data or 0,
            'real_estate': form.real_estate.data or 0,
            'vehicles': form.vehicles.data or 0,
            'business': form.business.data or 0,
            'other_assets': form.other_assets.data or 0,
            'credit_card': form.credit_card.data or 0,
            'loans': form.loans.data or 0,
            'other_debts': form.other_debts.data or 0,
            'auto_email': form.auto_email.data
        }
        
        # Calculate net worth
        bills = load_bills()
        outstanding_bills = sum(b['Amount'] for b in bills if b['Status'] == 'Unpaid')
        total_assets = (session['net_worth_data']['cash'] +
                       session['net_worth_data']['investments'] +
                       session['net_worth_data']['real_estate'] +
                       session['net_worth_data']['vehicles'] +
                       session['net_worth_data']['business'] +
                       session['net_worth_data']['other_assets'])
        total_liabilities = (session['net_worth_data']['credit_card'] +
                           session['net_worth_data']['loans'] +
                           session['net_worth_data']['other_debts'] +
                           outstanding_bills)
        net_worth = total_assets - total_liabilities
        
        # Insights
        insights = []
        if net_worth >= 0:
            insights.append(translations[lang]['Positive Net Worth'])
        else:
            insights.append(translations[lang]['Negative Net Worth'])
        
        asset_types = {
            'cash': session['net_worth_data']['cash'],
            'investments': session['net_worth_data']['investments'],
            'real_estate': session['net_worth_data']['real_estate'],
            'vehicles': session['net_worth_data']['vehicles'],
            'business': session['net_worth_data']['business'],
            'other_assets': session['net_worth_data']['other_assets']
        }
        total_assets_nonzero = sum(v for v in asset_types.values() if v > 0)
        for asset, value in asset_types.items():
            if total_assets_nonzero > 0 and value / total_assets_nonzero > 0.7:
                insights.append(translations[lang]['Asset Concentration Warning'].format(
                    asset_type=translations[lang][asset.capitalize()]
                ))
        
        if total_assets > 0 and total_liabilities / total_assets > 0.6:
            insights.append(translations[lang]['High Debt Ratio'])
        
        # Gamification
        badge = translations[lang]['Net Worth Milestone'] if net_worth >= 0 else None
        
        # Auto-email
        if session['net_worth_data']['auto_email'] == 'yes' and session['net_worth_data']['email']:
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
                                 'credit_card': session['net_worth_data']['credit_card'],
                                 'loans': session['net_worth_data']['loans'],
                                 'outstanding_bills': outstanding_bills,
                                 'other_debts': session['net_worth_data']['other_debts']
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
    total_assets = sum(data.get(k, 0) for k in ['cash', 'investments', 'real_estate', 'vehicles', 'business', 'other_assets'])
    total_liabilities = sum(data.get(k, 0) for k in ['credit_card', 'loans', 'other_debts']) + outstanding_bills
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
            'risk_level': form.risk_level.data,
            'dependents': form.dependents.data or 0,
            'timeline': int(form.timeline.data),
            'auto_email': form.auto_email.data
        }
        
        # Calculate emergency fund
        months = {'low': 3, 'medium': 6, 'high': 9}[session['emergency_fund_data']['risk_level']]
        months += session['emergency_fund_data']['dependents']
        target_fund = session['emergency_fund_data']['monthly_expenses'] * months
        savings_gap = target_fund - session['emergency_fund_data']['current_savings']
        monthly_savings = savings_gap / session['emergency_fund_data']['timeline'] if savings_gap > 0 else 0
        
        # Insights
        insights = [
            translations[lang]['Based on your bills, save ₦{amount}/month to reach your emergency fund goal in {months} months.'].format(
                amount=round(monthly_savings, 2),
                months=session['emergency_fund_data']['timeline']
            )
        ]
        
        # Gamification
        badge = translations[lang]['Fund Builder']
        
        # Auto-email
        if session['emergency_fund_data']['auto_email'] == 'yes' and session['emergency_fund_data']['email']:
            send_email(
                session['emergency_fund_data']['email'],
                translations[lang]['Emergency Fund Calculator'],
                'fund_email.html',
                lang,
                user_name=session['emergency_fund_data']['first_name'],
                target_fund=target_fund,
                savings_gap=savings_gap,
                monthly_savings=monthly_savings,
                timeline=session['emergency_fund_data']['timeline'],
                insights=insights,
                badge=badge
            )
        
        return render_template('emergency_fund_dashboard.html',
                             target_fund=target_fund,
                             savings_gap=savings_gap,
                             monthly_savings=monthly_savings,
                             timeline=session['emergency_fund_data']['timeline'],
                             current_savings=session['emergency_fund_data']['current_savings'],
                             insights=insights,
                             badge=badge,
                             translations=translations[lang])
    
    form.monthly_expenses.data = monthly_expenses if monthly_expenses > 0 else None
    return render_template('emergency_fund_form.html',
                          form=form,
                          step=step,
                          translations=translations[lang])

@app.route('/emergency_fund_share', methods=['POST'])
def emergency_fund_share():
    lang = session.get('language', 'en')
    email = request.form.get('email')
    if not email:
        flash(translations[lang]['Enter your email'], 'danger')
        return redirect(url_for('emergency_fund'))
    
    data = session.get('emergency_fund_data', {})
    months = {'low': 3, 'medium': 6, 'high': 9}[data.get('risk_level', 'medium')]
    months += data.get('dependents', 0)
    target_fund = data.get('monthly_expenses', 0) * months
    savings_gap = target_fund - data.get('current_savings', 0)
    monthly_savings = savings_gap / data.get('timeline', 12) if savings_gap > 0 else 0
    insights = [
        translations[lang]['Based on your bills, save ₦{amount}/month to reach your emergency fund goal in {months} months.'].format(
            amount=round(monthly_savings, 2),
            months=data.get('timeline', 12)
        )
    ]
    badge = translations[lang]['Fund Builder']
    
    if send_email(
        email,
        translations[lang]['Emergency Fund Calculator'],
        'fund_email.html',
        lang,
        user_name=data.get('first_name', 'User'),
        target_fund=target_fund,
        savings_gap=savings_gap,
        monthly_savings=monthly_savings,
        timeline=data.get('timeline', 12),
        insights=insights,
        badge=badge
    ):
        flash(translations[lang]['Share Results'], 'success')
    else:
        flash(translations[lang]['Error sending email'], 'danger')
    
    return redirect(url_for('emergency_fund'))

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
    send_email(email, translations[lang]['Bill Reminder'], 'reminder_email.html', lang,
               user_name=user_name, bill=bill)
    flash(translations[lang]['Test email sent'], 'success')
    return redirect(url_for('view_edit_bills'))

# Initialize scheduler
reload_scheduled_jobs()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
