# app.py (version with page layout fix)
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
    sender_email = os.environ.get('SENDER_EMAIL')
    sender_password = os.environ.get('SENDER_PASSWORD')
    recipient_email = os.environ.get('RECIPIENT_EMAIL')

    if not all([sender_email, sender_password, recipient_email]):
        app.logger.error("Email configuration is missing. Cannot send email.")
        return False

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = f"C-TPAT Deficiency Report for {company_name}"
    body = "Please find the C-TPAT Summary of Deficiencies attached."
    msg.attach(MIMEText(body, 'plain'))

    try:
        with open(pdf_path, "rb") as f:
            attach = MIMEApplication(f.read(), _subtype="pdf")
        attach.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
        msg.attach(attach)
    except FileNotFoundError:
        app.logger.error(f"Could not find PDF file at {pdf_path} to attach.")
        return False

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
            header = []
            for row in reader:
                if 'Question/Deficiency' in row and 'Recommended Action' in row:
                    header = row
                    break
            
            if not header:
                app.logger.error("FATAL: Could not find required headers in CSV.")
                return {}

            question_col_idx = header.index('Question/Deficiency')
            action_col_idx = header.index('Recommended Action')
            
            suggestion_col_idx = -1
            try:
                suggestion_col_idx = header.index('Suggested Corrective Action')
            except ValueError:
                app.logger.warning("Optional 'Suggested Corrective Action' column not found in CSV.")

            for row in reader:
                if len(row) > max(question_col_idx, action_col_idx):
                    question = row[question_col_idx].strip()
                    action = row[action_col_idx].strip()
                    suggestion = "N/A"
                    if suggestion_col_idx != -1 and len(row) > suggestion_col_idx:
                        suggestion = row[suggestion_col_idx].strip()

                    if question:
                        recommendation_map[question] = {"action": action, "suggestion": suggestion}
    except Exception as e:
        app.logger.error(f"An error occurred while loading the recommendations CSV: {e}")
        return {}
    return recommendation_map

recommendation_map = load_recommendations(RECOMMENDATIONS_CSV)


# --- PDF Generation Class (MODIFIED) ---
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
    
    # THIS FUNCTION IS UPDATED WITH THE LAYOUT FIX
    def add_deficiency(self, question, answer, recommendation, suggestion):
        # Calculate available width based on page size and margins
        page_width = self.w - self.l_margin - self.r_margin

        # Deficiency and Answer
        self.set_font('Arial', 'B', 11)
        self.multi_cell(page_width, 7, f"Deficiency: {question}")
        self.set_font('Arial', 'I', 10)
        self.set_text_color(255, 0, 0)
        self.multi_cell(page_width, 7, f"Answer: {answer}")
        self.set_text_color(0, 0, 0)
        
        # Recommended Action
        self.set_font('Arial', 'B', 10)
        self.multi_cell(page_width, 7, "Recommended Action:")
        self.set_font('Arial', '', 10)
        self.multi_cell(page_width, 6, recommendation)
        self.ln(2)

        # Suggested Corrective Action
        if suggestion and suggestion.strip() and suggestion != "N/A":
            self.set_font('Arial', 'B', 10)
            self.multi_cell(page_width, 7, "Suggested Corrective Action:")
            self.set_font('Arial', '', 10)
            self.multi_cell(page_width, 6, suggestion)

        self.ln(6)

# --- Core Functions (MODIFIED) ---
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
    if not os.path.exists
