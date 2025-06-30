from flask import Flask, request, jsonify
from fpdf import FPDF
import json
import os
import datetime
import csv

PDF_OUTPUT_DIR = "generated_reports"
RECOMMENDATIONS_CSV = "SOD - All Deficiencies - Thomas.xlsx - Sheet1.csv"

app = Flask(__name__)

# --- Data Loading ---
def load_recommendations(file_path):
    recommendation_map = {}
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
                print("ERROR: Could not find required headers in CSV.")
                return {}
            for row in reader:
                if len(row) > max(question_col_idx, action_col_idx):
                    question = row[question_col_idx].strip()
                    action = row[action_col_idx].strip()
                    if question:
                        recommendation_map[question] = action
    except FileNotFoundError:
        print(f"FATAL: The recommendations file was not found at '{file_path}'")
        return {}
    except Exception as e:
        print(f"An error occurred while loading the recommendations CSV: {e}")
        return {}
    return recommendation_map

recommendation_map = load_recommendations(RECOMMENDATIONS_CSV)
if recommendation_map:
    print(f"Successfully loaded {len(recommendation_map)} recommendations.")
else:
    print("Warning: Recommendation map is empty.")


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
            company_name = answer_value if answer_value else "N/A"
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
    pdf.ln(5)
    if deficiencies:
        for item in deficiencies:
            recommendation = recommendations.get(item['question'], "No specific recommendation was found in the provided CSV file.")
            pdf.add_deficiency(item['question'], item['answer'], recommendation)
    else:
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, "No Deficiencies Found.", 0, 1, 'L')
    file_path = os.path.join(PDF_OUTPUT_DIR, f"deficiency_report_{submission_id}.pdf")
    pdf.output(file_path)
    return file_path

@app.route('/webhook', methods=['POST'])
def jotform_webhook():
    try:
        # Jotform sends data differently, sometimes needing force=True
        submission_data = request.get_json(force=True)
        raw_request = json.loads(submission_data.get('rawRequest', '{}'))
        submission_id = submission_data.get('submissionID', 'UNKNOWN_SID')
        company_name, deficiencies = analyze_submission(raw_request)
        pdf_path = create_deficiency_report(submission_id, company_name, deficiencies, recommendation_map)
        print(f"Report generated: {pdf_path}")
        return jsonify({"status": "success", "message": f"Report generated at {pdf_path}"}), 200
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/')
def index():
    return "Jotform PDF Generator is running."

# The host and port settings are important for Replit
app.run(host='0.0.0.0', port=8080)
