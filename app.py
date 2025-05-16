from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SelectField, DateField, BooleanField, SubmitField, SelectMultipleField
from wtforms.validators import DataRequired, Email, NumberRange
from flask_session import Session
import json
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger

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
        'Back': 'Back',
        'Go to Dashboard': 'Go to Dashboard',
        'Dashboard': 'Dashboard',
        'Unpaid Bills': 'Unpaid Bills',
        'Total Bills': 'Total Bills',
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
        'Thank you for using Ficore Africa': 'Thank you for using Ficore Africa'
    },
    'ha': {
        'Bill Planner': 'Mai Tsara Kuɗi',
        'Financial growth passport for Africa': 'Fasfo na ci gaban kuɗi don Afirka',
        'Enter your first name': 'Shigar da sunanka na farko',
        'Enter your email': 'Shigar da imel ɗinka',
        'Choose your language': 'Zaɓi yarenka',
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
        'Back': 'Koma baya',
        'Go to Dashboard': 'Je zuwa Dashboard',
        'Dashboard': 'Dashboard',
        'Unpaid Bills': 'Kuɗin da ba a biya ba',
        'Total Bills': 'Jimlar Kuɗi',
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
        'Thank you for using Ficore Africa': 'Na godiya da amfani da Ficore Afirka'
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
            print(f"Error loading bills: {e}")
            return []
    return []

def save_bills(bills):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(bills, f, indent=4)
    except Exception as e:
        print(f"Error saving bills: {e}")

# Email reminder
def send_email_reminder(to_email, user_name, bill, lang, reminder_type):
    msg = MIMEMultipart()
    msg['From'] = os.environ.get('EMAIL_USER', 'your_email@gmail.com')
    msg['To'] = to_email
    msg['Subject'] = translations[lang]['Bill Reminder']
    
    reminder_text = {
        '3_days': '3 days before due date',
        '1_day': '1 day before due date',
        'due_date': 'on due date'
    }[reminder_type]
    
    html = render_template('reminder_email.html',
                         user_name=user_name,
                         bill=bill,
                         reminder_text=reminder_text,
                         translations=translations[lang])
    msg.attach(MIMEText(html, 'html'))
    
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(msg['From'], os.environ.get('EMAIL_PASSWORD', 'your_app_password'))
            server.sendmail(msg['From'], msg['To'], msg.as_string())
    except Exception as e:
        print(f"Email sending failed: {e}")

# Scheduler for reminders
scheduler = BackgroundScheduler()
scheduler.start()

def schedule_reminders(bill, email, user_name, lang):
    due_date = datetime.strptime(bill['DueDate'], '%Y-%m-%d')
    for reminder in bill.get('Reminders', []):
        if reminder == '3_days':
            send_date = due_date - timedelta(days=3)
        elif reminder == '1_day':
            send_date = due_date - timedelta(days=1)
        else:  # due_date
            send_date = due_date
        
        if send_date >= datetime.now():
            scheduler.add_job(
                send_email_reminder,
                trigger=DateTrigger(run_date=send_date),
                args=[email, user_name, bill, lang, reminder],
                id=f"bill_{bill['RecordID']}_{reminder}"
            )

# Routes
@app.route('/', methods=['GET', 'POST'])
def fill_form():
    form = UserForm()
    lang = session.get('language', 'en')
    
    if form.validate_on_submit():
        session['first_name'] = form.first_name.data
        session['email'] = form.email.data
        session['language'] = form.language.data
        return redirect(url_for('view_edit_bills'))
    
    return render_template('bill_form.html',
                         form=form,
                         translations=translations[lang])

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
        bill = {
            'Description': form.description.data,
            'Amount': form.amount.data,
            'DueDate': form.due_date.data.strftime('%Y-%m-%d'),
            'Category': form.category.data,
            'Recurrence': form.recurrence.data,
            'Status': form.status.data,
            'Reminders': form.reminders.data,
            'Email': email
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
            bills.append(bill)
        
        save_bills(bills)
        schedule_reminders(bill, email, user_name, lang)
        flash(translations[lang]['Save Bill'], 'success')
        return redirect(url_for('view_edit_bills', category=category))
    
    # Pre-populate form for editing
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

@app.route('/dashboard')
def dashboard():
    lang = session.get('language', 'en')
    bills = load_bills()
    
    unpaid_count = len([b for b in bills if b['Status'] == 'Unpaid'])
    total_bills = sum(b['Amount'] for b in bills)
    
    categories = {}
    for bill in bills:
        cat = bill['Category']
        categories[cat] = categories.get(cat, 0) + bill['Amount']
    
    today = datetime.now().date()
    week_end = today + timedelta(days=7)
    month_end = today.replace(day=28) + timedelta(days=4)
    
    due_today = [b for b in bills if b['DueDate'] == today.strftime('%Y-%m-%d')]
    due_week = [b for b in bills if today.strftime('%Y-%m-%d') <= b['DueDate'] <= week_end.strftime('%Y-%m-%d')]
    due_month = [b for b in bills if today.strftime('%Y-%m-%d') <= b['DueDate'] <= month_end.strftime('%Y-%m-%d')]
    
    tips = [
        translations[lang]['Pay bills early to avoid late fees. Use mobile money for quick payments.'],
        translations[lang]['Switch to energy-efficient utilities to save money.'],
        translations[lang]['Plan monthly bills to manage your budget better.']
    ]
    
    return render_template('dashboard.html',
                         unpaid_count=unpaid_count,
                         total_bills=total_bills,
                         categories=categories,
                         due_today=due_today,
                         due_week=due_week,
                         due_month=due_month,
                         tips=tips,
                         bills=bills,
                         translations=translations[lang])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
