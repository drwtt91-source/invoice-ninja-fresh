import streamlit as st
from datetime import datetime, timedelta
import base64
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from io import BytesIO
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from PIL import Image
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

CURRENCIES = {
    "USD": {"symbol": "$", "name": "US Dollar", "position": "before"},
    "GBP": {"symbol": "£", "name": "British Pound", "position": "before"},
    "EUR": {"symbol": "€", "name": "Euro", "position": "before"},
}

def get_db_connection():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS client_templates (
            id SERIAL PRIMARY KEY,
            template_name VARCHAR(255) NOT NULL,
            client_name VARCHAR(255),
            client_email VARCHAR(255),
            client_address TEXT,
            your_name VARCHAR(255),
            your_email VARCHAR(255),
            your_address TEXT,
            currency VARCHAR(10) DEFAULT 'USD',
            tax_rate INTEGER DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS invoice_history (
            id SERIAL PRIMARY KEY,
            invoice_number VARCHAR(100) NOT NULL,
            invoice_date DATE,
            due_date DATE,
            client_name VARCHAR(255),
            client_email VARCHAR(255),
            your_name VARCHAR(255),
            subtotal DECIMAL(12, 2),
            tax DECIMAL(12, 2),
            total DECIMAL(12, 2),
            currency VARCHAR(10) DEFAULT 'USD',
            items_json TEXT,
            pdf_data BYTEA,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            id SERIAL PRIMARY KEY,
            logo_data BYTEA,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def format_currency(amount, currency_code):
    curr = CURRENCIES.get(currency_code, CURRENCIES["USD"])
    formatted = f"{amount:,.2f}"
    if curr["position"] == "before":
        return f"{curr['symbol']}{formatted}"
    return f"{formatted}{curr['symbol']}"

def save_template(template_data):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO client_templates (template_name, client_name, client_email, client_address,
            your_name, your_email, your_address, currency, tax_rate, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        template_data["template_name"],
        template_data["client_name"],
        template_data["client_email"],
        template_data["client_address"],
        template_data["your_name"],
        template_data["your_email"],
        template_data["your_address"],
        template_data["currency"],
        template_data["tax_rate"],
        template_data["notes"]
    ))
    template_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return template_id

def get_templates():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM client_templates ORDER BY created_at DESC")
    templates = cur.fetchall()
    cur.close()
    conn.close()
    return templates

def delete_template(template_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM client_templates WHERE id = %s", (template_id,))
    conn.commit()
    cur.close()
    conn.close()

def save_invoice_history(invoice_data, pdf_bytes):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO invoice_history (invoice_number, invoice_date, due_date, client_name,
            client_email, your_name, subtotal, tax, total, currency, items_json, pdf_data)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        invoice_data["invoice_number"],
        invoice_data["invoice_date"],
        invoice_data["due_date"],
        invoice_data["client_name"],
        invoice_data["client_email"],
        invoice_data["your_name"],
        invoice_data["subtotal"],
        invoice_data["tax"],
        invoice_data["total"],
        invoice_data["currency"],
        json.dumps(invoice_data["items"]),
        pdf_bytes
    ))
    conn.commit()
    cur.close()
    conn.close()

def get_invoice_history(search_query=None, date_filter=None):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    query = "SELECT id, invoice_number, invoice_date, due_date, client_name, client_email, your_name, subtotal, tax, total, currency, created_at FROM invoice_history WHERE 1=1"
    params = []
    
    if search_query:
        query += " AND (invoice_number ILIKE %s OR client_name ILIKE %s OR client_email ILIKE %s)"
        search_param = f"%{search_query}%"
        params.extend([search_param, search_param, search_param])
    
    if date_filter:
        query += " AND invoice_date >= %s"
        params.append(date_filter)
    
    query += " ORDER BY created_at DESC"
    cur.execute(query, params)
    history = cur.fetchall()
    cur.close()
    conn.close()
    return history

