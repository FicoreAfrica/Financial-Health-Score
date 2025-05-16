from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SelectField, DateField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, NumberRange
from flask_session import Session
import json
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables from .env file (local development)
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'ficore-africa-secret-key')
app.config['SESSION_TYPE'] = 'filesystem'  # Server-side session storage
app.config['SESSION_FILE_DIR'] = os.path.join(app.instance_path, 'sessions')
app.config['SESSION_PERMANENT'] = False
Session(app)

DATA_FILE = 'bills.json'

# Ensure instance and sessions directories exist
os.makedirs(app.instance_path, exist_ok=True)
os.makedirs(os.path.join(app.instance_path, 'sessions'), exist_ok=True)

# Translations for English and Hausa
translations = {
    'en': {
        'Bill Planner': 'Bill Planner',
        'Financial growth passport for Africa': 'Financial growth passport for Africa',
        'Plan and manage your upcoming bills to avoid surprises.': 'Plan and manage your upcoming bills to avoid surprises.',
        'Enter your first name': 'Enter your first name',
        'Enter your first name to personalize your results.': 'Enter your first name to personalize your results.',
        'Looks good!': 'Looks good!',
        'First Name Required': 'First Name Required',
        'Enter your email': 'Enter your email',
        'Provide your email address to receive your results and personalized tips.': 'Provide your email address to receive your results and personalized tips.',
        'Invalid Email': 'Invalid Email',
        'Choose your preferred language for the planner.': 'Choose your preferred language for the planner.',
        'Language selected!': 'Language selected!',
        'Language required': 'Language required',
        'Add or edit your bills': 'Add or edit your bills',
        'Click Here': 'Click Here',
        'View Your Bill Summary': 'View Your Bill Summary',
        'Loading your bill summary...': 'Loading your bill summary...',
        'Home': 'Home',
        'Add/Edit Bill': 'Add/Edit Bill',
        'Contact Us': 'Contact Us',
        'Click to Email': 'Click to Email',
        'for support': 'for support',
        'Provide Feedback': 'Provide Feedback',
        'What is this bill for?': 'What is this bill for?',
        'Description required': 'Description required',
        'How much is the bill? Enter in Naira (₦).': 'How much is the bill? Enter in Naira (₦).',
        'Amount required': 'Amount required',
        'When is this bill due?': 'When is this bill due?',
        'Due date required': 'Due date required',
        'Choose the type of bill.': 'Choose the type of bill.',
        'Category selected!': 'Category selected!',
        'Category required': 'Category required',
        'How often does this bill occur?': 'How often does this bill occur?',
        'Recurrence selected!': 'Recurrence selected!',
        'Recurrence required': 'Recurrence required',
        'Check to receive email reminders for this bill.': 'Check to receive email reminders for this bill.',
        'Select a bill to edit or create a new one.': 'Select a bill to edit or create a new one.',
        'Save Bill': 'Save Bill',
        'Saving your bill...': 'Saving your bill...',
        'Your Bills': 'Your Bills',
        'Description': 'Description',
        'Amount': 'Amount',
        'Due Date': 'Due Date',
        'Status': 'Status',
        'Edit': 'Edit',
        'Dear': 'Dear',
        'This is a reminder about your upcoming or overdue bills.': 'This is a reminder about your upcoming or overdue bills.',
        'Please review the following bills': 'Please review the following bills',
        'Due': 'Due',
        'Pay on time to avoid late fees.': 'Pay on time to avoid late fees.',
        'Manage your bills now': 'Manage your bills now',
        'Go to Bill Planner': 'Go to Bill Planner',
        'Please provide feedback on your experience': 'Please provide feedback on your experience',
        'Feedback Form': 'Feedback Form',
        'Want Smart Insights? Join our waitlist': 'Want Smart Insights? Join our waitlist',
        'Join Waitlist': 'Join Waitlist',
        'Need expert advice? Book a consultancy': 'Need expert advice? Book a consultancy',
        'Book Consultancy': 'Book Consultancy',
        'Thank you for choosing Ficore Africa': 'Thank you for choosing Ficore Africa',
        'Pending': 'Pending',
        'Overdue': 'Overdue',
        'Paid': 'Paid',
        'Use mobile money for timely rent payments to avoid late fees.': 'Use mobile money for timely rent payments to avoid late fees.',
        'Switch to energy-efficient utilities to reduce bills.': 'Switch to energy-efficient utilities to reduce bills.',
        'Plan recurring bills to manage cash flow effectively.': 'Plan recurring bills to manage cash flow effectively.',
        'Your Financial Insights': 'Your Financial Insights',
        'Bill Categories': 'Bill Categories'
    },
    'ha': {
        'Bill Planner': 'Mai Tsara Kuɗi',
        'Financial growth passport for Africa': 'Fasfo na ci gaban kuɗi don Afirka',
        'Plan and manage your upcoming bills to avoid surprises.': 'Tsara kuma sarrafa kuɗin ku masu zuwa don guje wa abubuwan mamaki.',
        'Enter your first name': 'Shigar da sunanka na farko',
        'Enter your first name to personalize your results.': 'Shigar da sunanka na farko don keɓance sakamakonka.',
        'Looks good!': 'Yayi kyau!',
        'First Name Required': 'Ana buƙatar sunan farko',
        'Enter your email': 'Shigar da imel ɗinka',
        'Provide your email address to receive your results and personalized tips.': 'Bayar da adireshin imel ɗinka don karɓar sakamakonka da shawarwari na keɓance.',
        'Invalid Email': 'Imel mara inganci',
        'Choose your preferred language for the planner.': 'Zaɓi yaren da kake so don mai tsara.',
        'Language selected!': 'An zaɓi yare!',
        'Language required': 'Ana buƙatar yare',
        'Add or edit your bills': 'Ƙara ko gyara kuɗin ka',
        'Click Here': 'Danna Nan',
        'View Your Bill Summary': 'Duba Taƙaitaccen Kuɗin Ka',
        'Loading your bill summary...': 'Ana loda taƙaitaccen kuɗin ka...',
        'Home': 'Gida',
        'Add/Edit Bill': 'Ƙara/Gyara Kuɗi',
        'Contact Us': 'Tuntube Mu',
        'Click to Email': 'Danna don Imel',
        'for support': 'don tallafi',
        'Provide Feedback': 'Bayar da Ra\'ayi',
        'What is this bill for?': 'Wannan kuɗin na me ne?',
        'Description required': 'Ana buƙatar bayanin',
        'How much is the bill? Enter in Naira (₦).': 'Nawa ne kuɗin? Shigar da cikin Naira (₦).',
        'Amount required': 'Ana buƙatar adadin',
        'When is this bill due?': 'Yaushe ne wannan kuɗin zai kare?',
        'Due date required': 'Ana buƙatar ranar karewa',
        'Choose the type of bill.': 'Zaɓi nau\'in kuɗin.',
        'Category selected!': 'An zaɓi rukunin!',
        'Category required': 'Ana buƙatar rukunin',
        'How often does this bill occur?': 'Sau nawa wannan kuɗin yake faruwa?',
        'Recurrence selected!': 'An zaɓi maimaitawa!',
        'Recurrence required': 'Ana buƙatar maimaitawa',
        'Check to receive email reminders for this bill.': 'Duba don karɓar tunatarwa ta imel don wannan kuɗin.',
        'Select a bill to edit or create a new one.': 'Zaɓi kuɗi don gyara ko ƙirƙiri sabo.',
        'Save Bill': 'Ajiye Kuɗi',
        'Saving your bill...': 'Ana ajiye kuɗin ka...',
        'Your Bills': 'Kuɗin Ka',
        'Description': 'Bayanin',
        'Amount': 'Adadin',
        'Due Date': 'Ranar Karewa',
        'Status': 'Matsayi',
        'Edit': 'Gyara',
        'Dear': 'Masoyi',
        'This is a reminder about your upcoming or overdue bills.': 'Wannan tunatarwa ne game da kuɗin ka masu zuwa ko waɗanda suka wuce.',
        'Please review the following bills': 'Da fatan za a duba kuɗin masu zuwa',
        'Due': 'Karewa',
        'Pay on time to avoid late fees.': 'Biya a kan lokaci don guje wa jaruman jinkiri.',
        'Manage your bills now': 'Sarrafa kuɗin ka yanzu',
        'Go to Bill Planner': 'Je zuwa Mai Tsara Kuɗi',
        'Please provide feedback on your experience': 'Da fatan za a bayar da ra\'ayi kan ƙwarewarka',
        'Feedback Form': 'Fom ɗin Ra\'ayi',
        'Want Smart Insights? Join our waitlist': 'Kana son Fahimta Mai Wayo? Shiga jerin jirona',
        'Join Waitlist': 'Shiga Jerin Jirona',
        'Need expert advice? Book a consultancy': 'Kana buƙatar shawarar ƙwararru? Yi ajiyar shawara',
        'Book Consultancy': 'Yi Ajiyar Shawara',
        'Thank you for choosing Ficore Africa': 'Na godiya da zabar Ficore Afirka',
        'Pending': 'A Jiran',
        'Overdue': 'Ya Wuce',
        'Paid': 'An Biya',
        'Use mobile money for timely rent payments to avoid late fees.': 'Amfani da kuɗin wayar hannu don biyan hayar lokaci don guje wa jaruman jinkiri.',
        'Switch to energy-efficient utilities to reduce bills.': 'Canja zuwa kayan aiki masu amfani da makamashi don rage kuɗin.',
        'Plan recurring bills to manage cash flow effectively.': 'Tsara kuɗin maimaitawa don sarrafa kwararar kuɗi yadda ya kamata.',
        'Your Financial Insights': 'Fahimtar Kuɗin Ka',
        'Bill Categories': 'Rukunin Kuɗi'
    }
}

