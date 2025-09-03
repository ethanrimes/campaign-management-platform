# Campaign Management Platform

An agentic AI-powered social media campaign management system for Facebook and Instagram, designed to autonomously research, plan, create, and manage marketing campaigns across multiple initiatives.

## Overview

This platform uses multiple AI agents working together to:
- Research market trends and competitors
- Plan and orchestrate marketing campaigns
- Create engaging content with images and videos
- Manage budgets across campaigns and ad sets
- Track performance metrics
- Respond to comments (coming soon)

## Key Features

- **Multi-tenant Architecture**: Secure isolation between different initiatives using Supabase RLS
- **Flexible Model Support**: Switch between OpenAI, Grok, Gemini, and other providers
- **Autonomous Operation**: Scheduled agents that continuously optimize campaigns
- **Budget Management**: Intelligent allocation across campaigns and ad sets
- **Content Generation**: AI-powered creation of posts, images, and videos
- **Research Integration**: Automated competitive analysis and trend discovery

## Architecture

```
┌─────────────────────────────────────────────────┐
│                 Orchestrator Agent               │
│  (Plans campaigns, allocates budget, strategy)   │
└────────────────┬────────────────────────────────┘
                 │
       ┌─────────┴─────────┬──────────────┐
       ▼                   ▼              ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Research    │  │   Content    │  │   Comment    │
│    Agent     │  │   Creator    │  │  Responder   │
│              │  │    Agent     │  │   (Soon)     │
└──────────────┘  └──────────────┘  └──────────────┘
       │                   │              │
       ▼                   ▼              ▼
   [Supabase]         [Meta API]    [Analytics]
```

## Prerequisites

- Python 3.9+
- PostgreSQL database (via Supabase)
- Meta (Facebook/Instagram) Developer Account
- API keys for AI models (OpenAI, Grok, or Gemini)
- Perplexity API key for web search

## Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/campaign-management-platform.git
cd campaign-management-platform
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your actual credentials
```

5. **Set up Supabase**
   - Create a new Supabase project at https://supabase.com
   - Run the SQL migration in `backend/db/migrations/001_initial_schema.sql`
   - Copy your project URL and keys to `.env`

6. **Initialize the database**
```bash
python scripts/setup/init_database.py
```

## Configuration

### Creating an Initiative

Each initiative represents a distinct social media presence (e.g., education, recruiting, nonprofit).

1. **Create a configuration file** in `initiatives/your_initiative/config.yaml`:

```yaml
name: "Your Initiative Name"
description: "Brief description"
model_provider: "openai"  # or "grok", "gemini"

social_accounts:
  facebook:
    page_id: "your-page-id"
    page_name: "Your Page Name"
    page_url: "https://facebook.com/yourpage"
  instagram:
    username: "your_username"
    account_id: "your-account-id"
    url: "https://instagram.com/your_username"

category: "Education"  # or "Business", "Nonprofit", etc.
optimization_metric: "engagement"  # or "reach", "conversions"

objectives:
  primary: "Build engaged community"
  secondary:
    - "Share valuable content"
    - "Drive website traffic"

target_metrics:
  reach: 10000
  engagement_rate: 0.05
  clicks: 500

budget:
  daily:
    amount: 100
    currency: "USD"
  total:
    amount: 3000
    currency: "USD"
```

2. **Register the initiative**:
```bash
python scripts/setup/create_initiative.py initiatives/your_initiative/config.yaml
```

This will output a Tenant ID - save this for API calls.

### Meta API Setup

1. Create a Facebook App at https://developers.facebook.com
2. Add Facebook Login and Instagram Basic Display products
3. Generate Page Access Token with required permissions:
   - `pages_manage_posts`
   - `pages_read_engagement`
   - `instagram_basic`
   - `instagram_content_publish`
4. Add the token to your `.env` file

## Usage

### Starting the API Server

```bash
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Running the Scheduler

The scheduler runs all agents on their configured intervals:

```bash
python scripts/cron/scheduler.py
```

### Manual Agent Execution