def get_invoice_pdf(invoice_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT pdf_data, invoice_number FROM invoice_history WHERE id = %s", (invoice_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result

def save_logo(logo_bytes):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM user_settings")
    cur.execute("INSERT INTO user_settings (logo_data) VALUES (%s)", (logo_bytes,))
    conn.commit()
    cur.close()
    conn.close()

def get_logo():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT logo_data FROM user_settings ORDER BY id DESC LIMIT 1")
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else None

def delete_logo():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM user_settings")
    conn.commit()
    cur.close()
    conn.close()

init_db()

st.set_page_config(page_title="Invoice Ninja AI", layout="centered")

if "page" not in st.session_state:
    st.session_state.page = "create"
if "template_loaded_id" not in st.session_state:
    st.session_state.template_loaded_id = None

def init_form_defaults():
    if "your_name" not in st.session_state:
        st.session_state.your_name = "Alex Rivers"
    if "your_email" not in st.session_state:
        st.session_state.your_email = "alex@yourcompany.com"
    if "your_address" not in st.session_state:
        st.session_state.your_address = "123 Main St\nLos Angeles, CA 90001"
    if "client_name" not in st.session_state:
        st.session_state.client_name = "Acme Corp"
    if "client_email" not in st.session_state:
        st.session_state.client_email = "billing@acme.com"
    if "client_address" not in st.session_state:
        st.session_state.client_address = "456 Corporate Blvd\nSan Francisco, CA 94111"
    if "currency_index" not in st.session_state:
        st.session_state.currency_index = 0
    if "tax_rate" not in st.session_state:
        st.session_state.tax_rate = 8
    if "notes" not in st.session_state:
        st.session_state.notes = "Thank you for your business!\nPayment via PayPal, Wise, or bank transfer."

init_form_defaults()

def load_template_into_form(template):
    st.session_state.your_name = template["your_name"] or "Alex Rivers"
    st.session_state.your_email = template["your_email"] or "alex@yourcompany.com"
    st.session_state.your_address = template["your_address"] or "123 Main St\nLos Angeles, CA 90001"
    st.session_state.client_name = template["client_name"] or "Acme Corp"
    st.session_state.client_email = template["client_email"] or "billing@acme.com"
    st.session_state.client_address = template["client_address"] or "456 Corporate Blvd\nSan Francisco, CA 94111"
    currency_list = list(CURRENCIES.keys())
    st.session_state.currency_index = currency_list.index(template["currency"]) if template.get("currency") in currency_list else 0
    st.session_state.tax_rate = template["tax_rate"] if template.get("tax_rate") is not None else 8
    st.session_state.notes = template["notes"] if template.get("notes") else "Thank you for your business!\nPayment via PayPal, Wise, or bank transfer."
    st.session_state.template_loaded_id = template["id"]

def reset_form():
    st.session_state.your_name = "Alex Rivers"
    st.session_state.your_email = "alex@yourcompany.com"
    st.session_state.your_address = "123 Main St\nLos Angeles, CA 90001"
    st.session_state.client_name = "Acme Corp"
    st.session_state.client_email = "billing@acme.com"
    st.session_state.client_address = "456 Corporate Blvd\nSan Francisco, CA 94111"
    st.session_state.currency_index = 0
    st.session_state.tax_rate = 8
    st.session_state.notes = "Thank you for your business!\nPayment via PayPal, Wise, or bank transfer."
    st.session_state.template_loaded_id = None

with st.sidebar:
    st.title("Invoice Ninja AI")
    st.markdown("**Built in one night**  \nMade for freelancers who hate Canva & Word")
    
    st.markdown("---")
    page = st.radio("Navigation", ["Create Invoice", "Invoice History", "Client Templates", "Settings"], 
                    index=["create", "history", "templates", "settings"].index(st.session_state.page) if st.session_state.page in ["create", "history", "templates", "settings"] else 0)
    
    if page == "Create Invoice":
        st.session_state.page = "create"
    elif page == "Invoice History":
        st.session_state.page = "history"
    elif page == "Client Templates":
        st.session_state.page = "templates"
    elif page == "Settings":
        st.session_state.page = "settings"
    
    st.markdown("---")
    st.caption("© 2025 Invoice Ninja AI")

if st.session_state.page == "create":
    st.title("Create Invoice")
    st.markdown("### Generate beautiful PDF invoices in 3 seconds — no signup, no BS")
    
    templates = get_templates()
    if templates:
        template_options = ["-- New Invoice --"] + [t["template_name"] for t in templates]
        current_template_names = [t["template_name"] for t in templates if t["id"] == st.session_state.template_loaded_id]
        current_index = 0
        if current_template_names:
            try:
                current_index = template_options.index(current_template_names[0])
            except ValueError:
                current_index = 0
        
        selected_template = st.selectbox("Load from template", template_options, index=current_index, key="template_selector")
        
        if selected_template == "-- New Invoice --":
            if st.session_state.template_loaded_id is not None:
                reset_form()
        else:
            template = next((t for t in templates if t["template_name"] == selected_template), None)
            if template and template["id"] != st.session_state.template_loaded_id:
                load_template_into_form(template)
                st.rerun()
    
    col1, col2 = st.columns(2)
    with col1:
        your_name = st.text_input("Your Name / Business", key="your_name")
        your_email = st.text_input("Your Email", key="your_email")
        your_address = st.text_area("Your Address", height=100, key="your_address")

    with col2:
        client_name = st.text_input("Client Name", key="client_name")
        client_email = st.text_input("Client Email", key="client_email")
        client_address = st.text_area("Client Address", height=100, key="client_address")

    st.markdown("### Invoice Details")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        invoice_number = st.text_input("Invoice #", "INV-2025-001")
    with col2:
        invoice_date = st.date_input("Invoice Date", datetime.today())
    with col3:
        due_date = st.date_input("Due Date", datetime.today() + timedelta(days=30))
    with col4:
        currency = st.selectbox("Currency", list(CURRENCIES.keys()), index=st.session_state.currency_index, key="currency_selector")
        if list(CURRENCIES.keys()).index(currency) != st.session_state.currency_index:
            st.session_state.currency_index = list(CURRENCIES.keys()).index(currency)

    currency_symbol = CURRENCIES[currency]["symbol"]

    st.markdown("### Line Items")
    items = []
    for i in range(5):
        with st.expander(f"Item {i+1} {'(optional)' if i>0 else ''}", expanded=i==0):
            col1, col2, col3 = st.columns([3,1,1])
            with col1:
                desc = st.text_input("Description", "Web Design Services" if i == 0 else "", key=f"desc{i}")
            with col2:
                qty = st.number_input("Qty", 1, 100, 1, key=f"qty{i}")
            with col3:
                rate = st.number_input(f"Rate ({currency_symbol})", 0.0, 100000.0, 250.0 if i == 0 else 0.0, key=f"rate{i}")
            if desc:
                items.append({"desc": desc, "qty": qty, "rate": rate, "total": qty*rate})

    tax_rate = st.slider("Tax Rate (%)", 0, 30, key="tax_rate")
    notes = st.text_area("Additional Notes (optional)", key="notes")

    subtotal = sum(item["total"] for item in items if "total" in item)
    tax = subtotal * (tax_rate / 100)
    total = subtotal + tax

    col1, col2, col3 = st.columns([2,1,1])
    with col2:
        st.metric("Subtotal", format_currency(subtotal, currency))
    with col3:
        st.metric("Total", format_currency(total, currency), f"+{format_currency(tax, currency)} tax")

    def create_invoice_pdf(currency_code):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.7*inch)
        styles = getSampleStyleSheet()
        story = []

        logo_data = get_logo()
        if logo_data:
            logo_buffer = BytesIO(bytes(logo_data))
            logo_img = RLImage(logo_buffer, width=80, height=80)
            logo_img.hAlign = 'LEFT'
            header_table = Table([
                [logo_img, Paragraph(f"<font size=24 color='#1E3A8A'><b>INVOICE</b></font><br/><font size=12><b>#{invoice_number}</b></font>", styles["Normal"])]
            ], colWidths=[1.5*inch, 4.5*inch])
        else:
            header_table = Table([
                [Paragraph(f"<font size=24 color='#1E3A8A'><b>INVOICE</b></font>", styles["Normal"]),
                 Paragraph(f"<font size=12><b>#{invoice_number}</b></font>", styles["Normal"])]
            ], colWidths=[4*inch, 2*inch])
        
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 30))

        from_text = f"<b>From:</b><br/>{your_name}<br/>{your_email}<br/>{your_address.replace(chr(10), '<br/>')}"
        to_text = f"<b>Bill To:</b><br/>{client_name}<br/>{client_email}<br/>{client_address.replace(chr(10), '<br/>')}"
        
        data = [
            [Paragraph(from_text, styles["Normal"]),
             Paragraph(to_text, styles["Normal"])]
        ]
        bill_table = Table(data, colWidths=[2.8*inch, 2.8*inch])
        bill_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.lightgrey),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(bill_table)
        story.append(Spacer(1, 20))

        meta_data = [
            ["Invoice Date", str(invoice_date)],
            ["Due Date", str(due_date)],
            ["Invoice #", invoice_number],
            ["Currency", f"{CURRENCIES[currency_code]['name']} ({currency_code})"],
        ]
        meta_table = Table(meta_data, colWidths=[1.5*inch, 4*inch])
        meta_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor("#374151")),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 30))

        table_data = [["Description", "Qty", "Rate", "Amount"]]
        for item in items:
            if item["desc"]:
                table_data.append([
                    item["desc"], 
                    str(item["qty"]), 
                    format_currency(item['rate'], currency_code), 
                    format_currency(item['total'], currency_code)
                ])
        table_data.append(["", "", "Subtotal", format_currency(subtotal, currency_code)])
        table_data.append(["", "", f"Tax ({tax_rate}%)", format_currency(tax, currency_code)])
        table_data.append(["", "", Paragraph("<b>Total</b>", styles["Normal"]), 
                          Paragraph(f"<b>{format_currency(total, currency_code)}</b>", styles["Normal"])])

        item_table = Table(table_data, colWidths=[3.2*inch, 0.7*inch, 1*inch, 1*inch])
        item_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#3B82F6")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
            ('ALIGN', (0,0), (0,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 1, colors.lightgrey),
            ('PADDING', (0,0), (-1,-1), 8),
            ('BACKGROUND', (2,-3), (-1,-1), colors.HexColor("#F3F4F6")),
        ]))
        story.append(item_table)
        story.append(Spacer(1, 30))

        if notes:
            story.append(Paragraph("<b>Notes</b>", styles["Normal"]))
            story.append(Spacer(1, 5))
            notes_style = ParagraphStyle(
                'Notes',
                parent=styles['Normal'],
                textColor=colors.HexColor("#6B7280"),
                fontSize=10
            )
            story.append(Paragraph(notes.replace("\n","<br/>"), notes_style))

        doc.build(story)
        buffer.seek(0)
        return buffer

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Generate & Download PDF Invoice", type="primary", use_container_width=True):
            with st.spinner("Generating your invoice..."):
                pdf_buffer = create_invoice_pdf(currency)
                pdf_bytes = pdf_buffer.getvalue()
                
                invoice_data = {
                    "invoice_number": invoice_number,
                    "invoice_date": invoice_date,
                    "due_date": due_date,
                    "client_name": client_name,
                    "client_email": client_email,
                    "your_name": your_name,
                    "subtotal": subtotal,
                    "tax": tax,
                    "total": total,
                    "currency": currency,
                    "items": items
                }
                save_invoice_history(invoice_data, pdf_bytes)
                
                st.download_button(
                    label="Download Your Invoice Now",
                    data=pdf_bytes,
                    file_name=f"Invoice_{invoice_number}.pdf",
                    mime="application/pdf",
                    type="secondary",
                    use_container_width=True
                )
                st.success("Invoice ready and saved to history! Click above to download.")
                st.balloons()

    with col2:
        with st.expander("Save as Template"):
            template_name = st.text_input("Template Name", f"Template - {client_name}")
            if st.button("Save Template", use_container_width=True):
                template_data = {
                    "template_name": template_name,
                    "client_name": client_name,
                    "client_email": client_email,
                    "client_address": client_address,
                    "your_name": your_name,
                    "your_email": your_email,
                    "your_address": your_address,
                    "currency": currency,
                    "tax_rate": tax_rate,
                    "notes": notes
                }
                save_template(template_data)
                st.success(f"Template '{template_name}' saved!")
                st.rerun()

    st.markdown("---")
    
    with st.expander("Email Invoice to Client"):
        st.info("Configure your SMTP settings in the Settings page to enable email delivery.")
        smtp_server = os.environ.get("SMTP_SERVER", "")
        if smtp_server:
            email_subject = st.text_input("Email Subject", f"Invoice {invoice_number} from {your_name}")
            email_body = st.text_area("Email Body", f"""Dear {client_name},

Please find attached invoice {invoice_number} for {format_currency(total, currency)}.

Payment is due by {due_date}.

Thank you for your business!

Best regards,
{your_name}""")
            
            if st.button("Send Invoice via Email", use_container_width=True):
                try:
                    pdf_buffer = create_invoice_pdf(currency)
                    pdf_bytes = pdf_buffer.getvalue()
                    
                    msg = MIMEMultipart()
                    msg['From'] = os.environ.get("SMTP_FROM", your_email)
                    msg['To'] = client_email
                    msg['Subject'] = email_subject
                    
                    msg.attach(MIMEText(email_body, 'plain'))
                    
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(pdf_bytes)
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename="Invoice_{invoice_number}.pdf"')
                    msg.attach(part)
                    
                    server = smtplib.SMTP(smtp_server, int(os.environ.get("SMTP_PORT", 587)))
                    server.starttls()
                    server.login(os.environ.get("SMTP_USER", ""), os.environ.get("SMTP_PASSWORD", ""))
                    server.send_message(msg)
                    server.quit()
                    
                    st.success(f"Invoice sent to {client_email}!")
                except Exception as e:
                    st.error(f"Failed to send email: {str(e)}")
        else:
            st.warning("SMTP not configured. Add SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, and SMTP_FROM to your environment variables.")

    st.markdown("---")
    st.markdown("""
    **Loving this? Unlock the full AI toolkit:**  
    Get **Outfit Roaster** (£9.99 lifetime) – Unlimited AI outfit roasts with zero mercy.  
    Perfect for freelancers: Bill like a pro, roast like a savage.  
    [Buy Now on Gumroad →](https://drwitt.gumroad.com/l/zfbdxb)  
    (30-day money-back, source code included)
    """)

