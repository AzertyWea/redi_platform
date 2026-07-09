import sys
sys.path.insert(0, ".")
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

doc = SimpleDocTemplate("sample_timetable.pdf", pagesize=landscape(A4), topMargin=1.5*cm, bottomMargin=1.5*cm)
styles = getSampleStyleSheet()
elements = [
    Paragraph("INSTITUT UNIVERSITAIRE DE LA COTE - IUC DOUALA", styles['Title']),
    Paragraph("Weekly Timetable - L2 Software Engineering - Group A - Semester 3 - 2026-2027", styles['Heading2']),
    Spacer(1, 16),
]

# Format: Day | Time | Course Code | Course Name | Teacher | Room
# This fixed column structure is what the extraction algorithm will be designed against.
rows = [
    ["Day", "Time", "Code", "Course", "Teacher", "Room"],
    ["Monday", "08:00 - 10:00", "SWEN301", "Advanced Topics - Software Engineering", "Dr. Kenfack Amina", "Room A101"],
    ["Monday", "10:00 - 12:00", "SWEN302", "Research Methods - Software Engineering", "Dr. Mbarga Kevin", "Room A102"],
    ["Tuesday", "08:00 - 10:00", "SWEN303", "Professional Skills - Software Engineering", "Dr. Kenfack Amina", "Room B201"],
    ["Wednesday", "13:00 - 15:00", "SWEN304", "Capstone Project - Software Engineering", "Dr. Nguemo Pascal", "Amphitheater 1"],
    ["Thursday", "10:00 - 12:00", "SWEN305", "Fundamentals - Software Engineering", "Dr. Mbarga Kevin", "Room C301"],
    ["Friday", "15:00 - 17:00", "SWEN306", "Practicum - Software Engineering", "Dr. Nguemo Pascal", "Room A103"],
]

table = Table(rows, colWidths=[3*cm, 4*cm, 2.5*cm, 8*cm, 5*cm, 3.5*cm])
table.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#7B0D1E")),
    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
    ('FONTSIZE', (0,0), (-1,-1), 9),
    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#DDDDDD")),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F8F5F5")]),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('TOPPADDING', (0,0), (-1,-1), 8),
    ('BOTTOMPADDING', (0,0), (-1,-1), 8),
]))
elements.append(table)
doc.build(elements)
print("sample_timetable.pdf generated")
