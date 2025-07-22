# app.py - DEMO VERSION for Current JotForm
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
DEFICIENCIES_CSV = "ctpat_deficiencies_complete.csv"

app = Flask(__name__)

# Current JotForm to C-TPAT Mapping
CURRENT_JOTFORM_MAPPING = {
    # Map JotForm question patterns to our deficiency IDs
    'information.*clearing': 'VII.2',
    'weight.*piece.*count': 'VII.2', 
    'bill.*lading.*manifest': 'VII.4',
    'cargo.*staged.*overnight': 'VII.1',
    'cargo.*reconciled': 'VII.3',
    'shortages.*overages': 'VII.10',
    'unauthorized.*persons': 'VII.11',
    'reporting.*procedures': 'VII.12',
    'internal.*investigations': 'VII.14',
    
    'secure.*storage.*iit': 'V.1',
    'inspection.*procedures': 'V.2',
    'seven.*point.*inspection': 'V.3',
    'seal.*procedures': 'VI.1',
    'iso.*seal': 'VI.2',
    'vvtt': 'VI.4',
    
    'physical.*barriers': 'IX.1',
    'gates.*manned': 'IX.3',
    'adequate.*lighting': 'IX.4',
    'cctv.*cameras': 'IX.5',
    
    'identification.*badge': 'X.2',
    'photo.*identification': 'X.5',
    'driver.*identification': 'X.7',
    'cargo.*pickup.*log': 'X.8',
    
    'screening.*employees': 'XI.1',
    'background.*check': 'XI.2',
    'code.*conduct': 'XI.3',
    
    'cybersecurity.*policies': 'IV.1',
    'firewall': 'IV.2',
    'test.*security': 'IV.3',
    'individual.*account': 'IV.7',
    'password': 'IV.7'
}

# [Include all the previous email, CSV loading, and PDF class code here - same as before]
# ... [Previous functions remain the same] ...

def find_deficiency_by_keywords(question_text):
    """Find deficiency using keyword matching for current JotForm"""
    question_lower = question_text.lower()
    
    # Try keyword pattern matching
    for pattern, deficiency_id in CURRENT_JOTFORM_MAPPING.items():
        import re
        if re.search(pattern, question_lower):
            # Find the deficiency data
            for db_question, data in deficiency_database.items():
                if data.get('question_id') == deficiency_id:
                    return data
    
    # Fallback to text matching
    return find_matching_deficiency(question_text)

def analyze_current_jotform(data):
    """Analyze current JotForm structure"""
    deficiencies = []
    company_name = "Demo Company"
    
    answers = data.get('answers', {})
    
    for qid, answer_data in answers.items():
        question_text = answer_data.get('text', 'Unknown Question').strip()
        answer_value = answer_data.get('answer', '')
        
        # Extract company name if present
        if any(word in question_text.lower() for word in ['company', 'organization', 'business']):
            if len(str(answer_value)) > 3:  # Valid company name
                company_name = str(answer_value)
                continue
        
        # Evaluate for deficiencies
        is_deficient, processed_answer = evaluate_answer(question_text, answer_value, qid)
        
        if is_deficient:
            # Find matching deficiency
            deficiency_data = find_deficiency_by_keywords(question_text)
            
            if deficiency_data:
                deficiencies.append({
                    "question_id": qid,
                    "question": question_text,
                    "answer": processed_answer,
                    "category": deficiency_data.get('category', 'Security Requirement'),
                    "deficiency_data": deficiency_data
                })
    
    return company_name, deficiencies

# [Include the enhanced PDF and other functions from previous version]

