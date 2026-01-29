# SevDesk Connector

A FastAPI backend service to ease the creation of quotes and billings with the SevDesk API.

## Features

- 🚀 **FastAPI** - Modern, fast Python web framework
- 💾 **SQLite Database** - Local storage for quotes and invoices
- 🔗 **SevDesk Integration** - Sync quotes and invoices with SevDesk API
- 📝 **Quote Management** - Create, read, update, and delete quotes
- 🧾 **Invoice Management** - Create, read, update, and delete invoices
- 📧 **Email Sending** - Send invoices via SevDesk email functionality
- 🔄 **Async Support** - Full async/await support for better performance

## Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- SevDesk API key

## Installation

1. Clone the repository:
```bash
git clone https://github.com/mi-skam/sevdesk-connector.git
cd sevdesk-connector
```

2. Install uv (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Install dependencies using uv:
```bash
uv pip install -e .
```

4. Create a `.env` file from the example:
```bash
cp .env.example .env
```

5. Configure your environment variables in `.env`:
```env
SEVDESK_API_KEY=your_api_key_here
SEVDESK_BASE_URL=https://my.sevdesk.de/api/v1
DATABASE_URL=sqlite+aiosqlite:///./sevdesk.db
HOST=0.0.0.0
PORT=8000
DEBUG=false
```

## Usage

### Running the Server

Start the development server:
```bash
uv run python -m app.main
```

Or using uvicorn directly:
```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive API docs (Swagger)**: http://localhost:8000/docs
- **Alternative API docs (ReDoc)**: http://localhost:8000/redoc

### API Endpoints

#### Quotes

- `POST /quotes/` - Create a new quote
- `GET /quotes/` - List all quotes (with pagination)
- `GET /quotes/{quote_id}` - Get a specific quote
- `PUT /quotes/{quote_id}` - Update a quote
- `DELETE /quotes/{quote_id}` - Delete a quote
- `POST /quotes/{quote_id}/sync-to-sevdesk` - Sync quote to SevDesk

#### Invoices

- `POST /invoices/` - Create a new invoice
- `GET /invoices/` - List all invoices (with pagination)
- `GET /invoices/{invoice_id}` - Get a specific invoice
- `PUT /invoices/{invoice_id}` - Update an invoice
- `DELETE /invoices/{invoice_id}` - Delete an invoice
- `POST /invoices/{invoice_id}/sync-to-sevdesk` - Sync invoice to SevDesk
- `POST /invoices/{invoice_id}/send` - Send invoice via email

### Example Requests

#### Create a Quote

```bash
curl -X POST "http://localhost:8000/quotes/" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "John Doe",
    "customer_email": "john@example.com",
    "description": "Website development services",
    "amount": 1500.00,
    "tax_rate": 19.0
  }'
```

#### Create an Invoice

```bash
curl -X POST "http://localhost:8000/invoices/" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Jane Smith",
    "customer_email": "jane@example.com",
    "description": "Consulting services",
    "amount": 2500.00,
    "tax_rate": 19.0,
    "quote_id": 1
  }'
```

#### Sync to SevDesk

```bash
curl -X POST "http://localhost:8000/invoices/1/sync-to-sevdesk"
```

## Development

### Install Development Dependencies

```bash
uv pip install -e ".[dev]"
```

### Code Formatting

```bash
uv run black app/
```

### Linting

```bash
uv run ruff check app/
```

## Project Structure

```
sevdesk-connector/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── api/                    # API endpoints
│   │   ├── __init__.py
│   │   ├── quotes.py           # Quote endpoints
│   │   └── invoices.py         # Invoice endpoints
│   ├── core/                   # Core configuration
│   │   ├── __init__.py
│   │   ├── config.py           # Settings and configuration
│   │   └── database.py         # Database setup
│   ├── models/                 # Data models
│   │   ├── __init__.py
│   │   ├── models.py           # SQLAlchemy models
│   │   └── schemas.py          # Pydantic schemas
│   └── services/               # Business logic
│       ├── __init__.py
│       └── sevdesk_client.py   # SevDesk API client
├── .env.example                # Example environment variables
├── .gitignore                  # Git ignore file
├── pyproject.toml              # Project dependencies
└── README.md                   # This file
```

## Database

The application uses SQLite for local storage. The database file `sevdesk.db` will be created automatically when you first run the application.

### Database Schema

**Quotes Table:**
- `id` - Primary key
- `sevdesk_id` - SevDesk API ID (nullable)
- `quote_number` - Unique quote number
- `customer_name` - Customer name
- `customer_email` - Customer email
- `description` - Quote description
- `amount` - Quote amount
- `tax_rate` - Tax rate (default: 19%)
- `status` - Quote status (draft, sent, accepted, rejected, converted)
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp
- `valid_until` - Quote validity date

**Invoices Table:**
- `id` - Primary key
- `sevdesk_id` - SevDesk API ID (nullable)
- `invoice_number` - Unique invoice number
- `quote_id` - Related quote ID (optional)
- `customer_name` - Customer name
- `customer_email` - Customer email
- `description` - Invoice description
- `amount` - Invoice amount
- `tax_rate` - Tax rate (default: 19%)
- `status` - Invoice status (draft, sent, paid, overdue, cancelled)
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp
- `due_date` - Payment due date

## SevDesk Integration

The application provides a wrapper around the SevDesk API. To use SevDesk features:

1. Obtain a SevDesk API key from your SevDesk account
2. Set the `SEVDESK_API_KEY` in your `.env` file
3. Create quotes/invoices locally
4. Sync them to SevDesk using the `/sync-to-sevdesk` endpoints

**Note:** The SevDesk API client implementation follows the general structure of the SevDesk API. You may need to adjust the exact endpoints and data structures based on the current SevDesk API documentation.

## Production Deployment

### Security Considerations

When deploying to production, ensure you:

1. **Set proper CORS origins**: Update `CORS_ORIGINS` in `.env` to restrict access to trusted domains only:
   ```env
   CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
   ```

2. **Secure your API key**: Never commit your `.env` file. Always use environment variables or secrets management services.

3. **Use HTTPS**: Always deploy behind a reverse proxy (nginx, Caddy) with HTTPS enabled.

4. **Database**: Consider upgrading to PostgreSQL or MySQL for production workloads:
   ```env
   DATABASE_URL=postgresql+asyncpg://user:password@localhost/sevdesk
   ```

5. **Monitoring**: Add logging and monitoring tools to track application health and errors.

6. **Rate Limiting**: Implement rate limiting to prevent abuse of your API endpoints.

### Alternative to uv

If you prefer using pip and virtual environments:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
