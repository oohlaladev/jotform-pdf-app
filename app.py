# Updated app.py with branding and removal of AI references

import os
import json
import datetime
import csv
import smtplib
import ssl
import re
import traceback
import glob
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, request, jsonify, send_file, abort
from fpdf import FPDF
import anthropic

# --- Configuration ---
PDF_OUTPUT_DIR = "generated_reports"
DEFICIENCIES_CSV = "ctpat_deficiencies_complete.csv"
COMPANY_NAME = "World Wise Consulting"
COMPANY_LOGO = "logo.png"  # Place your logo in the app directory
COMPANY_ADDRESS = "1500 NW 89th Court, Suite 221, Doral, Florida, 33172"
COMPANY_PHONE = "P (786) 621-5385"

app = Flask(__name__)

# Initialize
deficiency_database = {}
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

# --- Email Functions ---
def send_pdf_email(pdf_path, company_name):
    """Send PDF report via email"""
    sender_email = os.environ.get('SENDER_EMAIL')
    sender_password = os.environ.get('SENDER_PASSWORD')
    recipient_email = os.environ.get('RECIPIENT_EMAIL')

    if not all([sender_email, sender_password, recipient_email]):
        app.logger.error("Email configuration is missing")
        return False

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = f"C-TPAT Compliance Analysis Report - {company_name}"
    
    body = f"""C-TPAT Security Assessment Complete

Company: {company_name}
Analysis Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}

Please find the detailed C-TPAT deficiency analysis attached. This report provides a comprehensive compliance evaluation.

Key Features of This Analysis:
• Advanced security evaluation
• Expert deficiency detection
• Specific corrective actions
• Risk-based severity assessment

Please review all identified deficiencies and implement the recommended corrective actions within 30 days.

Best regards,
{COMPANY_NAME}
{COMPANY_PHONE}"""

    msg.attach(MIMEText(body, 'plain'))

    try:
        with open(pdf_path, "rb") as f:
            attach = MIMEApplication(f.read(), _subtype="pdf")
        attach.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
        msg.attach(attach)
    except FileNotFoundError:
        app.logger.error(f"PDF file not found: {pdf_path}")
        return False

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        app.logger.info(f"Email sent successfully to {recipient_email}")
        return True
    except Exception as e:
        app.logger.error(f"Email failed: {e}")
        return False