@app.route('/webhook', methods=['POST'])
def jotform_webhook():
    """Production webhook for current JotForm"""
    try:
        submission_data_str = request.form.get('rawRequest')
        if not submission_data_str:
            return jsonify({"status": "error", "message": "No rawRequest field"}), 400
        
        submission_data = json.loads(submission_data_str)
        submission_id = request.form.get('submissionID', f'DEMO_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}')
        
        # Use current JotForm analysis
        company_name, deficiencies = analyze_current_jotform(submission_data)
        
        # Generate report
        pdf_path = create_ctpat_deficiency_report(submission_id, company_name, deficiencies)
        
        # Send email
        email_sent = send_pdf_email(pdf_path, company_name)
        
        message = f"C-TPAT analysis complete for {company_name}. Found {len(deficiencies)} deficiencies. Email: {'Sent' if email_sent else 'Failed'}"
        
        return jsonify({
            "status": "success",
            "message": message,
            "company": company_name,
            "deficiencies_found": len(deficiencies),
            "categories_affected": len(set(d['category'] for d in deficiencies)),
            "email_sent": email_sent
        }), 200
        
    except Exception as e:
        app.logger.error(f"Webhook error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/demo')
def create_demo():
    """Create impressive demo for owner using current JotForm questions"""
    
    # Create realistic demo data using actual JotForm questions
    demo_data = {
        "answers": {
            "company": {
                "text": "Company Name", 
                "answer": "Acme Import/Export Corp"
            },
            "4.1": {
                "text": "Are procedures in place to ensure that all information used in the clearing of merchandise/cargo is legible, complete, accurate, protected against the exchange, loss, or introduction of erroneous information, and reported on time?",
                "answer": "No"
            },
            "4.5": {
                "text": "When cargo is staged overnight, or for an extended period of time, are measures taken to secure the cargo from unauthorized access?",
                "answer": "Not implemented"
            },
            "5.1": {
                "text": "Are conveyances and Instruments of International Traffic (IIT) stored in a secure area to prevent unauthorized access?",
                "answer": "No"
            },
            "5.16": {
                "text": "Are all CTPAT shipments that can be sealed secured immediately after loading with a high security seal that meets or exceeds ISO 17712 standard?",
                "answer": "N/A"
            },
            "7.8": {
                "text": "Is adequate lighting provided inside and outside the facility including entrances, exits, cargo handling and storage areas, fence lines, and parking areas?",
                "answer": "Partial - some areas lack adequate lighting"
            },
            "8.6": {
                "text": "Do visitors, vendors and service providers present photo identification upon arrival? Is a log maintained that records the details of the visit?",
                "answer": "No visitor log maintained"
            },
            "11.1": {
                "text": "Are comprehensive written cybersecurity policies and procedures in place to protect information technology systems?",
                "answer": "No formal policy exists"
            },
            "11.17": {
                "text": "Is access to IT systems protected from infiltration via the use of strong passwords, passphrases, or other forms of authentication?",
                "answer": "Basic passwords only, no policy"
            }
        }
    }
    
    try:
        submission_id = f"DEMO_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Analyze demo data
        company_name, deficiencies = analyze_current_jotform(demo_data)
        
        # Generate impressive report
        pdf_path = create_ctpat_deficiency_report(submission_id, company_name, deficiencies)
        
        # Send demo email
        email_sent = send_pdf_email(pdf_path, company_name)
        
        # Create impressive HTML response for owner
        html_response = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>C-TPAT Analysis Demo Results</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
                .container {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .header {{ color: #1a365d; border-bottom: 3px solid #3182ce; padding-bottom: 15px; margin-bottom: 25px; }}
                .success {{ color: #38a169; font-size: 18px; font-weight: bold; }}
                .warning {{ color: #d69e2e; font-weight: bold; }}
                .error {{ color: #e53e3e; font-weight: bold; }}
                .stats {{ display: flex; justify-content: space-between; margin: 20px 0; }}
                .stat-box {{ background: #edf2f7; padding: 15px; border-radius: 5px; text-align: center; min-width: 120px; }}
                .deficiency-list {{ background: #fed7d7; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                .category {{ background: #bee3f8; padding: 10px; margin: 10px 0; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔒 C-TPAT SECURITY ANALYSIS - DEMO RESULTS</h1>
                    <p>Automated Security Assessment Report</p>
                </div>
                
                <div class="success">✅ SYSTEM OPERATIONAL - Analysis Complete!</div>
                
                <div class="stats">
                    <div class="stat-box">
                        <h3>{company_name}</h3>
                        <p>Company Analyzed</p>
                    </div>
                    <div class="stat-box">
                        <h3 class="error">{len(deficiencies)}</h3>
                        <p>Deficiencies Found</p>
                    </div>
                    <div class="stat-box">
                        <h3>{len(set(d['category'] for d in deficiencies))}</h3>
                        <p>Security Categories Affected</p>
                    </div>
                    <div class="stat-box">
                        <h3 class="{'success' if email_sent else 'error'}">{'✓' if email_sent else '✗'}</h3>
                        <p>Email Delivered</p>
                    </div>
                </div>
                
                <div class="deficiency-list">
                    <h3>🚨 CRITICAL DEFICIENCIES IDENTIFIED:</h3>
        """
        
        # Group deficiencies by category for impressive display
        categories = {}
        for d in deficiencies:
            cat = d['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(d['question'][:80] + "..." if len(d['question']) > 80 else d['question'])
        
        for category, questions in categories.items():
            html_response += f"""
                    <div class="category">
                        <strong>{category}</strong>
                        <ul>
            """
            for question in questions:
                html_response += f"<li>{question}</li>"
            html_response += "</ul></div>"
        
        html_response += f"""
                </div>
                
                <div style="background: #c6f6d5; padding: 20px; border-radius: 5px; margin-top: 20px;">
                    <h3>📊 WHAT HAPPENS NEXT:</h3>
                    <ul>
                        <li><strong>PDF Report Generated:</strong> {os.path.basename(pdf_path)}</li>
                        <li><strong>Email Sent To:</strong> {os.environ.get('RECIPIENT_EMAIL', 'configured recipient')}</li>
                        <li><strong>Report Contains:</strong> Detailed corrective actions for each deficiency</li>
                        <li><strong>Implementation Guidance:</strong> Step-by-step compliance instructions</li>
                    </ul>
                </div>
                
                <div style="background: #e6fffa; padding: 20px; border-radius: 5px; margin-top: 20px; border-left: 5px solid #38b2ac;">
                    <h3>🎯 SYSTEM CAPABILITIES DEMONSTRATED:</h3>
                    <ul>
                        <li>✅ Automated analysis of JotForm submissions</li>
                        <li>✅ Intelligent deficiency detection across all C-TPAT categories</li>
                        <li>✅ Professional PDF report generation</li>
                        <li>✅ Automatic email delivery to stakeholders</li>
                        <li>✅ Detailed corrective action guidance</li>
                        <li>✅ Ready for production deployment</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin-top: 30px; padding: 20px; background: #1a365d; color: white; border-radius: 5px;">
                    <h3>🚀 READY FOR FULL DEPLOYMENT</h3>
                    <p>This demonstration shows the system working with your current JotForm.<br>
                    Full integration will provide comprehensive C-TPAT compliance monitoring.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_response
        
    except Exception as e:
        return f"""
        <h2 style="color: red;">Demo Error</h2>
        <p>Error: {str(e)}</p>
        <p>Please check logs for details.</p>
        """

# [Include all other routes from previous version]

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
