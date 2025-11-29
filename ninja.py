import streamlit as st
from datetime import date
import base64
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch

st.set_page_config(page_title="Invoice Ninja AI", layout="centered")

st.title("Invoice Ninja AI")
st.markdown("### Generate beautiful PDF invoices in 3 seconds — no signup, no BS")

# Perfect sidebar (this removes the ugly purple box)
with st.sidebar:
    st.image("https://i.imgur.com/8QvJ5eK.png", width=200)
    st.markdown("**Built in one night**")
    st.markdown("Made for freelancers who hate Canva & Word")
    st.caption("© 2025 Invoice Ninja AI")

# Rest of the app (your fields, items, PDF generator)
c1, c2 = st.columns(2)
with c1:
    your_name = st.text_input("Your Name / Business", "Alex Rivers")
    your_email = st.text_input("Your Email", "alex@company.com")
    your_address = st.text_area("Your Address", "123 Main St\nLos Angeles, CA 90001", height=100)
with c2:
    client_name = st.text_input("Client Name", "Acme Corp")
    client_email = st.text_input("Client Email", "billing@acme.com")
    client_address = st.text_area("Client Address", "456 Corp Blvd\nSan Francisco, CA", height=100)

d1, d2, d3 = st.columns(3)
with d1:
    invoice_no = st.text_input("Invoice #", "INV-2025-001")
with d2:
    invoice_date = st.date_input("Invoice Date", date.today())
with d3:
    due_date = st.date_input("Due Date", date.today())

st.markdown("### Line Items")
items = []
for i in range(5):
    with st.expander(f"Item {i+1}" + (" (optional)" if i>0 else ""), expanded=(i==0)):
        col1, col2, col3 = st.columns([3,1,1])
        desc = col1.text_input("Description", "Design work", key=f"d{i}")
        qty = col2.number_input("Qty", 1, 100, 1, key=f"q{i}")
        rate = col3.number_input("Rate ($)", 0.0, 99999.0, 350.0, key=f"r{i}")
        if desc.strip():
            items.append({"desc": desc, "qty": qty, "rate": rate, "total": qty*rate})

tax_rate = st.slider("Tax Rate (%)", 0, 30, 8)
notes = st.text_area("Notes (optional)", "Thank you! Payment via PayPal/Wise/bank.")

subtotal = sum(item["total"] for item in items)
tax = round(subtotal * tax_rate / 100, 2)
total = subtotal + tax

m1, m2, m3 = st.columns([2,1,1])
with m2: st.metric("Subtotal", f"${subtotal:,.2f}")
with m3: st.metric("Total", f"\( {total:,.2f}", f"+ \){tax:,.2f} tax")

def make_pdf():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.7*inch)
    styles = getSampleStyleSheet()
    story = []

    logo = Image("https://i.imgur.com/8QvJ5eK.png", width=80, height=80)
    header = Table([[logo, Paragraph(f"<font size=18><b>INVOICE</b></font><br/>#{invoice_no}", styles["Normal"])]])
    header.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(header)
    story.append(Spacer(1,20))

    bill_data = [
        [Paragraph(f"<b>From:</b><br/>{your_name}<br/>{your_email}<br/>{your_address.replace('\n','<br/>')}", styles["Normal"]),
         Paragraph(f"<b>Bill To:</b><br/>{client_name}<br/>{client_email}<br/>{client_address.replace('\n','<br/>')}", styles["Normal"])]
    ]
    bill_table = Table(bill_data, colWidths=[2.8*inch, 2.8*inch])
    bill_table.setStyle(TableStyle([("BOX",(0,0),(-1,-1),1,colors.lightgrey)]))
    story.append(bill_table)
    story.append(Spacer(1,30))

    line_data = [["Description","Qty","Rate","Amount"]]
    for it in items:
        line_data.append([it["desc"], str(it["qty"]), f"\( {it['rate']:,.2f}", f" \){it['total']:,.2f}"])
    line_data += [["","", "Subtotal", f"\( {subtotal:,.2f}"], ["","", f"Tax {tax_rate}%", f" \){tax:,.2f}"], ["","", Paragraph("<b>Total</b>"), Paragraph(f"<b>${total:,.2f}</b>")]]
    line_table = Table(line_data, colWidths=[3.2*inch,0.7*inch,1*inch,1*inch])
    line_table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#3B82F6")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),1,colors.lightgrey),
        ("ALIGN",(1,-3),(-1,-1),"RIGHT"),
        ("FONTNAME",(-2,-2),(-1,-1),"Helvetica-Bold")
    ]))
    story.append(line_table)

    if notes.strip():
        story.append(Spacer(1,20))
        story.append(Paragraph("<b>Notes</b>", styles["Normal"]))
        story.append(Paragraph(notes.replace("\n","<br/>"), styles["Normal"]))

    doc.build(story)
    buffer.seek(0)
    return buffer

if st.button("Generate & Download PDF Invoice", type="primary"):
    pdf = make_pdf()
    b64 = base64.b64encode(pdf.read()).decode()
    href = f'<a href="data:application/pdf;base64,{b64}" download="Invoice_{invoice_no}.pdf">Download Invoice Now</a>'
    st.markdown(href, unsafe_allow_html=True)
    st.success("Invoice ready! Click above to download.")
    st.balloons()

st.markdown("---")
st.markdown("Made with 💜 by drwtt91")