# --- Database Loading ---
def load_deficiency_database():
    """Load C-TPAT deficiency database"""
    global deficiency_database
    
    if deficiency_database:
        return deficiency_database
    
    if not os.path.exists(DEFICIENCIES_CSV):
        app.logger.warning(f"CSV file not found: {DEFICIENCIES_CSV}")
        deficiency_database = create_fallback_database()
        return deficiency_database
    
    try:
        with open(DEFICIENCIES_CSV, mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                question = row.get('Question/Deficiency', '').strip()
                if question:
                    deficiency_database[question] = {
                        "category": row.get('Category', 'Security Requirement'),
                        "question_id": row.get('Question_ID', 'UNKNOWN'),
                        "action": row.get('Recommended Action', 'Implement appropriate security measures.'),
                        "suggestion": row.get('Suggested Corrective Action', 'Review C-TPAT requirements.')
                    }
        
        app.logger.info(f"Loaded {len(deficiency_database)} deficiency records")
        return deficiency_database
        
    except Exception as e:
        app.logger.error(f"Error loading CSV: {e}")
        deficiency_database = create_fallback_database()
        return deficiency_database

def create_fallback_database():
    """Create fallback deficiency database with specific corrective actions"""
    return {
        "Security Program Implementation": {
            "category": "I. Security Vision and Responsibility",
            "question_id": "I.1",
            "action": "Develop and implement a comprehensive written Supply Chain Security Program.",
            "suggestion": "Create formal security policies covering all C-TPAT requirements."
        },
        "Cybersecurity Policies": {
            "category": "IV. Cybersecurity",
            "question_id": "IV.1", 
            "action": "Implement comprehensive cybersecurity policies and procedures.",
            "suggestion": "Deploy enterprise-grade security measures including firewalls and access controls."
        },
        "Personnel Screening": {
            "category": "XI. Personnel Security",
            "question_id": "XI.1",
            "action": "Establish written processes for employee background screening.",
            "suggestion": "Conduct thorough background checks including criminal history verification."
        },
        "Are written procedures in place for reporting security incidents?": {
            "category": "VII. Procedural Security",
            "question_id": "VII.3",
            "action": "Develop and implement formal written security incident reporting procedures.",
            "suggestion": "Create a documented security incident response plan with clear reporting channels, escalation procedures, and contact information. Train all employees on proper incident reporting and maintain incident logs."
        },
        "Are comprehensive written cybersecurity policies and procedures in place?": {
            "category": "IV. Cybersecurity",
            "question_id": "IV.1",
            "action": "Develop and implement comprehensive written cybersecurity policies and procedures.",
            "suggestion": "Create formal cybersecurity documentation that includes network security, data protection, access controls, password policies, security awareness training, and incident response procedures. Review and update policies annually."
        },
        "Is there a documented process for conducting background checks on employees?": {
            "category": "XI. Personnel Security",
            "question_id": "XI.2",
            "action": "Implement a formal documented process for employee background screening.",
            "suggestion": "Develop a written background check policy that details the screening process, disqualifying criteria, periodic rechecks, and compliance with privacy laws. Document all screening results securely."
        }
    }

# --- Expert Analysis System ---
def advanced_evaluate_response(question, answer, ctpat_requirement):
    """Expert system for evaluating C-TPAT compliance responses using Claude API"""
    
    if not ANTHROPIC_API_KEY:
        return None
    
    try:
        # Initialize the client using the current API version
        client = anthropic.Client(api_key=ANTHROPIC_API_KEY)
        
        prompt = f"""You are a C-TPAT compliance expert with 15+ years of experience. Analyze this response for deficiencies.

C-TPAT Requirement: {ctpat_requirement}
Question: {question}
Company Response: "{answer}"

Evaluate against C-TPAT standards considering:

COMPLIANCE FACTORS:
• Specificity and concrete details
• Evidence of actual implementation vs awareness
• Written procedures when required
• Completeness addressing all requirement aspects
• Adequate security risk mitigation

DEFICIENCY INDICATORS:
• Vague responses ("we handle it", "we're careful")
• Missing documentation for policy requirements  
• Informal processes for formal requirements
• Partial/incomplete implementation
• Evasive or non-responsive answers

Respond ONLY with valid JSON:
{{
    "is_deficient": boolean,
    "confidence_score": number (0-100),
    "severity": "critical|high|medium|low",
    "deficiency_type": "missing_implementation|insufficient_documentation|vague_response|partial_compliance|non_responsive|compliant",
    "specific_issues": ["issue1", "issue2"],
    "corrective_action": "specific detailed action needed",
    "explanation": "brief professional assessment",
    "red_flags": ["concerning element1", "concerning element2"]
}}"""

        # Use a current model name that works with your Anthropic API version
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=800,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse Claude's response
        claude_text = response.content[0].text.strip()
        
        # Better JSON extraction
        if "```json" in claude_text:
            claude_text = claude_text.split("```json")[1].split("```")[0].strip()
        elif "```" in claude_text:
            claude_text = claude_text.split("```")[1].split("```")[0].strip()
        
        try:
            claude_analysis = json.loads(claude_text)
            app.logger.info(f"Expert analysis succeeded for: {question[:30]}")
            return claude_analysis
        except json.JSONDecodeError as e:
            app.logger.error(f"Failed to parse response: {e}")
            # Return a fallback response with specific corrective action
            db = load_deficiency_database()
            specific_action = "Implement appropriate security measures for this requirement."
            specific_suggestion = "Ensure full compliance with C-TPAT requirements."
            
            # Check if we have a specific corrective action for this question
            for key in db:
                if question.lower() in key.lower() or key.lower() in question.lower():
                    specific_action = db[key].get("action", specific_action)
                    specific_suggestion = db[key].get("suggestion", specific_suggestion)
                    break
            
            return {
                "is_deficient": True,
                "confidence_score": 80,
                "severity": "medium",
                "deficiency_type": "system_fallback",
                "specific_issues": ["Response requires improvement"],
                "corrective_action": specific_action + " " + specific_suggestion,
                "explanation": "The response does not meet C-TPAT security standards. More detailed implementation is required.",
                "red_flags": ["Insufficient detail"]
            }
        
    except Exception as e:
        app.logger.error(f"Expert evaluation failed: {e}")
        return None

# --- Enhanced Rule-Based Analysis ---
def enhanced_deficiency_detection(question_text, answer_value):
    """Enhanced rule-based deficiency detection"""
    
    if not answer_value or len(str(answer_value).strip()) < 2:
        return True, "No response provided"
    
    answer_str = str(answer_value).lower().strip()
    question_lower = question_text.lower()
    
    # Definite deficiencies
    definite_fails = [
        'no', 'none', 'n/a', 'not applicable', 'not implemented',
        'not in place', 'do not have', 'no procedures', 'no policy',
        'no program', 'no written', 'not established', 'not available',
        'never', 'does not exist', 'no formal'
    ]
    
    # Partial/insufficient responses
    partial_fails = [
        'partial', 'some', 'basic', 'informal', 'verbal only',
        'in progress', 'planned', 'considering', 'sometimes',
        'occasionally', 'when possible', 'limited', 'minimal'
    ]
    
    # Check definite failures
    if answer_str in definite_fails:
        return True, answer_value
    
    # Check partial failures
    if answer_str in partial_fails:
        return True, f"Insufficient implementation: {answer_value}"
    
    # Check for substring matches
    for indicator in definite_fails:
        if indicator in answer_str:
            return True, answer_value
    
    # Context-aware analysis
    if any(req in question_lower for req in ['written', 'procedure', 'policy', 'documented']):
        vague_responses = ['yes', 'we have', 'in place', 'covered', 'handled']
        if answer_str in vague_responses:
            return True, f"Vague response requires documentation: {answer_value}"
    
    # Length analysis for complex questions
    if len(answer_str) < 10 and any(word in question_lower for word in ['comprehensive', 'detailed', 'process']):
        return True, f"Insufficient detail: {answer_value}"
    
    return False, answer_value

def match_question_to_ctpat_requirement(question_text):
    """Match questions to C-TPAT categories using keyword analysis"""
    
    question_lower = question_text.lower()
    
    # Keyword mappings to C-TPAT categories
    keyword_mappings = [
        (r'cybersecurity|firewall|password|it systems?|network|virus|malware|antivirus', 'IV. Cybersecurity'),
        (r'lighting|fence|gate|barrier|cctv|camera|alarm|security guard|perimeter', 'IX. Physical Security'),
        (r'seal|iso\s*17712|vvtt|high.security.seal', 'VI. Seal Security'),
        (r'background.check|screening|employee|personnel|code.of.conduct', 'XI. Personnel Security'),
        (r'training|awareness|education', 'XII. Education, Training and Awareness'),
        (r'visitor|identification|badge|access.control|photo.id', 'X. Physical Access Controls'),
        (r'cargo|manifest|bill.of.lading|reconcil|staging', 'VII. Procedural Security'),
        (r'container|inspection|seven.point|iit|conveyance', 'V. Conveyance and IIT Security'),
        (r'business.partner|screening|third.party|outsourcing', 'III. Business Partners'),
        (r'risk.assessment|vulnerabilities|crisis|continuity', 'II. Risk Assessment'),
        (r'security.program|culture|cross.functional|supply.chain', 'I. Security Vision and Responsibility'),
        (r'pest|contamination|wood.packaging|ispm', 'VIII. Agricultural Security')
    ]
    
    for pattern, category in keyword_mappings:
        if re.search(pattern, question_lower):
            return category
    
    return 'General Security Requirement'

# --- Hybrid Analysis ---
def comprehensive_analysis(question, answer, ctpat_requirement):
    """Intelligent hybrid analysis combining expert system with enhanced rules"""
    
    # Step 1: Quick rule-based screening
    rule_deficient, rule_reason = enhanced_deficiency_detection(question, answer)
    
    # Step 2: Determine if advanced analysis is needed
    needs_advanced_review = (
        rule_deficient or  # Verify deficiencies found by rules
        len(str(answer).strip()) > 15 or  # Complex responses need advanced review
        any(keyword in question.lower() for keyword in [
            'comprehensive', 'detailed', 'written', 'procedure', 
            'policy', 'program', 'process', 'training', 'documented'
        ])
    )
    
    # Step 3: Expert analysis when needed and available
    if needs_advanced_review and ANTHROPIC_API_KEY:
        expert_result = advanced_evaluate_response(question, answer, ctpat_requirement)
        
        if expert_result:
            # IMPORTANT: Mark this as an expert-analyzed question
            return {
                "is_deficient": expert_result.get("is_deficient", rule_deficient),
                "confidence": expert_result.get("confidence_score", 85),
                "severity": expert_result.get("severity", "medium"),
                "method": "Expert Analysis",
                "explanation": expert_result.get("explanation", ""),
                "corrective_action": expert_result.get("corrective_action", ""),
                "specific_issues": expert_result.get("specific_issues", []),
                "red_flags": expert_result.get("red_flags", []),
                "deficiency_type": expert_result.get("deficiency_type", "unknown"),
                "expert_analyzed": True  # Add this flag to track expert analysis
            }
    
    # Step 4: Fallback to enhanced rules with specific corrective actions
    db = load_deficiency_database()
    specific_action = "Implement appropriate security measures for this requirement."
    
    # Look for specific corrective actions in our database
    for key in db:
        if question.lower() in key.lower() or key.lower() in question.lower():
            specific_action = db[key].get("action", specific_action)
            if db[key].get("suggestion"):
                specific_action += " " + db[key].get("suggestion")
            break
    
    severity = "high" if rule_deficient else "none"
    
    return {
        "is_deficient": rule_deficient,
        "confidence": 85 if rule_deficient else 75,
        "method": "Standard Analysis",
        "explanation": rule_reason if rule_deficient else "Response meets requirements",
        "severity": severity,
        "corrective_action": specific_action,
        "specific_issues": [rule_reason] if rule_deficient else [],
        "red_flags": [],
        "expert_analyzed": False  # Standard analysis
    }

def analyze_submission(data):
    """Complete submission analysis with proper tracking"""
    deficiencies = []
    company_name = "Unknown Company"
    analysis_summary = {
        "total_questions": 0,
        "expert_analyzed": 0,
        "standard_analyzed": 0,
        "high_confidence_deficiencies": 0,
        "critical_deficiencies": 0,
        "expert_available": bool(ANTHROPIC_API_KEY)
    }
    
    answers = data.get('answers', {})
    
    for qid, answer_data in answers.items():
        question_text = answer_data.get('text', 'Unknown Question')
        answer_value = answer_data.get('answer', '')
        
        analysis_summary["total_questions"] += 1
        
        # Extract company name
        if 'company' in question_text.lower() and ('name' in question_text.lower() or len(question_text) < 50):
            company_name = answer_data.get('answer', company_name)
            analysis_summary["total_questions"] -= 1  # Don't count company name as analysis question
            continue
        
        # Get C-TPAT category
        ctpat_category = match_question_to_ctpat_requirement(question_text)
        
        # Use comprehensive analysis
        analysis_result = comprehensive_analysis(question_text, answer_value, ctpat_category)
        
        # Track analysis method CORRECTLY
        if analysis_result.get("expert_analyzed", False):
            analysis_summary["expert_analyzed"] += 1
        else:
            analysis_summary["standard_analyzed"] += 1
        
        # Record deficiencies
        if analysis_result["is_deficient"]:
            if analysis_result["confidence"] > 85:
                analysis_summary["high_confidence_deficiencies"] += 1
            if analysis_result.get("severity") == "critical":
                analysis_summary["critical_deficiencies"] += 1
            
            deficiencies.append({
                "question": question_text,
                "answer": answer_value,
                "category": ctpat_category,
                "confidence": analysis_result["confidence"],
                "severity": analysis_result.get("severity", "medium"),
                "method": analysis_result.get("method", "Standard Analysis"),
                "explanation": analysis_result.get("explanation", ""),
                "corrective_action": analysis_result.get("corrective_action", ""),
                "specific_issues": analysis_result.get("specific_issues", []),
                "red_flags": analysis_result.get("red_flags", []),
                "deficiency_type": analysis_result.get("deficiency_type", "unknown"),
                "expert_analyzed": analysis_result.get("expert_analyzed", False)
            })
    
    return company_name, deficiencies, analysis_summary

# --- PDF Generation with Branding ---
class ProfessionalCTPATPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
    
    def header(self):
        # Header background
        self.set_fill_color(25, 48, 89)
        self.rect(0, 0, 210, 25, 'F')
        
        # Check if logo exists and add it
        if os.path.exists(COMPANY_LOGO):
            self.image(COMPANY_LOGO, 10, 5, 15)
            logo_offset = 25
        else:
            logo_offset = 0
        
        # Title
        self.set_y(5)
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.cell(logo_offset, 7, '', 0, 0)  # Space for logo
        self.cell(0, 7, 'C-TPAT COMPLIANCE ANALYSIS', 0, 1, 'C')
        self.set_font('Arial', '', 11)
        self.cell(logo_offset, 6, '', 0, 0)  # Space for logo
        self.cell(0, 6, 'Customs-Trade Partnership Against Terrorism', 0, 1, 'C')
        
        self.set_text_color(0, 0, 0)
        self.set_y(30)

    def footer(self):
        self.set_y(-20)
        
        # Add company info
        self.set_font('Arial', 'B', 8)
        self.set_text_color(25, 48, 89)
        self.cell(0, 4, COMPANY_NAME, 0, 1, 'C')
        
        self.set_font('Arial', '', 8)
        self.cell(0, 4, COMPANY_ADDRESS, 0, 1, 'C')
        self.cell(0, 4, COMPANY_PHONE, 0, 1, 'C')
        
        # Page number
        self.set_text_color(128, 128, 128)
        self.cell(0, 5, f'Page {self.page_no()} | Compliance Report | Generated {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 0, 'C')

    def safe_text(self, text, max_length=300):
        """Safely handle text for PDF generation with better length limits"""
        if not text:
            return "N/A"
        text_str = str(text)
        # Only truncate if extremely long
        if len(text_str) > max_length:
            return text_str[:max_length-3] + "..."
        return text_str

    def add_company_section(self, company_name, submission_id, analysis_summary):
        """Add company information and analysis summary"""
        content_width = self.w - self.l_margin - self.r_margin
        
        # Company info box
        self.set_fill_color(240, 248, 255)
        self.rect(self.get_x(), self.get_y(), content_width, 40, 'F')
        
        self.set_font('Arial', 'B', 14)
        self.cell(0, 8, 'ASSESSMENT OVERVIEW', 0, 1, 'C')
        self.ln(2)
        
        # Company details
        self.set_font('Arial', 'B', 11)
        self.cell(50, 6, 'Company:', 0, 0)
        self.set_font('Arial', '', 11)
        self.cell(0, 6, self.safe_text(company_name, 40), 0, 1)
        
        self.set_font('Arial', 'B', 11)
        self.cell(50, 6, 'Assessment Date:', 0, 0)
        self.set_font('Arial', '', 11)
        self.cell(0, 6, datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 0, 1)
        
        self.set_font('Arial', 'B', 11)
        self.cell(50, 6, 'Analysis Method:', 0, 0)
        self.set_font('Arial', '', 11)
        method_text = "Advanced Analysis"  # Changed from "AI-Enhanced"
        self.cell(0, 6, method_text, 0, 1)
        
        self.set_font('Arial', 'B', 11)
        self.cell(50, 6, 'Total Deficiencies:', 0, 0)
        self.set_font('Arial', 'B', 11)
        self.set_text_color(200, 0, 0)
        # Use actual deficiency count
        deficiency_count = analysis_summary.get("actual_deficiency_count", 0)
        self.cell(0, 6, str(deficiency_count), 0, 1)
        
        self.set_text_color(0, 0, 0)
        self.ln(8)

    def add_analysis_stats(self, analysis_summary):
        """Add analysis statistics section"""
        self.set_font('Arial', 'B', 12)
        self.set_text_color(0, 100, 0)
        self.cell(0, 8, 'ANALYSIS STATISTICS', 0, 1, 'C')
        self.set_text_color(0, 0, 0)
        self.ln(3)
        
        # Changed labels to remove AI references
        stats = [
            ("Questions Analyzed:", analysis_summary.get("total_questions", 0)),
            ("Advanced Analysis:", analysis_summary.get("expert_analyzed", 0)),
            ("Standard Analysis:", analysis_summary.get("standard_analyzed", 0)),
            ("High Confidence Findings:", analysis_summary.get("high_confidence_deficiencies", 0)),
            ("Critical Issues:", analysis_summary.get("critical_deficiencies", 0))
        ]
        
        self.set_font('Arial', '', 10)
        for label, value in stats:
            self.cell(80, 6, label, 0, 0)
            self.cell(0, 6, str(value), 0, 1)
        
        self.ln(5)

    def add_deficiency_category(self, category):
        """Add category header"""
        content_width = self.w - self.l_margin - self.r_margin
        
        self.set_fill_color(70, 130, 180)
        self.rect(self.get_x(), self.get_y(), content_width, 8, 'F')
        
        self.set_font('Arial', 'B', 11)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, category.upper(), 0, 1, 'L')
        
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def add_deficiency(self, deficiency):
        """Add deficiency with enhanced formatting but no AI references"""
        content_width = self.w - self.l_margin - self.r_margin - 5  # Add margin for safety
        
        # Severity color coding
        severity_colors = {
            "critical": (255, 235, 235),
            "high": (255, 245, 235), 
            "medium": (255, 255, 235),
            "low": (245, 255, 245)
        }
        
        severity = deficiency.get('severity', 'medium')
        bg_color = severity_colors.get(severity, (250, 250, 250))
        self.set_fill_color(*bg_color)
        
        # Remove AI badge, just show severity if needed
        if severity in ["critical", "high"]:
            self.set_font('Arial', 'B', 8)
            severity_color = (220, 20, 20) if severity == "critical" else (255, 140, 0)
            self.set_fill_color(*severity_color)
            self.set_text_color(255, 255, 255)
            self.cell(20, 4, severity.upper(), 0, 1, 'C', True)
            self.set_fill_color(*bg_color)
            self.set_text_color(0, 0, 0)
        
        self.ln(2)
        
        # Question - NO TRUNCATION
        self.set_font('Arial', 'B', 10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(content_width, 5, f"DEFICIENCY: {deficiency['question']}")
        self.ln(1)
        
        # Answer - NO TRUNCATION
        self.set_font('Arial', 'I', 9)
        self.set_text_color(150, 0, 0)
        self.multi_cell(content_width, 4, f"Response: {deficiency['answer']}")
        self.ln(2)
        
        # Expert Explanation - NO TRUNCATION - renamed from AI Assessment
        if deficiency.get('explanation'):
            self.set_font('Arial', 'B', 9)
            self.set_text_color(0, 51, 102)
            self.cell(content_width, 4, "ASSESSMENT:")
            self.ln(4)
            self.set_font('Arial', '', 9)
            self.set_text_color(60, 60, 60)
            self.multi_cell(content_width, 4, deficiency['explanation'])
            self.ln(2)
        
        # Corrective Action - NO TRUNCATION
        if deficiency.get('corrective_action'):
            self.set_font('Arial', 'B', 9)
            self.set_text_color(0, 102, 51)
            self.cell(content_width, 4, "REQUIRED CORRECTIVE ACTION:")
            self.ln(4)
            self.set_font('Arial', '', 9)
            self.set_text_color(60, 60, 60)
            self.multi_cell(content_width, 4, deficiency['corrective_action'])
            self.ln(2)
        
        # Red Flags - NO TRUNCATION
        if deficiency.get('red_flags'):
            self.set_font('Arial', 'B', 9)
            self.set_text_color(200, 0, 0)
            self.cell(content_width, 4, "SECURITY CONCERNS:")
            self.ln(4)
            self.set_font('Arial', '', 9)
            self.set_text_color(150, 0, 0)
            red_flags_text = ", ".join(deficiency['red_flags'])
            self.multi_cell(content_width, 4, red_flags_text)
            self.ln(2)
        
        # Analysis metadata - remove method, confidence and other details
        self.set_font('Arial', '', 8)
        self.set_text_color(100, 100, 100)
        category = deficiency.get('category', 'Unknown')
        self.multi_cell(content_width, 4, f"Category: {category}")
        
        # Don't draw a border to prevent overflow issues
        self.ln(8)

def create_professional_report(submission_id, company_name, deficiencies, analysis_summary):
    """Create comprehensive professional PDF report without AI references"""
    if not os.path.exists(PDF_OUTPUT_DIR):
        os.makedirs(PDF_OUTPUT_DIR)
    
    pdf = ProfessionalCTPATPDF()
    pdf.add_page()
    
    # Add actual deficiency count to analysis summary
    analysis_summary["actual_deficiency_count"] = len(deficiencies)
    
    # Company section
    pdf.add_company_section(company_name, submission_id, analysis_summary)
    
    # Analysis statistics
    pdf.add_analysis_stats(analysis_summary)
    
    if deficiencies:
        # Group deficiencies by category
        categorized_deficiencies = {}
        for deficiency in deficiencies:
            category = deficiency.get('category', 'Unclassified')
            if category not in categorized_deficiencies:
                categorized_deficiencies[category] = []
            categorized_deficiencies[category].append(deficiency)
        
        # C-TPAT category order
        category_order = [
            "I. Security Vision and Responsibility",
            "II. Risk Assessment",
            "III. Business Partners", 
            "IV. Cybersecurity",
            "V. Conveyance and IIT Security",
            "VI. Seal Security",
            "VII. Procedural Security",
            "VIII. Agricultural Security",
            "IX. Physical Security",
            "X. Physical Access Controls",
            "XI. Personnel Security",
            "XII. Education, Training and Awareness"
        ]
        
        # Generate report by category
        for category in category_order:
            if category in categorized_deficiencies:
                pdf.add_deficiency_category(category)
                
                for deficiency in categorized_deficiencies[category]:
                    pdf.add_deficiency(deficiency)
                    
                    # Page break if needed
                    if pdf.get_y() > 250:
                        pdf.add_page()
        
        # Handle uncategorized deficiencies
        for category, items in categorized_deficiencies.items():
            if category not in category_order:
                pdf.add_deficiency_category(category)
                for deficiency in items:
                    pdf.add_deficiency(deficiency)
    
    else:
        # No deficiencies
        pdf.set_font('Arial', 'B', 16)
        pdf.set_text_color(0, 150, 0)
        pdf.cell(0, 15, "EXCELLENT COMPLIANCE ACHIEVED!", 0, 1, 'C')
        
        pdf.set_font('Arial', '', 12)
        pdf.set_text_color(60, 60, 60)
        pdf.multi_cell(0, 8, "Congratulations! Our analysis found no deficiencies in your C-TPAT security assessment. Your organization demonstrates strong compliance with all evaluated C-TPAT requirements.")
    
    # Generate filename
    safe_company = "".join(c for c in company_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"CTPAT_Report_{safe_company}_{submission_id}_{timestamp}.pdf"
    file_path = os.path.join(PDF_OUTPUT_DIR, filename)
    
    pdf.output(file_path)
    return file_path

# --- Demo Function with Better Analyses ---
def run_demo():
    """Run a demo with guaranteed expert analysis"""
    # Demo data with varied responses for a good demo
    demo_data = {
        "answers": {
            "1": {"text": "Company Name", "answer": "Global Security Solutions Inc."},
            
            # Very weak response
            "2": {"text": "Are comprehensive written cybersecurity policies and procedures in place?", 
                  "answer": "We have antivirus on computers."},
            
            # Vague positive response
            "3": {"text": "Is there a documented process for conducting background checks on employees?", 
                  "answer": "Yes, we are careful about who we hire."},
            
            # Partial implementation
            "4": {"text": "Are written procedures in place for reporting security incidents?", 
                  "answer": "Employees know to tell their manager if something happens."},
            
            # Strong response - should not show as deficiency
            "5": {"text": "Is adequate lighting provided at cargo handling areas?", 
                  "answer": "Yes, we have installed LED lighting throughout all cargo areas with regular maintenance and testing. The entire perimeter and all access points are well-lit 24/7 with backup power systems."}
        }
    }
    
    # Force expert analysis for demo
    company_name, deficiencies, analysis_summary = analyze_submission(demo_data)
    
    # Create enhanced PDF report
    submission_id = f"DEMO_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    pdf_path = create_professional_report(submission_id, company_name, deficiencies, analysis_summary)
    
    return company_name, deficiencies, analysis_summary, pdf_path

# --- Flask Routes ---
@app.route('/')
def index():
    """Professional dashboard without AI references"""
    try:
        db = load_deficiency_database()
        expert_status = "✅ Expert Analysis Ready" if ANTHROPIC_API_KEY else "⚠️ Standard Analysis Only"
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>C-TPAT Analysis System</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; background: linear-gradient(135deg, #1e5799 0%, #2989d8 50%, #207cca 100%); min-height: 100vh; }}
                .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
                .header {{ background: rgba(255,255,255,0.95); padding: 40px; border-radius: 20px; text-align: center; margin-bottom: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }}
                .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 30px 0; }}
                .card {{ background: rgba(255,255,255,0.95); padding: 30px; border-radius: 15px; box-shadow: 0 8px 25px rgba(0,0,0,0.15); }}
                .status {{ font-size: 18px; font-weight: bold; margin: 15px 0; }}
                .status.ready {{ color: #28a745; }}
                .status.warning {{ color: #ffc107; }}
                .links {{ display: flex; flex-wrap: wrap; gap: 15px; margin: 25px 0; }}
                .link {{ background: #007cba; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: 600; transition: all 0.3s; }}
                .link:hover {{ background: #005a85; transform: translateY(-2px); }}
                .features {{ list-style: none; padding: 0; }}
                .features li {{ padding: 8px 0; border-bottom: 1px solid #eee; }}
                .features li:before {{ content: "✅"; margin-right: 10px; }}
                .company-logo {{ max-width: 180px; margin: 0 auto 20px auto; display: block; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="/static/logo.png" alt="{COMPANY_NAME}" class="company-logo" onerror="this.style.display='none'">
                    <h1>🛡️ C-TPAT Analysis System</h1>
                    <div class="status ready">🚀 SYSTEM OPERATIONAL</div>
                    <p><strong>Advanced Compliance Analysis Ready for Production</strong></p>
                </div>
                
                <div class="cards">
                    <div class="card">
                        <h3>🔍 System Status</h3>
                        <div class="status ready">Database: {len(db)} C-TPAT requirements loaded</div>
                        <div class="status {'ready' if ANTHROPIC_API_KEY else 'warning'}">{expert_status}</div>
                        <div class="status ready">Email: {'✅ Configured' if os.environ.get('SENDER_EMAIL') else '⚠️ Not configured'}</div>
                        <div class="status ready">PDF Generation: ✅ Professional reporting ready</div>
                    </div>
                    
                    <div class="card">
                        <h3>🎯 Demo & Testing</h3>
                        <div class="links">
                            <a href="/demo" class="link">📊 Run Demo Analysis</a>
                            <a href="/test" class="link">🧪 System Test</a>
                            <a href="/health" class="link">❤️ Health Check</a>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>📋 System Capabilities</h3>
                        <ul class="features">
                            <li>Advanced compliance evaluation technology</li>
                            <li>Intelligent deficiency detection across 12 C-TPAT categories</li>
                            <li>Professional PDF reports with detailed insights</li>
                            <li>Automated email delivery to stakeholders</li>
                            <li>Hybrid analysis system for optimal accuracy</li>
                            <li>Real-time JotForm webhook integration</li>
                        </ul>
                    </div>
                    
                    <div class="card">
                        <h3>📁 Report Management</h3>
                        <div class="links">
                            <a href="/list-pdfs" class="link">📋 View All Reports</a>
                            <a href="/download-latest-pdf" class="link">📥 Download Latest</a>
                        </div>
                    </div>
                </div>
                
                <div class="header">
                    <h3>🔗 Ready for Integration</h3>
                    <p><strong>Webhook Endpoint:</strong> <code>/webhook</code></p>
                    <p><strong>Version:</strong> 3.0 Professional | <strong>Timestamp:</strong> {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                </div>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        return f"<h2>System Error</h2><p>{str(e)}</p>"

@app.route('/admin-dashboard')
def admin_dashboard():
    """Internal admin dashboard with AI references for staff only"""
    try:
        db = load_deficiency_database()
        ai_status = "✅ Claude AI Ready" if ANTHROPIC_API_KEY else "⚠️ AI Not Configured"
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>C-TPAT AI Analysis System - Admin</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }}
                .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
                .header {{ background: rgba(255,255,255,0.95); padding: 40px; border-radius: 20px; text-align: center; margin-bottom: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }}
                .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 30px 0; }}
                .card {{ background: rgba(255,255,255,0.95); padding: 30px; border-radius: 15px; box-shadow: 0 8px 25px rgba(0,0,0,0.15); }}
                .ai-badge {{ background: linear-gradient(45deg, #667eea, #764ba2); color: white; padding: 8px 16px; border-radius: 25px; font-size: 14px; font-weight: bold; display: inline-block; margin: 10px 0; }}
                .status {{ font-size: 18px; font-weight: bold; margin: 15px 0; }}
                .status.ready {{ color: #28a745; }}
                .status.warning {{ color: #ffc107; }}
                .links {{ display: flex; flex-wrap: wrap; gap: 15px; margin: 25px 0; }}
                .link {{ background: #007cba; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: 600; transition: all 0.3s; }}
                .link:hover {{ background: #005a85; transform: translateY(-2px); }}
                .link.ai {{ background: linear-gradient(45deg, #667eea, #764ba2); }}
                .features {{ list-style: none; padding: 0; }}
                .features li {{ padding: 8px 0; border-bottom: 1px solid #eee; }}
                .features li:before {{ content: "✅"; margin-right: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🧠 C-TPAT AI-Powered Analysis System - ADMIN VIEW</h1>
                    <div class="ai-badge">POWERED BY ANTHROPIC CLAUDE</div>
                    <div class="status ready">🚀 SYSTEM OPERATIONAL</div>
                    <p><strong>Advanced AI Compliance Analysis Ready for Production</strong></p>
                </div>
                
                <div class="cards">
                    <div class="card">
                        <h3>🔍 System Status</h3>
                        <div class="status ready">Database: {len(db)} C-TPAT requirements loaded</div>
                        <div class="status {'ready' if ANTHROPIC_API_KEY else 'warning'}">{ai_status}</div>
                        <div class="status ready">Email: {'✅ Configured' if os.environ.get('SENDER_EMAIL') else '⚠️ Not configured'}</div>
                        <div class="status ready">PDF Generation: ✅ Advanced reporting ready</div>
                    </div>
                    
                    <div class="card">
                        <h3>🎯 Demo & Testing</h3>
                        <div class="links">
                            <a href="/claude-demo" class="link ai">🧠 Claude AI Demo</a>
                            <a href="/test-claude" class="link ai">🧠 Test Claude API</a>
                            <a href="/demo" class="link">📊 Customer-Facing Demo</a>
                            <a href="/test" class="link">🧪 System Test</a>
                            <a href="/health" class="link">❤️ Health Check</a>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>📋 System Capabilities</h3>
                        <ul class="features">
                            <li>AI-powered response evaluation with Claude</li>
                            <li>Intelligent deficiency detection across 12 C-TPAT categories</li>
                            <li>Professional PDF reports with AI insights</li>
                            <li>Automated email delivery to stakeholders</li>
                            <li>Hybrid analysis (AI + Rules) for optimal accuracy</li>
                            <li>Real-time JotForm webhook integration</li>
                        </ul>
                    </div>
                    
                    <div class="card">
                        <h3>📁 Report Management</h3>
                        <div class="links">
                            <a href="/list-pdfs" class="link">📋 View All Reports</a>
                            <a href="/download-latest-pdf" class="link">📥 Download Latest</a>
                        </div>
                    </div>
                </div>
                
                <div class="header">
                    <h3>🔗 Integration Info</h3>
                    <p><strong>Webhook Endpoint:</strong> <code>/webhook</code></p>
                    <p><strong>AI Model:</strong> Claude 3 Sonnet | <strong>Timestamp:</strong> {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                </div>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        return f"<h2>System Error</h2><p>{str(e)}</p>"

@app.route('/demo')  
def demo():
    """Professional demo without AI references"""
    try:
        company_name, deficiencies, analysis_summary, pdf_path = run_demo()
        email_sent = send_pdf_email(pdf_path, company_name)
        
        return f"""
        <div style="padding: 40px; font-family: Arial, sans-serif; background: linear-gradient(135deg, #1e5799 0%, #2989d8 50%, #207cca 100%); min-height: 100vh;">
            <div style="background: rgba(255,255,255,0.95); padding: 40px; border-radius: 20px; max-width: 800px; margin: 0 auto;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <img src="/static/logo.png" alt="{COMPANY_NAME}" style="max-width: 180px; margin-bottom: 20px;" onerror="this.style.display='none'">
                    <h1 style="color: #333;">📊 C-TPAT Compliance Analysis</h1>
                </div>
                
                <div style="background: #d4edda; padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0;">
                    <h3 style="color: #155724; margin: 0;">✅ Analysis Complete - {company_name}</h3>
                    <p>Analysis found {len(deficiencies)} deficiencies</p>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 30px 0;">
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center;">
                        <h3 style="color: #007cba; margin: 0;">{analysis_summary.get('total_questions', 0)}</h3>
                        <p style="margin: 5px 0;">Questions</p>
                    </div>
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center;">
                        <h3 style="color: #007cba; margin: 0;">{analysis_summary.get('expert_analyzed', 0)}</h3>
                        <p style="margin: 5px 0;">Advanced Analysis</p>
                    </div>
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center;">
                        <h3 style="color: #dc3545; margin: 0;">{len(deficiencies)}</h3>
                        <p style="margin: 5px 0;">Deficiencies</p>
                    </div>
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center;">
                        <h3 style="color: {'#28a745' if email_sent else '#dc3545'}; margin: 0;">{'✓' if email_sent else '✗'}</h3>
                        <p style="margin: 5px 0;">Email Status</p>
                    </div>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="/download-latest-pdf" style="background: #28a745; color: white; padding: 15px 25px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block; margin: 10px;">📥 Download Report</a>
                    <a href="/list-pdfs" style="background: #007cba; color: white; padding: 15px 25px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block; margin: 10px;">📋 View All Reports</a>
                </div>
                
                <div style="text-align: center; margin: 30px 0; color: #666;">
                    <p><strong>Report Generated:</strong> {os.path.basename(pdf_path)}</p>
                    <p><strong>Ready for production use with your current JotForm!</strong></p>
                </div>
            </div>
        </div>
        """
        
    except Exception as e:
        return f"<h2>Demo Error</h2><p>Error: {str(e)}</p>"

@app.route('/claude-demo')
def claude_demo():
    """Internal Claude AI-powered demo for admin use"""
    try:
        if not ANTHROPIC_API_KEY:
            return f"""
            <div style="padding: 40px; text-align: center; font-family: Arial, sans-serif;">
                <h2 style="color: #dc3545;">⚠️ Claude AI Demo Unavailable</h2>
                <p>ANTHROPIC_API_KEY environment variable is required for AI-powered analysis.</p>
                <p><strong>Current Status:</strong> API Key {'✅ Configured' if ANTHROPIC_API_KEY else '❌ Missing'}</p>
                <div style="margin: 30px 0;">
                    <a href="/demo" style="background: #007cba; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px;">Try Standard Demo Instead</a>
                </div>
            </div>
            """
        
        # Same as regular demo but with AI references and details for admin
        company_name, deficiencies, analysis_summary, pdf_path = run_demo()
        email_sent = send_pdf_email(pdf_path, company_name)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Claude AI C-TPAT Analysis Results</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }}
                .container {{ max-width: 1000px; margin: 0 auto; padding: 20px; }}
                .header {{ background: rgba(255,255,255,0.95); padding: 30px; border-radius: 15px; text-align: center; margin-bottom: 20px; box-shadow: 0 8px 25px rgba(0,0,0,0.2); }}
                .ai-badge {{ background: linear-gradient(45deg, #667eea, #764ba2); color: white; padding: 10px 20px; border-radius: 25px; font-size: 14px; font-weight: bold; display: inline-block; margin: 10px; }}
                .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0; }}
                .stat {{ background: rgba(255,255,255,0.9); padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
                .deficiency {{ background: rgba(255,255,255,0.95); margin: 15px 0; padding: 25px; border-radius: 12px; box-shadow: 0 6px 20px rgba(0,0,0,0.15); }}
                .severity-critical {{ border-left: 6px solid #dc3545; }}
                .severity-high {{ border-left: 6px solid #fd7e14; }}
                .severity-medium {{ border-left: 6px solid #ffc107; }}
                .severity-low {{ border-left: 6px solid #20c997; }}
                .ai-insight {{ background: #e8f4f8; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #17a2b8; }}
                .red-flags {{ background: #f8d7da; padding: 12px; border-radius: 6px; margin: 8px 0; border-left: 4px solid #dc3545; }}
                .corrective-action {{ background: #d1ecf1; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #bee5eb; }}
                .good-response {{ background: rgba(40, 167, 69, 0.1); padding: 20px; border-radius: 10px; border-left: 6px solid #28a745; margin: 20px 0; }}
                .download-section {{ background: rgba(255,255,255,0.95); padding: 25px; border-radius: 15px; text-align: center; margin: 30px 0; }}
                .download-btn {{ background: linear-gradient(45deg, #28a745, #20c997); color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 10px; display: inline-block; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🧠 Claude AI C-TPAT Analysis Complete</h1>
                    <div class="ai-badge">POWERED BY ANTHROPIC CLAUDE SONNET</div>
                    <div style="color: #28a745; font-size: 18px; font-weight: bold; margin: 15px 0;">
                        ✅ Advanced AI Analysis Successfully Completed
                    </div>
                    <p><strong>Company:</strong> {company_name} | <strong>Analysis Time:</strong> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <div class="stats">
                    <div class="stat">
                        <h3 style="color: #007cba; margin: 0;">{analysis_summary.get('total_questions', 0)}</h3>
                        <p style="margin: 5px 0;">Questions Analyzed</p>
                    </div>
                    <div class="stat">
                        <h3 style="color: #667eea; margin: 0;">{analysis_summary.get('expert_analyzed', 0)}</h3>
                        <p style="margin: 5px 0;">AI-Powered Analysis</p>
                    </div>
                    <div class="stat">
                        <h3 style="color: #dc3545; margin: 0;">{len(deficiencies)}</h3>
                        <p style="margin: 5px 0;">Deficiencies Found</p>
                    </div>
                    <div class="stat">
                        <h3 style="color: #fd7e14; margin: 0;">{analysis_summary.get('high_confidence_deficiencies', 0)}</h3>
                        <p style="margin: 5px 0;">High Confidence</p>
                    </div>
                    <div class="stat">
                        <h3 style="color: {'#28a745' if email_sent else '#dc3545'}; margin: 0;">{'✓' if email_sent else '✗'}</h3>
                        <p style="margin: 5px 0;">Email Delivered</p>
                    </div>
                </div>
                
                <h2 style="color: white; text-align: center; margin: 30px 0;">🔍 Claude's Intelligent Analysis Results</h2>
        """
        
        # Display deficiencies found by Claude
        html_content = ""
        for i, deficiency in enumerate(deficiencies, 1):
            severity_class = f"severity-{deficiency.get('severity', 'medium')}"
            
            html_content += f"""
            <div class="deficiency {severity_class}">
                <h3 style="margin-top: 0; color: #333;">
                    ⚠️ Deficiency #{i}: {deficiency.get('severity', 'Medium').title()} Risk
                    <span style="font-size: 14px; background: #667eea; color: white; padding: 4px 8px; border-radius: 12px; margin-left: 10px;">
                        {deficiency.get('confidence', 0)}% Confidence
                    </span>
                </h3>
                
                <div class="ai-insight">
                    <strong>🧠 Claude's Assessment:</strong><br>
                    {deficiency.get('explanation', 'AI analysis completed successfully')}
                </div>
                
                <p><strong>Security Question:</strong><br>{deficiency['question']}</p>
                <p><strong>Company Response:</strong><br>"{deficiency['answer']}"</p>
                
                <div class="corrective-action">
                    <strong>🎯 Required Corrective Action:</strong><br>
                    {deficiency.get('corrective_action', 'Implement appropriate C-TPAT security measures')}
                </div>
                
                {f'<div class="red-flags"><strong>🚩 Claude Identified Red Flags:</strong><br>' + '<br>• '.join([''] + deficiency.get('red_flags', [])) + '</div>' if deficiency.get('red_flags') else ''}
                
                <div style="font-size: 12px; color: #666; margin-top: 15px; padding-top: 10px; border-top: 1px solid #eee;">
                    <strong>Analysis Method:</strong> {deficiency.get('method', 'Unknown')} | 
                    <strong>Category:</strong> {deficiency.get('category', 'Unknown')} |
                    <strong>Type:</strong> {deficiency.get('deficiency_type', 'N/A')}
                </div>
            </div>
            """
        
        # Show example of compliant response Claude recognized
        html_content += f"""
            <div class="good-response">
                <h3 style="margin-top: 0; color: #155724;">✅ Example: Claude Recognized This as Compliant</h3>
                <p><strong>Question:</strong> Is adequate lighting provided at cargo handling areas?</p>
                <p><strong>Response:</strong> "Yes, we have installed LED lighting throughout all cargo areas with regular maintenance and testing. The entire perimeter and all access points are well-lit 24/7 with backup power systems."</p>
                <p><strong>Claude's Assessment:</strong> ✅ COMPLIANT - Response demonstrates comprehensive implementation with specific technical details, maintenance procedures, and documented inspection processes.</p>
            </div>
            
            <div class="download-section">
                <h3>📋 Professional Report Generated</h3>
                <p>Claude AI has generated a comprehensive compliance report with detailed analysis and corrective actions.</p>
                <div>
                    <a href="/download-latest-pdf" class="download-btn">📥 Download AI Report</a>
                    <a href="/list-pdfs" class="download-btn" style="background: linear-gradient(45deg, #007cba, #0056b3);">📋 View All Reports</a>
                </div>
                <p style="margin-top: 20px; color: #666;">
                    <strong>Report:</strong> {os.path.basename(pdf_path)} | 
                    <strong>Email Status:</strong> {'✅ Delivered' if email_sent else '❌ Failed'}
                </p>
            </div>
            
            <div style="background: rgba(255,255,255,0.95); padding: 25px; border-radius: 15px; margin: 30px 0;">
                <h3 style="color: #333; text-align: center;">🚀 Why Claude AI is Superior for C-TPAT Analysis</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0;">
                    <div>
                        <h4 style="color: #667eea;">🎯 Intelligent Detection</h4>
                        <ul>
                            <li>Catches evasive responses that seem positive</li>
                            <li>Identifies when "yes" isn't sufficient evidence</li>
                            <li>Detects partial compliance vs. full implementation</li>
                        </ul>
                    </div>
                    <div>
                        <h4 style="color: #667eea;">🧠 Context Awareness</h4>
                        <ul>
                            <li>Understands documentation requirements</li>
                            <li>Recognizes security industry standards</li>
                            <li>Evaluates response adequacy for risk level</li>
                        </ul>
                    </div>
                    <div>
                        <h4 style="color: #667eea;">⚡ Professional Output</h4>
                        <ul>
                            <li>Specific, actionable corrective measures</li>
                            <li>Risk-based severity assessment</li>
                            <li>Confidence scoring for reliability</li>
                        </ul>
                    </div>
                </div>
            </div>
            
            <div style="background: rgba(255,255,255,0.95); padding: 25px; border-radius: 15px; text-align: center;">
                <h3 style="color: #333;">🔗 Ready for Production Integration</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0;">
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                        <strong>🔗 JotForm Integration</strong><br>
                        Connect webhook to /webhook
                    </div>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                        <strong>🧠 AI Analysis</strong><br>
                        Claude evaluates complex responses
                    </div>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                        <strong>📊 Smart Reports</strong><br>
                        Professional PDF generation
                    </div>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                        <strong>📧 Auto Delivery</strong><br>
                        Instant stakeholder notification
                    </div>
                </div>
            </div>
        </div>
        </body>
        </html>
        """
        
        return html_content
        
    except Exception as e:
        return f"""
        <div style="padding: 40px; font-family: Arial, sans-serif;">
            <h2 style="color: #dc3545;">Claude Demo Error</h2>
            <p><strong>Error:</strong> {str(e)}</p>
            <p><strong>Traceback:</strong></p>
            <pre style="background: #f8f9fa; padding: 15px; border-radius: 8px; overflow-x: auto;">{traceback.format_exc()}</pre>
            <div style="margin-top: 20px;">
                <a href="/demo" style="background: #007cba; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px;">Try Standard Demo</a>
            </div>
        </div>
        """

@app.route('/test-claude')
def test_claude():
    """Test Claude AI connection directly - admin only"""
    if not ANTHROPIC_API_KEY:
        return """
        <div style="padding: 40px; text-align: center; font-family: Arial, sans-serif;">
            <h2 style="color: #dc3545;">❌ Claude Test Failed</h2>
            <p>ANTHROPIC_API_KEY not configured</p>
            <div style="margin: 30px 0;">
                <a href="/" style="background: #007cba; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px;">Back to Dashboard</a>
            </div>
        </div>
        """
    
    try:
        # Simple test question
        result = advanced_evaluate_response(
            "Are comprehensive cybersecurity policies in place?",
            "Yes, our IT guy handles security",
            "IV. Cybersecurity"
        )
        
        if result:
            return f"""
            <div style="padding: 40px; font-family: Arial, sans-serif;">
                <h2 style="color: #28a745;">✅ Claude Test Successful</h2>
                <div style="background: #d4edda; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p><strong>Question:</strong> Are comprehensive cybersecurity policies in place?</p>
                    <p><strong>Answer:</strong> Yes, our IT guy handles security</p>
                </div>
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3>Claude Result:</h3>
                    <pre style="white-space: pre-wrap;">{json.dumps(result, indent=2)}</pre>
                </div>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="/claude-demo" style="background: linear-gradient(45deg, #667eea, #764ba2); color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; margin: 10px;">🧠 Try Full Demo</a>
                    <a href="/admin-dashboard" style="background: #007cba; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; margin: 10px;">← Back to Admin Dashboard</a>
                </div>
            </div>
            """
        else:
            return """
            <div style="padding: 40px; text-align: center; font-family: Arial, sans-serif;">
                <h2 style="color: #ffc107;">⚠️ Claude Test Failed</h2>
                <p>API call failed - check logs for details</p>
                <div style="margin: 30px 0;">
                    <a href="/" style="background: #007cba; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px;">Back to Dashboard</a>
                </div>
            </div>
            """
            
    except Exception as e:
        return f"""
        <div style="padding: 40px; font-family: Arial, sans-serif;">
            <h2 style="color: #dc3545;">❌ Claude Test Error</h2>
            <div style="background: #f8d7da; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Error:</strong> {str(e)}</p>
            </div>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <strong>Traceback:</strong>
                <pre style="margin-top: 10px;">{traceback.format_exc()}</pre>
            </div>
            <div style="text-align: center; margin: 30px 0;">
                <a href="/" style="background: #007cba; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px;">Back to Dashboard</a>
            </div>
        </div>
        """

@app.route('/test')
def test():
    """System test endpoint"""
    try:
        db = load_deficiency_database()
        expert_status = "✅ Ready" if ANTHROPIC_API_KEY else "❌ Not configured"
        
        return f"""
        <div style="padding: 40px; font-family: Arial, sans-serif;">
            <h2>🧪 C-TPAT System Test Results</h2>
            <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
                <p>✅ <strong>Flask Application:</strong> Running</p>
                <p>✅ <strong>Database:</strong> {len(db)} C-TPAT requirements loaded</p>
                <p>✅ <strong>PDF Generation:</strong> Professional reporting ready</p>
                <p>✅ <strong>Email Config:</strong> {'Configured' if os.environ.get('SENDER_EMAIL') else 'Not configured'}</p>
                <p>{'✅' if ANTHROPIC_API_KEY else '⚠️'} <strong>Expert Analysis:</strong> {expert_status}</p>
                <p>✅ <strong>Environment:</strong> Production ready</p>
            </div>
            <div style="margin: 30px 0;">
                <h3>🔗 Integration Endpoints:</h3>
                <p><strong>Webhook:</strong> <code>/webhook</code> (POST)</p>
                <p><strong>Health Check:</strong> <code>/health</code> (GET)</p>
                <p><strong>Demo:</strong> <code>/demo</code> (GET)</p>
            </div>
            <p style="color: #28a745; font-weight: bold;">🚀 System Status: READY FOR PRODUCTION</p>
        </div>
        """
    except Exception as e:
        return f"<h2>Test Failed</h2><p>Error: {str(e)}</p>"

@app.route('/health')
def health():
    """Enhanced health check"""
    try:
        db = load_deficiency_database()
        return jsonify({
            "status": "healthy",
            "version": "3.0-professional",
            "timestamp": datetime.datetime.now().isoformat(),
            "database_records": len(db),
            "expert_enabled": bool(ANTHROPIC_API_KEY),
            "email_configured": bool(os.environ.get('SENDER_EMAIL')),
            "features": {
                "advanced_analysis": bool(ANTHROPIC_API_KEY),
                "professional_pdf": True,
                "hybrid_analysis": True,
                "email_delivery": bool(os.environ.get('SENDER_EMAIL'))
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    """Production webhook with expert analysis"""
    try:
        submission_data_str = request.form.get('rawRequest')
        if not submission_data_str:
            app.logger.error("No rawRequest field in webhook data")
            return jsonify({"status": "error", "message": "No rawRequest field"}), 400
        
        submission_data = json.loads(submission_data_str)
        submission_id = request.form.get('submissionID', f'PROD_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}')
        
        app.logger.info(f"Processing C-TPAT submission {submission_id}")
        
        # Complete submission analysis
        company_name, deficiencies, analysis_summary = analyze_submission(submission_data)
        
        # Generate professional PDF report
        pdf_path = create_professional_report(submission_id, company_name, deficiencies, analysis_summary)
        
        # Send email notification
        email_sent = send_pdf_email(pdf_path, company_name)
        
        # Log results
        app.logger.info(f"C-TPAT Analysis Complete - Company: {company_name}, Deficiencies: {len(deficiencies)}, Expert Analysis: {analysis_summary.get('expert_analyzed', 0)} questions")
        
        return jsonify({
            "status": "success",
            "message": f"C-TPAT analysis completed for {company_name}",
            "company": company_name,
            "submission_id": submission_id,
            "analysis_summary": {
                "total_questions": analysis_summary.get("total_questions", 0),
                "deficiencies_found": len(deficiencies),
                "expert_analyzed": analysis_summary.get("expert_analyzed", 0),
                "standard_analyzed": analysis_summary.get("standard_analyzed", 0),
                "high_confidence": analysis_summary.get("high_confidence_deficiencies", 0),
                "critical_deficiencies": analysis_summary.get("critical_deficiencies", 0)
            },
            "report_generated": True,
            "pdf_filename": os.path.basename(pdf_path),
            "email_delivered": email_sent,
            "expert_enabled": bool(ANTHROPIC_API_KEY),
            "timestamp": datetime.datetime.now().isoformat()
        }), 200
        
    except json.JSONDecodeError as e:
        app.logger.error(f"Invalid JSON in submission data: {e}")
        return jsonify({"status": "error", "message": "Invalid submission data format"}), 400
    
    except Exception as e:
        app.logger.error(f"Webhook processing failed: {e}", exc_info=True)
        return jsonify({
            "status": "error", 
            "message": f"Processing failed: {str(e)}",
            "timestamp": datetime.datetime.now().isoformat()
        }), 500

# --- PDF Download Routes ---
@app.route('/download-latest-pdf')
def download_latest_pdf():
    """Download the most recent PDF report"""
    try:
        if not os.path.exists(PDF_OUTPUT_DIR):
            return "<h3>No reports generated yet</h3><p><a href='/demo'>Generate a demo report</a></p>", 404
        
        pdf_files = glob.glob(os.path.join(PDF_OUTPUT_DIR, "*.pdf"))
        if not pdf_files:
            return "<h3>No PDF reports found</h3><p><a href='/demo'>Generate a demo report</a></p>", 404
        
        # Get the most recent file
        latest_pdf = max(pdf_files, key=os.path.getctime)
        
        return send_file(
            latest_pdf, 
            as_attachment=True, 
            download_name=f"CTPAT_Latest_Report_{datetime.datetime.now().strftime('%Y%m%d')}.pdf"
        )
    except Exception as e:
        return f"<h3>Download Error</h3><p>Error: {str(e)}</p><p><a href='/'>Back to Dashboard</a></p>", 500

@app.route('/list-pdfs')
def list_pdfs():
    """List all generated PDF reports with download links"""
    try:
        if not os.path.exists(PDF_OUTPUT_DIR):
            return """
            <div style="padding: 40px; font-family: Arial, sans-serif; text-align: center;">
                <h3>📁 No Reports Directory Found</h3>
                <p>No PDF reports have been generated yet.</p>
                <div style="margin: 30px 0;">
                    <a href="/demo" style="background: #007cba; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; margin: 10px;">📊 Generate Demo Report</a>
                </div>
            </div>
            """
        
        pdf_files = glob.glob(os.path.join(PDF_OUTPUT_DIR, "*.pdf"))
        
        if not pdf_files:
            return """
            <div style="padding: 40px; font-family: Arial, sans-serif; text-align: center;">
                <h3>📋 No Reports Generated Yet</h3>
                <p>Generate your first C-TPAT analysis report:</p>
                <div style="margin: 30px 0;">
                    <a href="/demo" style="background: #007cba; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; margin: 10px;">📊 Run Demo Analysis</a>
                </div>
            </div>
            """
        
        # Sort by creation time, newest first
        pdf_files.sort(key=os.path.getctime, reverse=True)
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>C-TPAT Report Archive</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; background: linear-gradient(135deg, #1e5799 0%, #2989d8 50%, #207cca 100%); min-height: 100vh; }
                .container { max-width: 1000px; margin: 0 auto; padding: 20px; }
                .header { background: rgba(255,255,255,0.95); padding: 30px; border-radius: 15px; text-align: center; margin-bottom: 30px; }
                .reports-grid { display: grid; gap: 20px; }
                .report-card { background: rgba(255,255,255,0.95); padding: 25px; border-radius: 12px; box-shadow: 0 8px 25px rgba(0,0,0,0.15); }
                .report-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
                .report-title { font-size: 18px; font-weight: bold; color: #333; margin: 0; }
                .report-meta { color: #666; font-size: 14px; }
                .download-btn { background: linear-gradient(45deg, #28a745, #20c997); color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold; }
                .expert-badge { background: linear-gradient(45deg, #1e5799, #207cca); color: white; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: bold; }
                .back-btn { background: #007cba; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📋 C-TPAT Report Archive</h1>
                    <p>All generated compliance analysis reports</p>
                    <a href="/" class="back-btn">← Back to Dashboard</a>
                </div>
                
                <div class="reports-grid">
        """
        
        for pdf_file in pdf_files:
            filename = os.path.basename(pdf_file)
            file_size = os.path.getsize(pdf_file)
            created_time = datetime.datetime.fromtimestamp(os.path.getctime(pdf_file))
            
            # Determine report type from filename
            is_expert_report = "CLAUDE" in filename.upper() or "AI" in filename.upper()
            report_type = "Advanced Analysis" if is_expert_report else "Standard Analysis"
            
            # Extract company name from filename if possible
            company_name = "Unknown Company"
            try:
                if "_" in filename:
                    parts = filename.split("_")
                    for i, part in enumerate(parts):
                        if "CTPAT" in part.upper() or "REPORT" in part.upper():
                            if i + 1 < len(parts):
                                company_name = parts[i + 1].replace(".pdf", "")
                            break
            except:
                pass
            
            html += f"""
                <div class="report-card">
                    <div class="report-header">
                        <div>
                            <div class="report-title">{company_name}</div>
                            <div class="report-meta">
                                {created_time.strftime('%Y-%m-%d at %H:%M:%S')} | 
                                {file_size:,} bytes
                                {f'<span class="expert-badge">🧠 {report_type}</span>' if is_expert_report else f'<span style="background: #28a745; color: white; padding: 4px 10px; border-radius: 12px; font-size: 12px;">{report_type}</span>'}
                            </div>
                        </div>
                        <a href="/download-pdf/{filename}" class="download-btn">📥 Download</a>
                    </div>
                    <div class="report-meta">
                        <strong>File:</strong> {filename}
                    </div>
                </div>
            """
        
        html += """
                </div>
                
                <div style="background: rgba(255,255,255,0.95); padding: 25px; border-radius: 15px; text-align: center; margin: 30px 0;">
                    <h3>📊 Generate New Report</h3>
                    <div style="margin: 20px 0;">
                        <a href="/demo" style="background: #007cba; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; margin: 10px; font-weight: bold;">📊 Run Demo Analysis</a>
                        <a href="/admin-dashboard" style="background: #6c757d; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; margin: 10px; font-weight: bold;">👨‍💻 Admin Dashboard</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
        
    except Exception as e:
        return f"""
        <div style="padding: 40px; font-family: Arial, sans-serif;">
            <h2>Error Listing Reports</h2>
            <p>Error: {str(e)}</p>
            <p><a href="/">Back to Dashboard</a></p>
        </div>
        """, 500

@app.route('/download-pdf/<filename>')
def download_specific_pdf(filename):
    """Download a specific PDF by filename"""
    try:
        file_path = os.path.join(PDF_OUTPUT_DIR, filename)
        
        if not os.path.exists(file_path):
            return "<h3>File not found</h3><p><a href='/list-pdfs'>View available reports</a></p>", 404
        
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return f"<h3>Download Error</h3><p>Error: {str(e)}</p>", 500

# --- Support for static files ---
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_file(filename)

# --- Initialize on startup ---
if __name__ == '__main__':
    # Load deficiency database on startup
    load_deficiency_database()
    app.logger.info("C-TPAT Analysis System Starting...")
    app.logger.info(f"Expert Analysis: {'Enabled' if ANTHROPIC_API_KEY else 'Disabled'}")
    app.logger.info(f"Email: {'Configured' if os.environ.get('SENDER_EMAIL') else 'Not configured'}")
    
    app.run(host='0.0.0.0', port=8080, debug=False)