# WTForms for bill planner form
class BillForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    language = SelectField('Language', choices=[('en', 'English'), ('ha', 'Hausa')], validators=[DataRequired()])
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
    send_email = BooleanField('Send Email Reminders')
    record_id = StringField('Record ID')  # For editing existing bills
    submit = SubmitField('Save Bill')

# Load bills from JSON file
def load_bills():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading bills: {e}")
            return []
    return []

# Save bills to JSON file
def save_bills(bills):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(bills, f, indent=4)
    except Exception as e:
        print(f"Error saving bills: {e}")

# Send email reminder
def send_email_reminder(to_email, user_name, bills, lang):
    msg = MIMEMultipart()
    msg['From'] = os.environ.get('EMAIL_USER', 'your_email@gmail.com')
    msg['To'] = to_email
    msg['Subject'] = translations[lang]['Bill Payment Reminder']
    
    # Render email template
    html = render_template('bill_reminder_email.html', 
                         user_name=user_name, 
                         bills=bills, 
                         translations=translations[lang])
    msg.attach(MIMEText(html, 'html'))
    
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(msg['From'], os.environ.get('EMAIL_PASSWORD', 'your_app_password'))
            server.sendmail(msg['From'], msg['To'], msg.as_string())
    except Exception as e:
        print(f"Email sending failed: {e}")

