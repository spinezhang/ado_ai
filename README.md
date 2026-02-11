# ADO AI - Azure DevOps AI Auto-Complete Tool

A powerful tool that leverages Claude AI to automatically analyze and complete Azure DevOps work items. Available as both a **CLI** and **Web Service** with beautiful UI—fetch work items, get AI-powered analysis, and update them with intelligent solutions.

## 🌟 Features

### Core Features
- 🤖 **AI-Powered Analysis**: Uses Claude AI (Anthropic) to analyze work items and generate solutions
- 🔄 **Auto-Complete**: Automatically update work items with AI-generated analysis
- ⚙️ **Type-Specific Prompts**: Specialized analysis for Bugs, Tasks, and User Stories
- 💰 **Cost Tracking**: Real-time token usage and cost estimation
- 🔒 **Secure**: Encrypted credential storage with Fernet (AES-256)
- 🛡️ **Robust**: Automatic retry logic and comprehensive error handling

### Web Service Features
- 🌐 **Beautiful Web UI**: Modern interface built with FastAPI + Tailwind CSS
- 🔐 **Encrypted Storage**: Credentials stored securely in database
- 📝 **Custom Prompts**: Add specific instructions for each analysis
- 📊 **Analysis History**: Track all work item analyses with costs
- 🚀 **RESTful API**: Comprehensive API with auto-generated documentation
- ⚡ **Real-time Updates**: Progress tracking during AI analysis

### CLI Features
- 📊 **Beautiful Terminal**: Rich output with tables, colors, and progress indicators
- ⌨️ **Fast & Efficient**: Perfect for scripting and automation
- 🔧 **Developer-Friendly**: Works with existing terminal workflows

## Installation

### Prerequisites

- Python 3.9 or higher
- Azure DevOps account with a Personal Access Token (PAT)
- Anthropic API key for Claude AI

### Install Package

```bash
# Clone or navigate to the project directory
cd /path/to/azure_devops

# Install in development mode (includes all dependencies)
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

## Quick Start

### Option 1: Web Service (Recommended for UI)

```bash
# Start the web server
python -m ado_ai_web.main

# Open browser to http://localhost:8000
# Complete the setup wizard
# Start analyzing work items!
```

### Option 2: CLI (Recommended for automation)

```bash
# Create configuration file
cp .env.example .env

# Edit .env with your credentials
# vim .env

# Validate configuration
ado-ai config validate

# Analyze a work item
ado-ai complete 12345
```

---

## Web Service

### Starting the Web Service

```bash
# Development mode (with auto-reload)
python -m ado_ai_web.main

# Production mode with Uvicorn
uvicorn ado_ai_web.main:app --host 0.0.0.0 --port 8000
```

The service will be available at `http://localhost:8000`

### First-Time Setup

1. Navigate to `http://localhost:8000`
2. You'll be redirected to the setup wizard
3. Enter your Azure DevOps credentials:
   - Organization URL (e.g., `https://dev.azure.com/YourOrg`)
   - Project name
   - Personal Access Token (PAT)
4. Enter your Anthropic API key
5. (Optional) Set work folder path for file operations
6. Click "Test Connection" buttons to validate
7. Complete setup

### Using the Web Interface

#### Analyze a Work Item

1. Click "New Analysis" from the dashboard
2. Enter work item ID
3. (Optional) Add custom prompt for specific guidance
4. Click "Fetch Work Item" to see details
5. Click "🤖 Analyze with AI" to start analysis
6. Review comprehensive AI insights:
   - Analysis summary
   - Detailed solution
   - Task breakdown
   - Risk assessment
   - Proposed changes
   - Token usage and cost
7. (Coming soon) Click "Apply Changes" to update work item

#### Configuration Management

- Access settings via the "Settings" menu
- Update credentials, model selection, and preferences
- Test connections at any time
- All changes are saved to encrypted database

### API Documentation

Interactive API documentation is available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

#### API Endpoints

```
# Authentication & Setup
POST   /api/setup                          # Initial configuration
POST   /api/test-connection                # Test credentials

# Configuration
GET    /api/config                         # Get settings (redacted)
PUT    /api/config                         # Update settings
GET    /api/config/status                  # Check if configured

# Work Items
GET    /api/work-items/{id}                # Fetch work item
POST   /api/work-items/{id}/analyze        # Analyze with AI
GET    /api/work-items/history/{id}        # Get analysis results

# Health
GET    /health                             # Health check
```

### Docker Deployment

```bash
# Build image
docker build -t ado-ai-web .

# Run container
docker run -p 8000:8000 \
  -e ENCRYPTION_MASTER_KEY=your-key-here \
  -v ./ado_ai.db:/app/ado_ai.db \
  ado-ai-web
```

### Environment Variables (Web Service)

```bash
# Required
ENCRYPTION_MASTER_KEY=your-base64-encoded-32-byte-key

# Optional
DATABASE_URL=sqlite:///./ado_ai.db
SESSION_SECRET_KEY=your-session-secret
CSRF_SECRET_KEY=your-csrf-secret
```

