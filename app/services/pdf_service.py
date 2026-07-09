from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import cm
import io

def generate_student_report(student, profile, results):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("title", fontSize=22, fontName="Helvetica-Bold",
                                  textColor=colors.HexColor("#1B4F72"), spaceAfter=6)
    sub_style   = ParagraphStyle("sub", fontSize=11,
                                  textColor=colors.HexColor("#17A589"), spaceAfter=20)
    label_style = ParagraphStyle("label", fontSize=10, fontName="Helvetica-Bold",
                                  textColor=colors.HexColor("#1B4F72"), spaceAfter=4)
    body_style  = ParagraphStyle("body", fontSize=10, spaceAfter=12)

    story = []
    story.append(Paragraph("REDI Platform", title_style))
    story.append(Paragraph("Real-time Employability & Digital Intelligence", sub_style))
    story.append(Paragraph(f"Rapport de : {student.name}", label_style))
    story.append(Paragraph(f"Matricule : {student.matricule} | Departement : {student.department or 'N/A'}", body_style))
    story.append(Spacer(1, 0.3*cm))

    eri = profile.eri_score if profile else 0
    story.append(Paragraph(f"Score ERI : {eri}%", label_style))
    filled = max(1, int(eri / 100 * 15))
    empty  = 15 - filled
    bar = Table([["",""]], colWidths=[filled*cm, empty*cm], rowHeights=[14])
    bar.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(0,0), colors.HexColor("#17A589")),
        ("BACKGROUND",(1,0),(1,0), colors.HexColor("#E5E8EC")),
    ]))
    story.append(bar)
    story.append(Spacer(1, 0.5*cm))

    if results:
        story.append(Paragraph("Resultats academiques", label_style))
        data = [["Semestre","CA","Examen","Score global"]]
        for r in results:
            data.append([f"Semestre {r.semester_number}", f"{r.ca_score}/20", f"{r.exam_score}/20", f"{r.overall_score}%"])
        t = Table(data, colWidths=[7*cm,3*cm,3*cm,3*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0), colors.HexColor("#1B4F72")),
            ("TEXTCOLOR",(0,0),(-1,0), colors.white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("FONTSIZE",(0,0),(-1,-1),9),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#F4F6F9")]),
            ("GRID",(0,0),(-1,-1),0.5, colors.HexColor("#E5E8EC")),
            ("PADDING",(0,0),(-1,-1),6),
        ]))
        story.append(t)

    doc.build(story)
    buffer.seek(0)
    return buffer
