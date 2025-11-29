# Replit Workspace Configuration

## Overview

This is a Streamlit-based invoice generation application that allows users to create, manage, and send professional invoices. The application supports multiple currencies (USD, GBP, EUR), tax calculations, PDF generation using ReportLab, and email delivery capabilities. Client information can be saved as templates in a PostgreSQL database for reuse.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Streamlit web application framework
- **UI Pattern**: Single-page application with interactive forms
- **Rationale**: Streamlit provides rapid development of data-driven web applications with minimal frontend code, ideal for business tools like invoice generation

### Backend Architecture
- **Language**: Python 3.x
- **Application Structure**: Monolithic architecture in `app.py`
- **Data Flow**: User input → Business logic → PDF generation → Email delivery (optional)
- **Rationale**: Simple monolithic structure appropriate for a focused invoice generation tool without complex business logic separation needs

### Data Storage
- **Database**: PostgreSQL
- **ORM/Driver**: psycopg2 (direct database driver)
- **Schema Design**: 
  - `client_templates` table stores reusable client information templates
  - Fields include client details, business details, currency preferences, tax rates, and custom notes
- **Connection Management**: Environment variable-based connection string (`DATABASE_URL`)
- **Rationale**: PostgreSQL provides reliability and ACID compliance for business data; direct driver chosen over ORM for simplicity given minimal database complexity

### PDF Generation
- **Library**: ReportLab
- **Components Used**: 
  - SimpleDocTemplate for document structure
  - Platypus (Paragraph, Spacer, Table, Image) for layout elements
  - Custom styling with ParagraphStyle
- **Output**: In-memory PDF generation via BytesIO for immediate download/email
- **Rationale**: ReportLab offers professional-grade PDF generation with precise layout control necessary for business documents like invoices

### Email Delivery
- **Protocol**: SMTP
- **Library**: Python standard library (smtplib, email.mime)
- **Functionality**: Sends generated invoices as PDF attachments
- **Attachment Handling**: MIME multipart messages with base64 encoding
- **Rationale**: Standard SMTP provides universal email compatibility without third-party service dependencies

### Multi-Currency Support
- **Supported Currencies**: USD, GBP, EUR
- **Storage**: Dictionary-based configuration with symbol, name, and position attributes
- **Extensibility**: Easy to add new currencies by extending the CURRENCIES dictionary
- **Rationale**: Dictionary-based approach provides flexibility and simplicity for limited currency set

### State Management
- **Approach**: Streamlit session state (implicit)
- **Persistence**: Database-backed templates for client information
- **Rationale**: Streamlit's built-in state management sufficient for single-user session workflows

## External Dependencies

### Database
- **PostgreSQL**: Primary data storage
- **Connection**: Via `DATABASE_URL` environment variable
- **Driver**: psycopg2 with RealDictCursor for dictionary-style result access

### Python Libraries
- **streamlit**: Web application framework
- **reportlab**: PDF generation and formatting
- **Pillow (PIL)**: Image processing for invoice logos/branding
- **psycopg2**: PostgreSQL database adapter
- **smtplib/email**: Email delivery (Python standard library)

### Environment Variables
- **DATABASE_URL**: PostgreSQL connection string (required)
- Potential SMTP credentials for email functionality (implementation-dependent)

### Third-Party Services
- **SMTP Server**: Required for email delivery functionality (Gmail, SendGrid, or custom SMTP server)
- **Note**: No payment processing, cloud storage, or authentication services currently integrated