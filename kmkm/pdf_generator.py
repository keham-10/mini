import os
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing, Rect, Circle
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderPDF
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import base64
from PIL import Image as PILImage


class ProductResultsPDFGenerator:
    def __init__(self, product, responses, scores, user):
        self.product = product
        self.responses = responses
        self.scores = scores
        self.user = user
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()

    def setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2c3e50')
        )
        
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=12,
            textColor=colors.HexColor('#34495e')
        )
        
        self.subheading_style = ParagraphStyle(
            'CustomSubheading',
            parent=self.styles['Heading3'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=10,
            textColor=colors.HexColor('#7f8c8d')
        )

    def generate_pdf(self, filename):
        """Generate the complete PDF report"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                              rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        story = []
        
        # Title page
        story.extend(self.create_title_page())
        story.append(PageBreak())
        
        # Executive summary
        story.extend(self.create_executive_summary())
        story.append(PageBreak())
        
        # Detailed results
        story.extend(self.create_detailed_results())
        story.append(PageBreak())
        
        # Questionnaire responses
        story.extend(self.create_questionnaire_responses())
        story.append(PageBreak())
        
        # Recommendations
        story.extend(self.create_recommendations())
        
        doc.build(story)
        
        # Save to file
        pdf_data = buffer.getvalue()
        buffer.close()
        
        with open(filename, 'wb') as f:
            f.write(pdf_data)
        
        return pdf_data

    def create_title_page(self):
        """Create the title page"""
        story = []
        
        # Main title
        title = Paragraph("Security Maturity Assessment Report", self.title_style)
        story.append(title)
        story.append(Spacer(1, 0.5*inch))
        
        # Product name
        product_title = Paragraph(f"Product: {self.product.name}", self.heading_style)
        story.append(product_title)
        story.append(Spacer(1, 0.3*inch))
        
        # Client information
        client_info = [
            ["Organization:", self.user.organization or "N/A"],
            ["Client:", f"{self.user.username} ({self.user.email})"],
            ["Assessment Date:", datetime.now().strftime("%B %d, %Y")],
            ["Product URL:", self.product.product_url],
            ["Programming Language:", self.product.programming_language],
            ["Cloud Platform:", self.product.cloud_platform],
            ["CI/CD Platform:", self.product.cicd_platform]
        ]
        
        info_table = Table(client_info, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey)
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 1*inch))
        
        # Overall score visualization
        if self.scores:
            overall_score = sum(score.total_score for score in self.scores) / len(self.scores)
            story.extend(self.create_score_visualization(overall_score))
        
        return story

    def create_executive_summary(self):
        """Create executive summary section"""
        story = []
        
        story.append(Paragraph("Executive Summary", self.title_style))
        story.append(Spacer(1, 0.3*inch))
        
        if self.scores:
            # Calculate metrics
            total_questions = len(self.responses)
            completed_questions = len([r for r in self.responses if r.answer])
            avg_score = sum(score.total_score for score in self.scores) / len(self.scores)
            
            # Summary metrics table
            metrics = [
                ["Metric", "Value"],
                ["Total Questions", str(total_questions)],
                ["Completed Questions", str(completed_questions)],
                ["Completion Rate", f"{(completed_questions/total_questions*100):.1f}%" if total_questions > 0 else "0%"],
                ["Overall Maturity Score", f"{avg_score:.1f}/5.0"],
                ["Maturity Level", self.get_maturity_level(avg_score)]
            ]
            
            metrics_table = Table(metrics, colWidths=[3*inch, 2*inch])
            metrics_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
            ]))
            
            story.append(metrics_table)
            story.append(Spacer(1, 0.5*inch))
            
            # Key findings
            story.append(Paragraph("Key Findings", self.heading_style))
            
            findings = self.generate_key_findings(avg_score)
            for finding in findings:
                story.append(Paragraph(f"• {finding}", self.styles['Normal']))
                story.append(Spacer(1, 6))
        
        return story

    def create_detailed_results(self):
        """Create detailed results by dimension"""
        story = []
        
        story.append(Paragraph("Detailed Results by Dimension", self.title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Group responses by section
        sections = {}
        for response in self.responses:
            if response.section not in sections:
                sections[response.section] = []
            sections[response.section].append(response)
        
        for section_name, section_responses in sections.items():
            story.append(Paragraph(section_name, self.heading_style))
            
            # Calculate section score
            section_scores = [r.score for r in section_responses if r.score is not None]
            if section_scores:
                avg_section_score = sum(section_scores) / len(section_scores)
                max_section_score = sum(r.max_score for r in section_responses if r.max_score is not None)
                
                score_text = f"Section Score: {avg_section_score:.1f}/{max_section_score} ({(avg_section_score/max_section_score*100):.1f}%)"
                story.append(Paragraph(score_text, self.styles['Normal']))
                story.append(Spacer(1, 12))
            
            # Section questions summary
            completed = len([r for r in section_responses if r.answer])
            total = len(section_responses)
            
            summary_text = f"Questions: {completed}/{total} completed"
            story.append(Paragraph(summary_text, self.styles['Normal']))
            story.append(Spacer(1, 20))
        
        return story

    def create_questionnaire_responses(self):
        """Create detailed questionnaire responses"""
        story = []
        
        story.append(Paragraph("Questionnaire Responses", self.title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Group by section
        sections = {}
        for response in self.responses:
            if response.section not in sections:
                sections[response.section] = []
            sections[response.section].append(response)
        
        for section_name, section_responses in sections.items():
            story.append(Paragraph(section_name, self.heading_style))
            story.append(Spacer(1, 12))
            
            for i, response in enumerate(section_responses, 1):
                # Question
                question_text = f"Q{i}: {response.question}"
                story.append(Paragraph(question_text, self.subheading_style))
                
                # Answer
                answer_text = f"Answer: {response.answer or 'Not answered'}"
                story.append(Paragraph(answer_text, self.styles['Normal']))
                
                # Score if available
                if response.score is not None and response.max_score is not None:
                    score_text = f"Score: {response.score}/{response.max_score}"
                    story.append(Paragraph(score_text, self.styles['Normal']))
                
                # Client comments
                if response.client_comment:
                    comment_text = f"Comments: {response.client_comment}"
                    story.append(Paragraph(comment_text, self.styles['Normal']))
                
                story.append(Spacer(1, 15))
        
        return story

    def create_recommendations(self):
        """Create recommendations section"""
        story = []
        
        story.append(Paragraph("Recommendations", self.title_style))
        story.append(Spacer(1, 0.3*inch))
        
        if self.scores:
            avg_score = sum(score.total_score for score in self.scores) / len(self.scores)
            recommendations = self.generate_recommendations(avg_score)
            
            for rec in recommendations:
                story.append(Paragraph(f"• {rec}", self.styles['Normal']))
                story.append(Spacer(1, 12))
        
        return story

    def create_score_visualization(self, overall_score):
        """Create a simple score visualization"""
        story = []
        
        # Create a simple table-based visualization
        score_data = [
            ["Overall Maturity Score", f"{overall_score:.1f}/5.0"],
            ["Maturity Level", self.get_maturity_level(overall_score)],
            ["Progress", f"{(overall_score/5*100):.1f}%"]
        ]
        
        score_table = Table(score_data, colWidths=[3*inch, 2*inch])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ecf0f1')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 14),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(score_table)
        return story

    def get_maturity_level(self, score):
        """Get maturity level description"""
        if score < 1:
            return "Level 1 - Initial"
        elif score < 2:
            return "Level 2 - Developing"
        elif score < 3:
            return "Level 3 - Defined"
        elif score < 4:
            return "Level 4 - Managed"
        else:
            return "Level 5 - Optimized"

    def generate_key_findings(self, overall_score):
        """Generate key findings based on score"""
        findings = []
        
        if overall_score >= 4:
            findings.append("Your organization demonstrates excellent security maturity practices")
            findings.append("Continue to maintain and optimize current security processes")
        elif overall_score >= 3:
            findings.append("Your organization has well-defined security processes")
            findings.append("Focus on implementing consistent management practices")
        elif overall_score >= 2:
            findings.append("Your organization has basic security processes in place")
            findings.append("Work on formalizing and documenting security procedures")
        else:
            findings.append("Your organization needs significant improvement in security practices")
            findings.append("Prioritize establishing fundamental security processes")
        
        return findings

    def generate_recommendations(self, overall_score):
        """Generate recommendations based on score"""
        recommendations = []
        
        if overall_score < 2:
            recommendations.extend([
                "Establish basic security policies and procedures",
                "Implement fundamental access controls",
                "Create incident response procedures",
                "Establish regular security training programs"
            ])
        elif overall_score < 3:
            recommendations.extend([
                "Document all security processes and procedures",
                "Implement regular security assessments",
                "Establish security metrics and monitoring",
                "Create formal risk management processes"
            ])
        elif overall_score < 4:
            recommendations.extend([
                "Implement automated security monitoring",
                "Establish security performance metrics",
                "Create continuous improvement processes",
                "Implement advanced threat detection"
            ])
        else:
            recommendations.extend([
                "Continue optimizing security processes",
                "Share best practices across the organization",
                "Implement predictive security analytics",
                "Lead industry security initiatives"
            ])
        
        return recommendations


def generate_product_pdf(product, responses, scores, user, filename):
    """Main function to generate PDF report"""
    generator = ProductResultsPDFGenerator(product, responses, scores, user)
    return generator.generate_pdf(filename)