You can also trigger agents manually via API:

```bash
# Trigger orchestrator for an initiative
curl -X POST http://localhost:8000/api/campaigns/orchestrate \
  -H "X-Tenant-ID: your-tenant-id" \
  -H "Content-Type: application/json" \
  -d '{"initiative_id": "your-initiative-id"}'
```

### Testing

Run the test suite:

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_orchestrator.py

# Run with coverage
pytest --cov=agents --cov=backend tests/
```

## Agent Schedules

Default cron schedules (configurable in `.env`):

- **Orchestrator**: Every 6 hours - Plans campaigns and allocates budget
- **Researcher**: Daily at midnight - Gathers market insights
- **Content Creator**: Every 4 hours - Generates new posts
- **Metrics Collector**: Every hour - Updates performance data

## API Endpoints

### Initiatives
- `GET /api/initiatives` - List all initiatives
- `GET /api/initiatives/{id}` - Get specific initiative
- `POST /api/initiatives` - Create new initiative
- `PUT /api/initiatives/{id}` - Update initiative

### Campaigns
- `GET /api/campaigns` - List campaigns
- `POST /api/campaigns/orchestrate` - Trigger orchestration

### Content
- `GET /api/content` - List posts
- `POST /api/content/generate` - Generate new content

### Metrics
- `GET /api/metrics` - Get performance metrics

## Development

### Project Structure

```
campaign-management-platform/
├── agents/               # AI agents
│   ├── orchestrator/    # Campaign planning
│   ├── researcher/      # Market research
│   ├── content_creator/ # Content generation
│   └── comment_responder/ # Comment management
├── backend/             # API and database
│   ├── api/            # FastAPI routes
│   ├── db/             # Database models
│   └── config/         # Configuration
├── tools/              # Integration tools
│   ├── search/         # Search APIs
│   ├── social_media/   # Platform APIs
│   └── analytics/      # Metrics tools
├── initiatives/        # Initiative configs
└── scripts/           # Utility scripts
```

### Adding a New Agent

1. Create agent directory in `agents/`
2. Extend `BaseAgent` class
3. Implement required methods:
   - `get_system_prompt()`
   - `_run()`
   - `validate_output()`
4. Add to scheduler if needed

### Switching AI Models

Models can be configured per initiative or globally:

```python
# In initiative config.yaml
model_provider: "grok"  # Switch to Grok

# Or in code
config = AgentConfig(
    model_provider="gemini",
    model_config={
        "temperature": 0.7,
        "max_tokens": 4000
    }
)
```

## Monitoring

### Logs
Logs are written to console and can be configured for file output.

### Metrics
Performance metrics are stored in Supabase and accessible via API.

### Budget Tracking
The system monitors spend and warns when approaching limits.

## Security

- **Multi-tenancy**: Row-level security isolates data between initiatives
- **API Authentication**: Bearer token authentication (implement as needed)
- **Secrets Management**: All sensitive data in environment variables
- **Rate Limiting**: Configurable limits on API calls and content generation

## Troubleshooting

### Common Issues

1. **Database connection errors**
   - Verify Supabase credentials in `.env`
   - Check network connectivity
   - Ensure RLS policies are configured

2. **API rate limits**
   - Adjust scheduling intervals
   - Implement exponential backoff
   - Check rate limit settings

3. **Content generation failures**
   - Verify AI model API keys
   - Check model-specific requirements
   - Review error logs for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

[Your License Choice]

## Support

For issues and questions:
- Open an issue on GitHub
- Check documentation in `/docs`
- Review example initiatives in `/initiatives`

## Research Questions

This platform is designed to answer:
- Which AI model performs best for autonomous campaign management?
- How do different models utilize available tools?
- What strategies emerge from autonomous orchestration?

## Roadmap

- [ ] Comment responder agent
- [ ] Advanced analytics dashboard
- [ ] A/B testing framework
- [ ] Video generation integration
- [ ] Multi-platform support (LinkedIn, Twitter)
- [ ] Real-time bidding optimization