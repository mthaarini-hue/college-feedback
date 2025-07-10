import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import inch
from myextensions import db
from models import Staff, Course, Event, Question, FeedbackResponse, QuestionResponse, Student

def generate_pdf_report(staff_id, event_id):
    """
    Generate a PDF report for a specific staff and event.
    Returns: BytesIO object containing the PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)
    elements = []
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    subtitle_style = styles['Heading2']
    normal_style = styles['Normal']

    staff = Staff.query.get_or_404(staff_id)
    event = Event.query.get_or_404(event_id)
    course = Course.query.get_or_404(staff.course_id)

    elements.append(Paragraph("Feedback Report", title_style))
    elements.append(Spacer(1, 0.25*inch))
    elements.append(Paragraph(f"Event: {event.title}", subtitle_style))
    elements.append(Paragraph(f"Course: {course.code} - {course.name}", subtitle_style))
    elements.append(Paragraph(f"Staff: {staff.name}", subtitle_style))
    elements.append(Spacer(1, 0.5*inch))

    feedback_responses = FeedbackResponse.query.filter_by(staff_id=staff_id, event_id=event_id).all()
    questions = Question.query.all()
    question_data = []
    for question in questions:
        ratings = []
        for feedback in feedback_responses:
            response = QuestionResponse.query.filter_by(feedback_id=feedback.id, question_id=question.id).first()
            if response:
                ratings.append(response.rating)
        if ratings:
            avg = sum(ratings) / len(ratings)
            question_data.append((question.text, round(avg, 2), len(ratings)))
        else:
            question_data.append((question.text, 0, 0))

    table_data = [['Question', 'Average Rating', 'Responses']]
    table_data.extend(question_data)
    table = Table(table_data, colWidths=[4*inch, 1*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.5*inch))

    drawing = Drawing(500, 250)
    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 150
    bc.width = 400
    bc.data = [[data[1] for data in question_data]]
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 4
    bc.valueAxis.valueStep = 1
    bc.categoryAxis.labels = [f"Q{i+1}" for i in range(len(question_data))]
    bc.barLabelFormat = '%.2f'
    drawing.add(bc)
    elements.append(drawing)
    elements.append(Spacer(1, 0.5*inch))

    responded_students = db.session.query(Student.id).join(FeedbackResponse, Student.id == FeedbackResponse.student_id)\
                         .filter(FeedbackResponse.staff_id == staff_id, FeedbackResponse.event_id == event_id)\
                         .distinct().count()
    total_students = Student.query.count()
    elements.append(Paragraph("Participation Statistics", subtitle_style))
    elements.append(Paragraph(f"Responses: {responded_students} students", normal_style))
    elements.append(Paragraph(f"Total Students: {total_students} students", normal_style))
    if total_students > 0:
        response_rate = (responded_students / total_students) * 100
        elements.append(Paragraph(f"Response Rate: {response_rate:.2f}%", normal_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer
