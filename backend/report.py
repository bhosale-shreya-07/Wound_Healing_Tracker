import io, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

DISCLAIMER = ("This report shows measured changes in the visible wound region in photographs. "
              "It is NOT a medical diagnosis and cannot confirm infection or healing. "
              "Please consult a qualified healthcare professional.")


def build_report(wound, imgs, comps, root):
    st = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    use_cm = bool(imgs) and all(i.area_cm2 is not None for i in imgs)
    unit = "cm²" if use_cm else "px²"
    val = lambda i: i.area_cm2 if use_cm else i.area_px

    el = [Paragraph("SmartHeal - Wound Progress Report", st["Title"]),
          Paragraph(f"Wound: {wound.label} ({wound.body_location or 'n/a'})", st["Normal"]),
          Spacer(1, 10)]
    rows = [["Date", f"Area ({unit})", "Perimeter", "Change vs prev", "Notes"]]
    for i in imgs:
        c = comps.get(i.id)
        if c and c.pct_change is not None:
            pc = f"{abs(c.pct_change):.1f}% " + ("smaller" if c.pct_change >= 0 else "larger")
        else:
            pc = "-"
        note = ("manual " if i.manually_corrected else "") + ("low-confidence" if i.low_confidence else "")
        per = i.perimeter_cm if use_cm else i.perimeter_px
        rows.append([str(i.captured_on), f"{val(i):.2f}", f"{per:.2f}", pc, note])
    t = Table(rows, repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), .5, colors.grey),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey)]))
    el += [t, Spacer(1, 12)]

    if len(imgs) > 1:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot([str(i.captured_on) for i in imgs], [val(i) for i in imgs], "o-")
        ax.set_ylabel(f"Wound area ({unit})")
        ax.set_title("Measured wound area over time")
        plt.xticks(rotation=30)
        plt.tight_layout()
        g = io.BytesIO()
        fig.savefig(g, format="png")
        plt.close(fig)
        g.seek(0)
        el += [Image(g, width=400, height=200), Spacer(1, 12)]
    if imgs:
        p = os.path.join(root, imgs[-1].overlay_path)
        el += [Paragraph("Latest image with detected boundary", st["Heading3"]),
               Image(p, width=300, height=225)]
    el += [Spacer(1, 12), Paragraph(DISCLAIMER, st["Italic"])]
    doc.build(el)
    buf.seek(0)
    return buf