@app.route('/', methods=['GET', 'POST'])
def bill_planner_form():
    form = BillForm()
    lang = session.get('language', 'en')
    
    if form.validate_on_submit():
        session['first_name'] = form.first_name.data
        session['email'] = form.email.data
        session['language'] = form.language.data
        flash(translations[lang]['Looks good!'], 'success')
        return redirect(url_for('bill_planner_dashboard'))
    
    return render_template('bill_planner_form.html', 
                         form=form, 
                         translations=translations[lang])

@app.route('/dashboard', methods=['GET', 'POST'])
def bill_planner_dashboard():
    form = BillForm()
    lang = session.get('language', 'en')
    email = session.get('email')
    user_name = session.get('first_name', 'User')
    
    bills = load_bills()
    if not bills:
        bills = []
    
    if form.validate_on_submit():
        bill = {
            'Description': form.description.data,
            'Amount': form.amount.data,
            'DueDate': form.due_date.data.strftime('%Y-%m-%d'),
            'Category': form.category.data,
            'Recurrence': form.recurrence.data,
            'Status': 'Pending',
            'SendEmail': form.send_email.data,
            'Email': form.email.data,
            'PaymentHistory': []
        }
        
        record_id = form.record_id.data
        if record_id:  # Editing existing bill
            for i, b in enumerate(bills):
                if b.get('RecordID') == record_id:
                    bills[i] = bill
                    bills[i]['RecordID'] = record_id
                    break
        else:  # New bill
            bill['RecordID'] = str(len(bills) + 1)  # Simple ID generation
            bills.append(bill)
        
        save_bills(bills)
        flash(translations[lang]['Saving your bill...'], 'success')
        
        # Send email reminder if checked
        if form.send_email.data:
            send_email_reminder(form.email.data, user_name, [bill], lang)
        
        return redirect(url_for('bill_planner_dashboard'))
    
    # Update bill statuses
    today = datetime.now().date()
    for bill in bills:
        try:
            due_date = datetime.strptime(bill['DueDate'], '%Y-%m-%d').date()
            if bill['Status'] != 'Paid':
                bill['Status'] = 'Overdue' if due_date < today else 'Pending'
        except ValueError:
            print(f"Invalid due date format for bill: {bill['Description']}")
    
    return render_template('bill_planner_dashboard.html', 
                         form=form, 
                         bills=bills, 
                         translations=translations[lang])

@app.route('/toggle_status/<record_id>')
def toggle_status(record_id):
    bills = load_bills()
    today = datetime.now().date().strftime('%Y-%m-%d')
    
    for bill in bills:
        if bill.get('RecordID') == record_id:
            if bill['Status'] == 'Paid':
                bill['Status'] = 'Pending'
                bill['PaymentHistory'] = [h for h in bill['PaymentHistory'] if h['Date'] != today]
            else:
                bill['Status'] = 'Paid'
                bill['PaymentHistory'].append({'Date': today, 'Amount': bill['Amount']})
            break
    
    save_bills(bills)
    return redirect(url_for('bill_planner_dashboard'))

@app.route('/share_summary')
def share_summary():
    lang = session.get('language', 'en')
    bills = load_bills()
    summary = f"{translations[lang]['Your Bills']}:\n"
    for bill in bills:
        summary += f"{bill['Description']} - ₦{bill['Amount']} ({translations[lang]['Due']}: {bill['DueDate']}, {translations[lang]['Status']}: {translations[lang][bill['Status']]})\n"
    
    # URL-encode summary for social media sharing (e.g., WhatsApp, Twitter)
    from urllib.parse import quote
    whatsapp_url = f"https://wa.me/?text={quote(summary)}"
    twitter_url = f"https://twitter.com/intent/tweet?text={quote(summary)}"
    
    return render_template('bill_planner_dashboard.html', 
                         form=BillForm(), 
                         bills=bills, 
                         translations=translations[lang], 
                         whatsapp_url=whatsapp_url, 
                         twitter_url=twitter_url)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