elif st.session_state.page == "history":
    st.title("Invoice History")
    st.markdown("View and download your previously generated invoices")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        search_query = st.text_input("Search invoices", placeholder="Search by invoice #, client name, or email...")
    with col2:
        date_options = {
            "All Time": None,
            "Last 7 Days": datetime.today() - timedelta(days=7),
            "Last 30 Days": datetime.today() - timedelta(days=30),
            "Last 90 Days": datetime.today() - timedelta(days=90),
        }
        date_filter_label = st.selectbox("Date Range", list(date_options.keys()))
        date_filter = date_options[date_filter_label]
    
    invoices = get_invoice_history(search_query if search_query else None, date_filter)
    
    if invoices:
        st.markdown(f"**{len(invoices)} invoice(s) found**")
        
        for invoice in invoices:
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                with col1:
                    st.markdown(f"**{invoice['invoice_number']}**")
                    st.caption(f"{invoice['client_name']}")
                with col2:
                    st.markdown(f"Date: {invoice['invoice_date']}")
                    st.caption(f"Due: {invoice['due_date']}")
                with col3:
                    st.markdown(f"**{format_currency(float(invoice['total']), invoice['currency'])}**")
                with col4:
                    pdf_result = get_invoice_pdf(invoice['id'])
                    if pdf_result:
                        pdf_data, inv_num = pdf_result
                        st.download_button(
                            "Download",
                            data=bytes(pdf_data),
                            file_name=f"Invoice_{inv_num}.pdf",
                            mime="application/pdf",
                            key=f"dl_{invoice['id']}"
                        )
                st.divider()
    else:
        st.info("No invoices found. Create your first invoice to see it here!")

