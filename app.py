# app.py (version with email sending and test route)
import os
import json
import datetime
import csv
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, request, jsonify
from fpdf import FPDF

# --- Configuration ---
PDF_OUTPUT_DIR = "generated_reports"
RECOMMENDATIONS_CSV = "SOD - All Deficiencies - Thomas.xlsx - Sheet1.csv"

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Email Sending Function ---
def send_pdf_email(pdf_path, company_name):
    """Sends the generated PDF as an email attachment."""
    # Fetch email configuration securely from environment variables
    sender_email = os.environ.get('SENDER_EMAIL')
    sender_password = os.environ.get('SENDER_PASSWORD')
    recipient_email = os.environ.get('RECIPIENT_EMAIL')

    if not all([sender_email, sender_password, recipient_email]):
        app.logger.error("Email configuration is missing. Cannot send email.")
        return False

    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = f"C-TPAT Deficiency Report for {company_name}"

    body = "Please find the C-TPAT Summary of Deficiencies attached."
    msg.attach(MIMEText(body, 'plain'))

    # Attach the PDF file
    try:
        with open(pdf_path, "rb") as f:
            attach = MIMEApplication(f.read(), _subtype="pdf")
        attach.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
        msg.attach(attach)
    except FileNotFoundError:
        app.logger.error(f"Could not find PDF file at {pdf_path} to attach.")
        return False

    # Send the email using Gmail's SMTP server
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        app.logger.info(f"Email sent successfully to {recipient_email}")
        return True
    except Exception as e:
        app.logger.error(f"Failed to send email: {e}")
        return False

# --- Data Loading ---
def load_recommendations(file_path):
    recommendation_map = {}
    if not os.path.exists(file_path):
        app.logger.error(f"FATAL: Recommendations CSV not found at '{file_path}'")
        return {}
    try:
        with open(file_path, mode='r', encoding='utf-8') as infile:
            reader = csv.reader(infile)
            header_found = False
            question_col_idx, action_col_idx = -1, -1
            for header in reader:
                try:
                    question_col_idx = header.index('Question/Deficiency')
                    action_col_idx = header.index('Recommended Action')
                    header_found = True
                    break
                except ValueError:
                    continue
            if not header_found:
                app.logger.error("FATAL: Could not find required headers in CSV.")
                return {}
            for row in reader:
                if len(row) > max(question_col_idx, action_col_idx):
                    question = row[question_col_idx].strip()
                    action = row[action_col_idx].strip()
                    if question:
                        recommendation_map[question] = action
    except Exception as e:
        app.logger.error(f"An error occurred while loading the recommendations CSV: {e}")
        return {}
    return recommendation_map

recommendation_map = load_recommendations(RECOMMENDATIONS_CSV)


# --- PDF Generation Class ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'C-TPAT Summary of Deficiencies & Recommended Actions', 0, 1, 'C')
        self.ln(10)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(5)
    def add_deficiency(self, question, answer, recommendation):
        self.set_font('Arial', 'B', 11)
        self.multi_cell(0, 7, f"Deficiency: {question}")
        self.set_font('Arial', 'I', 10)
        self.set_text_color(255, 0, 0)
        self.multi_cell(0, 7, f"Answer: {answer}")
        self.set_font('Arial', 'B', 10)
        self.set_text_color(0, 0, 0)
        self.multi_cell(0, 7, "Recommended Action:")
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 6, recommendation)
        self.ln(6)

# --- Core Functions ---
def analyze_submission(data):
    deficiencies = []
    company_name = "N/A"
    answers = data.get('answers', {})
    for qid, answer_data in answers.items():
        question_text = answer_data.get('text', 'Unknown Question').strip()
        answer_value = answer_data.get('answer', '')
        if qid == '4':
            company_name = answer_data.get('answer', "N/A")
        if isinstance(answer_value, str) and answer_value.lower() == 'no':
            deficiencies.append({"question": question_text, "answer": answer_value})
    return company_name, deficiencies

