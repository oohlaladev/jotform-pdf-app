# app.py (Final version with data visibility fix)
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


# --- PDF Generation Class (FIXED DESIGN) ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(25, 48, 89) # Dark Blue
        self.rect(0, 0, 210, 20, 'F')
        self.set_y(5)
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(255, 255, 255) # White
        self.cell(0, 10, 'C-TPAT Summary of Deficiencies', 0, 1, 'C')
        self.set_text_color(0, 0, 0)
        self.set_y(25)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def report_info(self, company_name, submission_id, report_date):
        self.set_font('Helvetica', 'B', 12)
        self.cell(40, 10, 'Company:', 0, 0)
        self.set_font('Helvetica', '', 12)
        self.cell(0, 10, company_name, 0, 1)

        self.set_font('Helvetica', 'B', 12)
        self.cell(40, 10, 'Submission ID:', 0, 0)
        self.set_font('Helvetica', '', 12)
        self.cell(0, 10, submission_id, 0, 1)

        self.set_font('Helvetica', 'B', 12)
        self.cell(40, 10, 'Report Date:', 0, 0)
        self.set_font('Helvetica', '', 12)
        self.cell(0, 10, report_date, 0, 1)
        self.ln(10)

    # THIS IS THE CORRECTED FUNCTION
    def add_deficiency(self, question, answer, recommendation, suggestion):
        content_width = self.w - self.l_margin - self.r_margin

        # --- Deficiency Title ---
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(40, 40, 40)
        self.multi_cell(content_width, 6, f"DEFICIENCY: {question}")
        self.ln(1)
        
        # --- Submitted Answer ---
        self.set_font('Helvetica', 'I', 10)
        self.set_text_color(200, 0, 0) # Red
        self.multi_cell(content_width, 6, f"Submitted Answer: {answer}")
        self.ln(4)
        
        # --- Recommended Action ---
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(0, 51, 102) # Dark Blue
        self.cell(content_width, 6, "Recommended Action")
        self.ln(5)
        self.set_font('Helvetica', '', 10)
        self.set_text_color(80, 80, 80)
        self.multi_cell(content_width, 5, recommendation)
        self.ln(4)

        # --- Suggested Corrective Action ---
        if suggestion and suggestion.strip() and suggestion != "N/A":
            self.set_font('Helvetica', 'B', 10)
            self.set_text_color(0, 51, 102) # Dark Blue
            self.cell(content_width, 6, "Suggested Corrective Action")
            self.ln(5)
            self.set_font('Helvetica', '', 10)
            self.set_text_color(80, 80, 80)
            self.multi_cell(content_width, 5, suggestion)
            self.ln(2)
        
        # Use a line separator instead of a background box
        self.line(self.get_x(), self.get_y(), self.get_x() + content_width, self.get_y())
        self.ln(8)

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
    
    report_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pdf.report_info(company_name, submission_id, report_date)

    if deficiencies:
        for item in deficiencies:
            rec_data = recommendations.get(item['question'], {
                "action": "No specific recommendation was found.",
                "suggestion": "N/A"
            })
            pdf.add_deficiency(item['question'], item['answer'], rec_data['action'], rec_data['suggestion'])
    else:
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(0, 128, 0) # Green
        pdf.cell(0, 10, "No Deficiencies Found.", 0, 1, 'C')

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
        company_name, deficiencies = analyze_submission(submission_data)
        pdf_path = create_deficiency_report(submission_id, company_name, deficiencies, recommendation_map)
        email_sent = send_pdf_email(pdf_path, company_name)
        message = f"Report generated. Email status: {'Success' if email_sent else 'Failed'}"
        return jsonify({"status": "success", "message": message}), 200
    except Exception as e:
        app.logger.error(f"An unhandled error occurred: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

# --- Test Route ---
@app.route('/test')
def test_email():
    dummy_submission_id = "DUMMY_TEST_001"
    dummy_data = {
        "answers": {
            "4": {"text": "Company Name", "answer": "Test Company Inc."},
            "6": {"text": "Is there a documented seal security program?", "answer": "No"},
            "7": {"text": "Are shipping manifests verified against cargo? This question is designed to be extra long to test the text wrapping functionality of the new PDF design.", "answer": "No"}
        }
    }
    
    dummy_recommendations = {
        "Is there a documented seal security program?": {
            "action": "Develop and implement a written seal security program that includes procedures for verifying the physical integrity of the seal upon affixing and receipt.",
            "suggestion": "Review the C-TPAT guidelines for high-security seals (ISO 17712). Ensure all personnel handling seals are trained on recognition of compromised seals."
        },
        "Are shipping manifests verified against cargo? This question is designed to be extra long to test the text wrapping functionality of the new PDF design.": {
            "action": "Implement a mandatory procedure to verify that all shipping documents accurately reflect the cargo being loaded. This includes bills of lading, manifests, and any other relevant transit documents.",
            "suggestion": "Consider using a two-person verification system for all outgoing shipments. This creates accountability and reduces errors. Also, implement random spot-checks by a manager."
        }
    }

    company_name, deficiencies = analyze_submission(dummy_data)
    pdf_path = create_deficiency_report(dummy_submission_id, company_name, deficiencies, dummy_recommendations)
    email_sent = send_pdf_email(pdf_path, company_name)
    
    message = f"Test complete. Report for '{company_name}' generated. Email status: {'Success' if email_sent else 'Failed'}"
    return message

# --- Root URL ---
@app.route('/')
def index():
    return "Jotform PDF Generator with Email is running."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
