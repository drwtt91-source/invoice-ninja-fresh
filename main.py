import streamlit as st
from datetime import datetime
import base64
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from io import BytesIO

st.set_page_config(page_title="Invoice Ninja AI", layout="centered")
st.title("Invoice Ninja AI")
st.markdown("### Generate beautiful PDF invoices in 3 seconds — no signup, no BS")

# Sidebar branding — FIXED
with st.sidebar:
    st.image("https://i.imgur.com/8QvJ5eK.png", width=200)
    st.markdown("**Built in one night**")
    st.markdown("Made for freelancers who hate Canva & Word")
    st.caption("© 2025 Invoice Ninja AI")

col1, col2 = st.columns(2)
with col1:
    your_name = st.text_input("Your Name / Business", "Alex Rivers")
    your_email = st.text_input("Your Email", "alex@yourcompany.com")
    your_address = st.text_area("Your Address", "123 Main St\nLos Angeles, CA 90001", height=100)

with col2:
    client_name = st.text_input("Client Name", "Acme Corp")
    client_email = st.text_input("Client Email", "billing@acme.com")
    client_address = st.text_area("Client Address", "456 Corporate Blvd\nSan Francisco, CA 94111", height=100)

st.markdown("### Invoice Details")
col1, col2, col3 = st.columns(3)
with col1:
    invoice_number = st.text_input("Invoice #", "INV-2025-001")
with col2:
    invoice_date = st.date_input("Invoice Date", datetime.today())
with col3:
    due_date = st.date_input("Due Date", datetime.today())

st.markdown("### Line Items")
items = []
for i in range(5):
    with st.expander(f"Item {i+1} {'(optional)' if i>0 else ''}", expanded=i==0):
        col1, col2, col3 = st.columns([3,1,1])
        with col1:
            desc = st.text_input("Description", "Web Design Services", key=f"desc{i}")
        with col2:
            qty = st.number_input("Qty", 1, 100, 1, key=f"qty{i}")
        with col3:
            rate = st.number_input("Rate ($)", 0.0, 10000.0, 250.0, key=f"rate{i}")
        if desc:
            items.append({"desc": desc, "qty": qty, "rate": rate, "total": qty*rate})

tax_rate = st.slider("Tax Rate (%)", 0, 30, 8)
notes = st.text_area("Additional Notes (optional)", "Thank you for your business!\nPayment via PayPal, Wise, or bank transfer.")

# Calculate totals
subtotal = sum(item["total"] for item in items if "total" in item)
tax = subtotal * (tax_rate / 100)
total = subtotal + tax

col1, col2, col3 = st.columns([2,1,1])
with col2:
    st.metric("Subtotal", f"${subtotal:,.2f}")
with col3:
    st.metric("Total", f"\( {total:,.2f}", f"+ \){tax:,.2f} tax")

# Generate PDF
def create_invoice_pdf():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.7*inch)
    styles = getSampleStyleSheet()
    story = []

    # Header
    logo = Image("https://i.imgur.com/8QvJ5eK.png", width=80, height=80)
    logo.hAlign = 'LEFT'
    header_table = Table([[logo, Paragraph(f"<font size=18><b>INVOICE</b></font><br/>#{invoice_number}", styles["Normal"])]])
    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(header_table)
    story.append(Spacer(1, 20))

    # Bill To / From
    data = [
        [Paragraph("<b>From:</b><br/>" + your_name.replace("\n","<br/>") + f"<br/>{your_email}<br/>" + your_address.replace("\n","<br/>"), styles["Normal"]),
         Paragraph("<b>Bill To:</b><br/>" + client_name + f"<br/>{client_email}<br/>" + client_address.replace("\n","<br/>"), styles["Normal"])]
    ]
    bill_table = Table(data, colWidths=[2.8*inch, 2.8*inch])
    bill_table.setStyle(TableStyle([('BOX', (0,0), (-1,-1), 1, colors.lightgrey),
                                   ('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(bill_table)
    story.append(Spacer(1, 20))

    # Invoice meta
    meta_data = [
        ["Invoice Date", str(invoice_date)],
        ["Due Date", str(due_date)],
        ["Invoice #", invoice_number],
    ]
    meta_table = Table(meta_data, colWidths=[1.5*inch, 4*inch])
    story.append(meta_table)
    story.append(Spacer(1, 30))

    # Line items table
    table_data = [["Description", "Qty", "Rate", "Amount"]]
    for item in items:
        if item["desc"]:
            table_data.append([item["desc"], str(item["qty"]), f"\( {item['rate']:,.2f}", f" \){item['total']:,.2f}"])
    table_data.append(["", "", "Subtotal", f"${subtotal:,.2f}"])
    table_data.append(["", "", f"Tax ({tax_rate}%)", f"${tax:,.2f}"])
    table_data.append(["", "", Paragraph("<b>Total</b>", styles["Normal"]), Paragraph(f"<b>${total:,.2f}</b>", styles["Normal"])])

    item_table = Table(table_data, colWidths=[3.2*inch, 0.7*inch, 1*inch, 1*inch])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#3B82F6")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (1,-3), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,-2), (-1,-1), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 1, colors.lightgrey),
    ]))
    story.append(item_table)
    story.append(Spacer(1, 30))

    # Notes
    if notes:
        story.append(Paragraph("<b>Notes</b>", styles["Normal"]))
        story.append(Paragraph(notes.replace("\n","<br/>"), styles["Normal"]))

    doc.build(story)
    buffer.seek(0)
    return buffer

if st.button("Generate & Download PDF Invoice", type="primary"):
    pdf_buffer = create_invoice_pdf()
    b64 = base64.b64encode(pdf_buffer.read()).decode()
    href = f'<a href="data:application/pdf;base64,{b64}" download="Invoice_{invoice_number}.pdf">Download Your Invoice Now</a>'
    st.markdown(href, unsafe_allow_html=True)
    st.success("Invoice ready! Click above to download.")
    st.balloons()

# Footer
st.markdown("---")
st.markdown("""
**Loving this? Unlock the full AI toolkit:**  
Get **Outfit Roaster** (£9.99 lifetime) – Unlimited AI outfit roasts with zero mercy.  
Perfect for freelancers: Bill like a pro, roast like a savage.  
[Buy Now on Gumroad →](https://drwitt.gumroad.com/l/zfbdxb)  
(30-day money-back, source code included)
""")