def create_deficiency_report(submission_id, company_name, deficiencies, recommendations):
    if not os.path.exists(PDF_OUTPUT_DIR):
        os.makedirs(PDF_OUTPUT_DIR)
    pdf = PDF()
    pdf.add_page()
    pdf.chapter_title(f"Company: {company_name}")
    pdf.chapter_title(f"Submission ID: {submission_id}")
    report_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pdf.chapter_title(f"Report Date: {report_date}")
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
    pdf.ln(10)
    if deficiencies:
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, f"Found {len(deficiencies)} Deficiencies", 0, 1, 'L')
        pdf.ln(5)
        for item in deficiencies:
            recommendation = recommendations.get(item['question'], "No specific recommendation was found in the provided CSV file.")
            pdf.add_deficiency(item['question'], item['answer'], recommendation)
    else:
        pdf.set_font('Arial', 'B', 14)
        pdf.set_text_color(0, 128, 0)
        pdf.cell(0, 10, "No Deficiencies Found.", 0, 1, 'L')
        pdf.set_text_color(0, 0, 0)
    file_path = os.path.join(PDF_OUTPUT_DIR, f"deficiency_report_{submission_id}.pdf")
    pdf.output(file_path)
    return file_path

# --- Main Webhook Endpoint ---
@app.route('/webhook', methods=['POST'])
def jotform_webhook():
    try:
        submission_data_str = request.form.get('rawRequest')
        if not submission_data_str:
            return jsonify({"status": "error", "message": "No rawRequest field"}), 400
        
        submission_data = json.loads(submission_data_str)
        submission_id = request.form.get('submissionID', 'UNKNOWN_SID')
        app.logger.info(f"Received submission {submission_id}")
        company_name, deficiencies = analyze_submission(submission_data)
        pdf_path = create_deficiency_report(submission_id, company_name, deficiencies, recommendation_map)
        email_sent = send_pdf_email(pdf_path, company_name)
        message = f"Report generated. Email status: {'Success' if email_sent else 'Failed'}"
        return jsonify({"status": "success", "message": message}), 200
    except Exception as e:
        app.logger.error(f"An unhandled error occurred: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

# --- NEW: Test Route ---
@app.route('/test')
def test_email():
    """Generates a sample report from dummy data and emails it."""
    app.logger.info("--- Running Test ---")
    
    # 1. Create dummy data that mimics a Jotform submission
    dummy_submission_id = "DUMMY_TEST_001"
    dummy_data = {
        "answers": {
            "4": {
                "text": "Company Name",
                "answer": "Test Company Inc."
            },
            "5": {
                "text": "Are background checks performed?",
                "answer": "Yes"
            },
            "6": {
                "text": "Is there a documented seal security program?",
                "answer": "No"
            },
            "7": {
                "text": "Are shipping manifests verified against cargo?",
                "answer": "No"
            }
        }
    }
    
    # 2. Process the dummy data
    company_name, deficiencies = analyze_submission(dummy_data)
    if not deficiencies:
        return "Test ran, but no deficiencies were found in the dummy data."
        
    app.logger.info(f"Test Company: {company_name}, Deficiencies found: {len(deficiencies)}")
    
    # 3. Create the PDF report
    pdf_path = create_deficiency_report(dummy_submission_id, company_name, deficiencies, recommendation_map)
    app.logger.info(f"Test PDF generated: {pdf_path}")
    
    # 4. Email the PDF
    email_sent = send_pdf_email(pdf_path, company_name)
    
    # 5. Return a message to the browser
    message = f"Test complete. Report for '{company_name}' generated. Email status: {'Success' if email_sent else 'Failed'}"
    return message

# --- Root URL ---
@app.route('/')
def index():
    return "Jotform PDF Generator with Email is running."

# This part is used for local testing but not by Render's gunicorn server
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