---

## CLI Usage

### Configuration

#### 1. Create Environment File

```bash
cp .env.example .env
```

#### 2. Configure Credentials

Edit the `.env` file:

```bash
# Azure DevOps Configuration
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/YourOrganization
AZURE_DEVOPS_PROJECT=YourProject
AZURE_DEVOPS_PAT=your_personal_access_token_here

# Anthropic Claude Configuration
ANTHROPIC_API_KEY=your_anthropic_api_key_here
CLAUDE_MODEL=claude-opus-4-6

# Application Settings
LOG_LEVEL=INFO
AUTO_APPROVE=false
MAX_RETRIES=3
TIMEOUT_SECONDS=30
```

#### 3. Validate Configuration

```bash
ado-ai config validate
```

### Commands

#### Fetch a Work Item

Display work item details without making changes:

```bash
ado-ai fetch 12345
```

#### Complete a Work Item

Analyze and auto-complete a work item with AI:

```bash
# Interactive mode (prompts for confirmation)
ado-ai complete 12345

# Auto-approve mode (no confirmation)
ado-ai complete 12345 --auto-approve

# Dry-run mode (simulate without changes)
ado-ai complete 12345 --dry-run
```

#### Configuration Commands

```bash
# Validate configuration
ado-ai config validate

# Show current configuration
ado-ai config show
```

#### Global Options

```bash
# Verbose output (DEBUG level)
ado-ai --verbose complete 12345

# Quiet output (only warnings/errors)
ado-ai --quiet complete 12345

# Show help
ado-ai --help

# Show version
ado-ai version
```

### Example Output

```
✓ Fetching work item 12345...
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Work Item Details                         ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ ID:          12345                        ┃
┃ Type:        Task                         ┃
┃ Title:       Implement user auth          ┃
┃ State:       Active                       ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

✓ Analyzing with Claude AI...

🤖 AI Analysis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Analysis: This task requires implementing a secure user authentication system...

Solution: Implement JWT-based authentication with the following approach...

Tasks:
  1. Set up authentication middleware
  2. Create login/logout endpoints
  3. Implement token validation
  4. Add unit tests for auth flow

💡 Proposed Changes:
  • Status: Active → Resolved
  • Remaining Work: 8.0 → 0 hours
  • Add AI-generated comment

💰 Cost: $0.15 (3,000 input, 1,200 output tokens)

Apply these changes? (y/n): y

✓ Work item 12345 updated successfully!
View at: https://dev.azure.com/YourOrg/...
```

---

## How It Works

### Workflow

1. **Fetch**: Retrieves work item details from Azure DevOps using the REST API
2. **Analyze**: Sends work item context to Claude AI for intelligent analysis
3. **Display**: Shows AI-generated analysis, solution, tasks, and risks
4. **Confirm**: Prompts for user confirmation (Web UI or CLI)
5. **Update**: Updates work item status, adds AI-generated comment, and applies tags

### Architecture

```
┌─────────────────────┐         ┌──────────────────────┐
│   Web UI / CLI      │────────>│  Workflow Service    │
└─────────────────────┘         └──────────────────────┘
                                         │
                        ┌────────────────┼────────────────┐
                        │                │                │
                        v                v                v
               ┌─────────────┐  ┌──────────────┐  ┌──────────────┐
               │Azure DevOps │  │  Claude AI   │  │   Database   │
               │   Client    │  │    Client    │  │  (Settings)  │
               └─────────────┘  └──────────────┘  └──────────────┘
```

---

## Azure DevOps Setup

### Creating a Personal Access Token (PAT)

1. Go to Azure DevOps: `https://dev.azure.com/{YourOrganization}`
2. Click your profile icon → **Personal access tokens**
3. Click **+ New Token**
4. Configure the token:
   - **Name**: ADO AI
   - **Expiration**: Choose your preferred duration
   - **Scopes**:
     - Work Items: **Read & Write**
     - Project and Team: **Read**
5. Click **Create** and copy the token immediately
6. Use in web setup wizard or paste in `.env` file

### Required Permissions

- **Work Items**: Read, Write (to fetch and update work items)
- **Project and Team**: Read (to access project information)

---

## Anthropic API Setup

