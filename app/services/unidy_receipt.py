from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import cm
import io


def generate_receipt_pdf(payment, profile):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    user = profile.user

    title_style = ParagraphStyle('title', fontSize=20, fontName='Helvetica-Bold',
                                  textColor=colors.HexColor('#7B0D1E'), spaceAfter=4)
    sub_style = ParagraphStyle('sub', fontSize=11,
                                textColor=colors.HexColor('#6B5C5C'), spaceAfter=16)
    label_style = ParagraphStyle('label', fontSize=10, fontName='Helvetica-Bold',
                                  textColor=colors.HexColor('#1A0A0A'), spaceAfter=4)
    body_style = ParagraphStyle('body', fontSize=10, spaceAfter=8)
    note_style = ParagraphStyle('note', fontSize=9, textColor=colors.HexColor('#8C6E6E'),
                                 spaceAfter=12)

    story = []
    story.append(Paragraph('UNIDY', title_style))
    story.append(Paragraph('Fee Payment Receipt', sub_style))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph('PAYMENT RECEIPT', ParagraphStyle(
        'receipt_title', fontSize=14, fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1A0A0A'), spaceAfter=12, alignment=1)))

    receipt_data = [
        ['Receipt No:', f'REC-{payment.id:06d}', 'Date:', str(payment.payment_date)],
        ['Student:', user.name, 'Matricule:', user.matricule],
        ['Program:', profile.program or 'N/A', 'Semester:', f'{payment.semester_number or "N/A"}'],
    ]
    receipt_table = Table(receipt_data, colWidths=[3.5*cm, 5.5*cm, 3.5*cm, 5.5*cm])
    receipt_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#6B5C5C')),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#6B5C5C')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(receipt_table)
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph('Payment Details', label_style))
    payment_data = [
        ['Description', 'Amount (FCFA)'],
        [payment.description or 'Tuition Fee', f'{payment.amount:,.0f}'],
        ['Payment Method', payment.payment_method or 'Cash'],
        ['Reference', payment.reference or 'N/A'],
        ['', ''],
        ['TOTAL PAID', f'{payment.amount:,.0f} FCFA'],
    ]
    pay_table = Table(payment_data, colWidths=[10*cm, 6*cm])
    pay_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7B0D1E')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F4F2F2')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E8E0E0')),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (0, -1), (-1, -1), 1.5, colors.HexColor('#7B0D1E')),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))
    story.append(pay_table)

    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(
        'This is a computer-generated receipt. No signature required. '
        'For inquiries, contact the Finance Office.',
        note_style))
    story.append(Paragraph(
        f'Generated: {__import__("datetime").datetime.now().strftime("%d %B %Y %H:%M")}',
        ParagraphStyle('date', fontSize=8, textColor=colors.HexColor('#8C6E6E'))))

    doc.build(story)
    buffer.seek(0)
    return buffer