elif st.session_state.page == "templates":
    st.title("Client Templates")
    st.markdown("Save and manage templates for repeat clients")
    
    templates = get_templates()
    
    if templates:
        st.markdown(f"**{len(templates)} template(s) saved**")
        
        for template in templates:
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.markdown(f"**{template['template_name']}**")
                    st.caption(f"Client: {template['client_name']} | Currency: {template['currency']}")
                with col2:
                    if st.button("Use", key=f"use_{template['id']}", use_container_width=True):
                        load_template_into_form(template)
                        st.session_state.page = "create"
                        st.rerun()
                with col3:
                    if st.button("Delete", key=f"del_{template['id']}", use_container_width=True, type="secondary"):
                        delete_template(template['id'])
                        st.rerun()
                st.divider()
    else:
        st.info("No templates saved yet. Create an invoice and save it as a template!")

elif st.session_state.page == "settings":
    st.title("Settings")
    
    st.markdown("### Logo Upload")
    st.markdown("Upload your business logo to appear on invoices")
    
    current_logo = get_logo()
    if current_logo:
        st.image(bytes(current_logo), width=150, caption="Current Logo")
        if st.button("Remove Logo", type="secondary"):
            delete_logo()
            st.success("Logo removed!")
            st.rerun()
    
    uploaded_logo = st.file_uploader("Upload Logo (PNG, JPG)", type=["png", "jpg", "jpeg"])
    if uploaded_logo:
        img = Image.open(uploaded_logo)
        img = img.convert("RGB")
        img.thumbnail((200, 200))
        
        img_buffer = BytesIO()
        img.save(img_buffer, format="PNG")
        img_bytes = img_buffer.getvalue()
        
        st.image(img_bytes, width=150, caption="Preview")
        
        if st.button("Save Logo", type="primary"):
            save_logo(img_bytes)
            st.success("Logo saved! It will appear on your invoices.")
            st.rerun()
    
    st.markdown("---")
    st.markdown("### Email Configuration")
    st.markdown("Configure SMTP settings to send invoices directly to clients")
    
    st.info("""
    To enable email delivery, add these environment variables:
    - **SMTP_SERVER**: Your SMTP server (e.g., smtp.gmail.com)
    - **SMTP_PORT**: SMTP port (usually 587 for TLS)
    - **SMTP_USER**: Your email username
    - **SMTP_PASSWORD**: Your email password or app password
    - **SMTP_FROM**: The 'From' email address
    """)
    
    smtp_configured = os.environ.get("SMTP_SERVER", "") != ""
    if smtp_configured:
        st.success("SMTP is configured!")
    else:
        st.warning("SMTP is not configured. Email delivery is disabled.")