1. Sign up at [Anthropic Console](https://console.anthropic.com/)
2. Go to **API Keys** section
3. Create a new API key
4. Copy and use in setup wizard or paste in `.env` file

### Pricing

- **Claude Opus 4.6**: $5 per million input tokens, $25 per million output tokens
- **Claude Sonnet 4.5**: $1 per million input tokens, $5 per million output tokens

Typical work item analysis costs **$0.10-$0.30** per work item.

---

## Project Structure

```
azure_devops/
├── .env                         # Environment variables (git-ignored)
├── .env.example                 # Template for environment variables
├── .gitignore                   # Git ignore rules
├── README.md                    # This file
├── pyproject.toml               # Python project configuration
├── alembic.ini                  # Database migration config
├── ado_ai.db                    # SQLite database (auto-created)
│
└── src/
    ├── ado_ai_cli/              # CLI Package
    │   ├── __init__.py
    │   ├── __main__.py          # CLI entry point
    │   ├── cli.py               # Typer CLI commands
    │   ├── config.py            # Configuration management
    │   │
    │   ├── core/                # Business logic
    │   │   ├── workflow.py      # Main orchestration (refactored)
    │   │   └── presenter.py     # CLI display logic
    │   │
    │   ├── azure_devops/        # Azure DevOps integration
    │   │   ├── client.py        # Azure DevOps API client
    │   │   └── models.py        # Work item data models
    │   │
    │   ├── ai/                  # AI integration
    │   │   ├── claude_client.py # Anthropic Claude client
    │   │   └── prompts.py       # Prompt templates
    │   │
    │   └── utils/               # Utilities
    │       ├── logger.py        # Logging setup
    │       └── exceptions.py    # Custom exceptions
    │
    └── ado_ai_web/              # Web Service Package
        ├── main.py              # FastAPI application
        │
        ├── api/                 # REST API endpoints
        │   ├── setup.py         # Setup wizard endpoints
        │   ├── config.py        # Configuration endpoints
        │   └── work_items.py    # Work item endpoints
        │
        ├── services/            # Business logic
        │   ├── encryption.py    # Credential encryption
        │   ├── settings_manager.py  # Database CRUD
        │   └── workflow_service.py  # Workflow wrapper
        │
        ├── models/              # Data models
        │   ├── database.py      # SQLAlchemy ORM models
        │   ├── requests.py      # API request models
        │   └── responses.py     # API response models
        │
        ├── database/            # Database layer
        │   ├── session.py       # SQLAlchemy session
        │   └── migrations/      # Alembic migrations
        │
        ├── templates/           # Jinja2 templates
        │   ├── base.html        # Base layout
        │   ├── setup.html       # Setup wizard
        │   ├── dashboard.html   # Main dashboard
        │   └── work_item_detail.html  # Analysis UI
        │
        ├── static/              # Static assets
        │   ├── css/             # Stylesheets
        │   └── js/              # JavaScript
        │
        └── middleware/          # Custom middleware
            └── security.py      # Security middleware
```

---

## Security Best Practices

- ✅ Credentials encrypted at rest with AES-256
- ✅ Master encryption key stored in environment variable
- ✅ Never commit `.env` or database files to version control
- ✅ Use minimal PAT permissions (principle of least privilege)
- ✅ Set PAT expiration dates
- ✅ Rotate credentials regularly
- ✅ HTTPS recommended for production deployments
- ✅ CSRF protection ready for production
- ✅ Comprehensive audit logging

---

## Troubleshooting

### Web Service Issues

**Error**: "ENCRYPTION_MASTER_KEY not set"
- **Solution**: Set the environment variable with a secure key
- Generate one with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

**Error**: "Database not found"
- **Solution**: Run the server once to auto-create the database
- Or run: `alembic upgrade head`

### Configuration Errors

**Error**: "Failed to load configuration"
- **Solution**: Complete setup wizard in web UI, or ensure `.env` file exists for CLI
- Run `ado-ai config validate` for CLI

### Authentication Errors

**Error**: "Invalid PAT or insufficient permissions"
- **Solution**: Check that your Azure DevOps PAT is valid and has required permissions
- Use "Test Connection" in web UI to validate
- Ensure the PAT hasn't expired

**Error**: "Claude API error"
- **Solution**: Verify your Anthropic API key is valid
- Check available credits in your Anthropic account
- Use "Test Connection" to validate

### Work Item Not Found

**Error**: "Work item {id} not found"
- **Solution**: Verify the work item ID exists in your project
- Ensure you have permission to view the work item
- Check that the project name matches

---

## Development

### Running from Source

```bash
# CLI
python -m ado_ai_cli complete 12345

# Web Service
python -m ado_ai_web.main
```

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=ado_ai_cli --cov=ado_ai_web --cov-report=term-missing
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

---

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

## License

MIT License

---

## Support

For issues, questions, or feedback:
- Create an issue on GitHub
- Check the troubleshooting section above
- Review Azure DevOps and Anthropic API documentation

---

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/) for web service
- Built with [Typer](https://typer.tiangolo.com/) for CLI
- Uses [Rich](https://rich.readthedocs.io/) for beautiful terminal output
- Powered by [Claude AI](https://www.anthropic.com/claude) from Anthropic
- Integrates with [Azure DevOps](https://azure.microsoft.com/en-us/products/devops/) REST API
- UI built with [Tailwind CSS](https://tailwindcss.com/) and [Alpine.js](https://alpinejs.dev/)
- Database management with [SQLAlchemy](https://www.sqlalchemy.org/) and [Alembic](https://alembic.sqlalchemy.org/)

---

**Made with ❤️ and 🤖 AI**
