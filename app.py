from flask import Flask, render_template, request, send_file, redirect, url_for
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from datetime import datetime
import io

app = Flask(__name__)

# ---------------- SSLC GRADE SYSTEM ----------------
def calculate_grade(percentage):
    if percentage >= 85:
        return "Distinction"
    elif percentage >= 60:
        return "First Class"
    elif percentage >= 50:
        return "Second Class"
    elif percentage >= 35:
        return "Pass Class"
    else:
        return "Fail"

# ---------------- WATERMARK ----------------
def add_watermark(pdf, width, height, text):
    pdf.saveState()
    pdf.setFont("Helvetica-Bold", 40)
    pdf.setFillGray(0.9)
    pdf.translate(width / 2, height / 2)
    pdf.rotate(45)
    pdf.drawCentredString(0, 0, text)
    pdf.restoreState()

# ---------------- SSLC INSIGHTS ----------------
def generate_insights(percentage, failed, subject_percentages):
    insights = []

    if failed:
        insights.append(
            "The student has failed in one or more subjects as per Karnataka SSLC rules."
        )
    else:
        insights.append(
            "The student has passed all subjects as per Karnataka SSLC board norms."
        )

    if percentage >= 85:
        insights.append("Overall performance is excellent and falls under Distinction.")
    elif percentage >= 60:
        insights.append("Overall performance is good and qualifies for First Class.")
    elif percentage >= 50:
        insights.append("Overall performance is satisfactory with Second Class.")
    else:
        insights.append("Minimum passing performance achieved. Needs improvement.")

    insights.append(f"Highest subject percentage: {max(subject_percentages)}%.")
    insights.append(f"Lowest subject percentage: {min(subject_percentages)}%.")

    return insights

# ---------------- MAIN PAGE ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    result = {}
    error = ""

    if request.method == "POST":
        try:
            name = request.form["student_name"].strip()
            subjects = request.form.getlist("subject_name[]")
            marks_list = request.form.getlist("marks[]")

            if not name:
                raise ValueError("Student name is required")

            total_obtained = 0
            total_max = 0
            failed = False
            subject_data = []

            for subject, mark in zip(subjects, marks_list):
                mark = int(mark)

                if subject.lower() == "kannada":
                    if mark < 0 or mark > 125:
                        raise ValueError("Kannada marks must be between 0 and 125")
                    max_marks = 125
                else:
                    if mark < 0 or mark > 100:
                        raise ValueError(f"{subject} marks must be between 0 and 100")
                    max_marks = 100

                percentage = (mark / max_marks) * 100

                if percentage < 35:
                    failed = True

                total_obtained += mark
                total_max += max_marks

                subject_data.append({
                    "subject": subject,
                    "marks": mark,
                    "percentage": round(percentage, 2)
                })

            overall_percentage = (total_obtained / total_max) * 100

            result = {
                "name": name,
                "subjects": subject_data,
                "average": round(overall_percentage, 2),
                "grade": calculate_grade(overall_percentage),
                "status": "FAIL" if failed else "PASS"
            }

        except Exception as e:
            error = str(e)

    return render_template("index.html", result=result, error=error)

# ---------------- PDF DOWNLOAD ----------------
@app.route("/download_pdf", methods=["POST"])
def download_pdf():
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    name = request.form["name"]
    percentage = float(request.form["average"])
    grade = request.form["grade"]
    raw_subjects = request.form.getlist("subjects[]")

    subjects = []
    subject_percentages = []
    failed = False

    total_obtained = 0
    total_max = 0

    for item in raw_subjects:
        subject, mark = item.split(":")
        mark = int(mark)

        if subject.lower() == "kannada":
            max_marks = 125
        else:
            max_marks = 100

        pct = (mark / max_marks) * 100
        if pct < 35:
            failed = True

        total_obtained += mark
        total_max += max_marks

        subjects.append(subject)
        subject_percentages.append(round(pct, 2))

    insights = generate_insights(percentage, failed, subject_percentages)

    # WATERMARK
    add_watermark(pdf, width, height, "KARNATAKA SSLC")

    # HEADER
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(
        width / 2,
        height - 40,
        "Karnataka SSLC Examination Result"
    )

    pdf.setFont("Helvetica", 11)
    pdf.drawString(
        50,
        height - 70,
        "Board: Karnataka Secondary Education Examination Board (KSEEB)"
    )

    # STUDENT DETAILS
    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, height - 110, f"Student Name: {name}")
    pdf.drawString(50, height - 140, f"Overall Percentage: {round((total_obtained/total_max)*100, 2)}%")
    pdf.drawString(50, height - 170, f"Class: {grade}")

    # ---------------- BAR GRAPH ----------------
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, height - 210, "Subject-wise Performance (Percentage)")

    graph_left = 80
    graph_bottom = height - 480
    graph_width = 420
    graph_height = 230

    pdf.line(graph_left, graph_bottom, graph_left, graph_bottom + graph_height)
    pdf.line(graph_left, graph_bottom, graph_left + graph_width, graph_bottom)

    pdf.setFont("Helvetica", 9)
    for i in range(0, 101, 20):
        y = graph_bottom + (i / 100) * graph_height
        pdf.drawString(graph_left - 30, y - 3, str(i))
        pdf.line(graph_left - 3, y, graph_left, y)

    bar_width = graph_width / (len(subject_percentages) * 2)
    gap = bar_width

    for i, pct in enumerate(subject_percentages):
        bar_height = (pct / 100) * graph_height
        x = graph_left + gap + i * (bar_width + gap)

        pdf.setFillColor(colors.lightgreen if pct >= 35 else colors.salmon)
        pdf.rect(x, graph_bottom, bar_width, bar_height, fill=1)

        pdf.setFillColor(colors.black)
        pdf.drawCentredString(x + bar_width / 2, graph_bottom - 15, subjects[i][:6])
        pdf.drawCentredString(x + bar_width / 2, graph_bottom + bar_height + 5, f"{pct}%")

    # ---------------- INSIGHTS ----------------
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, graph_bottom - 50, "Academic Performance Insights")

    pdf.setFont("Helvetica", 11)
    y = graph_bottom - 80
    for insight in insights:
        pdf.drawString(60, y, f"- {insight}")
        y -= 18

    # FOOTER
    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, 30, f"Generated on: {datetime.now().strftime('%d-%m-%Y')}")
    pdf.drawRightString(
        width - 50,
        30,
        "Karnataka SSLC Result Analysis System"
    )

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="karnataka_sslc_result.pdf",
        mimetype="application/pdf"
    )

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
