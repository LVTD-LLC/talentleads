# TalentLeads

TalentLeads is an agent-ready talent sourcing workspace for finding technical candidates, reviewing structured profile context, and starting precise outreach from one place.

The product is built for startup founders, operators, and recruiting teams that want a focused source of credible technical talent without running a traditional inbound hiring funnel. Today it turns public hiring intent, especially Hacker News "Who wants to be hired" threads, into a searchable profile database. The longer-term direction is to keep the workflow legible to AI agents while humans supervise fit, strategy, and outreach quality.

## What It Does

- Imports Hacker News "Who wants to be hired" comments into candidate profiles.
- Uses a Pydantic AI profile analyzer to extract role, skills, location, seniority, availability, links, and contact context.
- Generates profile embeddings with Jina and stores them in PostgreSQL with pgvector.
- Lets users filter profiles by title, description, location, tech stack, experience, remote preference, relocation status, capacity, and hiring thread.
- Supports authenticated profile browsing, private candidate details, saved outreach templates, and direct email outreach.
- Handles paid access through Stripe and dj-stripe.
- Includes a small token-authenticated Django Ninja API for blog publishing.

## Stack

- Python 3.13
- Django 6
- PostgreSQL with pgvector
- Redis and django-q2 for background jobs
- Pydantic AI with Gemini for profile extraction
- Jina embeddings for semantic profile vectors
- django-allauth for accounts
- Stripe, dj-stripe, and Mailgun/Anymail for billing and email
- Tailwind CSS, Webpack, Stimulus, and Turbo for the frontend
- Docker Compose for local development
- GitHub Actions, GHCR, and CapRover for production deploys

## Project Structure

```text
talentleads/        Django project settings, URLs, API mounting, auth, logging
profiles/           Candidate profile models, filters, views, AI analysis tasks
users/              Custom user model, account settings, billing, outreach templates
sales/              Sent outreach email tracking
blog/               Blog models, feeds, public views, and token-authenticated API
pages/              Marketing, pricing, product, and static page views
templates/          Django templates
frontend/           Webpack, Tailwind, Stimulus, and Turbo source
deployment/         Local, server, and worker Dockerfiles
```

## Local Development

### Prerequisites

- Docker and Docker Compose
- Node 18 if you run frontend commands outside Docker
- Poetry if you run Python tooling outside Docker

### Environment

Create a `.env` file in the repository root. These values are enough to boot the local Docker stack; real API keys are only needed for the workflows that call those providers.

```env
ENVIRONMENT=dev
DEBUG=True
SECRET_KEY=change-me-in-dev
SITE_URL=http://localhost:8010

POSTGRES_DB=talentleads
POSTGRES_USER=talentleads
POSTGRES_PASSWORD=talentleads
POSTGRES_HOST=db
POSTGRES_PORT=5432

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=talentleads
REDIS_DB=0

AWS_S3_ENDPOINT_URL=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

OPENAI_KEY=
GEMINI_API_KEY=
JINA_API_KEY=

STRIPE_LIVE_SECRET_KEY=
STRIPE_TEST_SECRET_KEY=
STRIPE_LIVE_MODE=False
DJSTRIPE_WEBHOOK_SECRET=
WEBHOOK_UUID=

MAILGUN_API_KEY=
HNJOBS_API_TOKEN=
HNJOBS_HOST=

SENTRY_DSN=
LOGFIRE_TOKEN=
```

### Run The App

```bash
make serve
```

The app runs at [http://localhost:8010](http://localhost:8010). The frontend dev server runs on port `9091`, MailHog is available at [http://localhost:8025](http://localhost:8025), and the backend runs migrations automatically during startup.

Useful follow-up commands:

```bash
make manage createsuperuser
make shell
make test
make restart-worker
```

## Frontend Assets

The Docker Compose frontend service runs the webpack dev server. For manual frontend work:

```bash
npm install
npm run start
npm run watch
npm run build
```

Production builds write assets into `frontend/build`, which Django reads through `webpack_boilerplate`.

## Profile Import Workflow

Profiles are created from Hacker News item IDs for "Who wants to be hired" posts.

1. Sign in as a staff user.
2. Open `/profiles/trigger-task/`.
3. Submit the Hacker News post ID.
4. The backend queues `get_hn_pages_to_analyze`, which schedules one analysis job per new comment.

In `DEBUG=True`, the importer only processes the first 20 comments from a thread to keep local runs small.

The worker pipeline:

1. Fetches the HN comment JSON.
2. Runs the Pydantic AI analyzer against the comment text.
3. Normalizes the extracted profile fields.
4. Creates or reuses related `Technology` rows.
5. Requests a Jina embedding for the comment text.
6. Stores the final `Profile` with pgvector indexes for future semantic workflows.

## Outreach Workflow

Authenticated users can create outreach templates under `/users/templates`. From a profile detail page, a user can send a saved template to the candidate email on the profile. The sender is added as the reply-to address and copied on the outgoing email.

Local email is routed through MailHog when `DEBUG=True`.

## Blog API

The Django Ninja API is mounted at `/api/`. Blog routes live under `/api/blog` and use bearer token authentication with each user's `api_token`.

Show or rotate a user's token with:

```bash
make manage show_api_token <username>
make manage regenerate_api_token <username>
```

Example:

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8010/api/blog/posts
```

Only superusers can create blog posts through the API.

## Quality Checks

Run the test suite through Docker:

```bash
make test
```

Run local formatting and linting with pre-commit if your local Python environment has the dev dependencies installed:

```bash
pre-commit run --all-files
```

The configured hooks include YAML checks, trailing whitespace cleanup, Ruff, djlint, and Poetry export to `requirements.txt`.

## Deployment

Pushes to `main` trigger two GitHub Actions workflows:

- `Deploy Prod Server` builds `deployment/Dockerfile.server`, pushes the server image to GHCR, and deploys it to CapRover.
- `Deploy Prod Workers` builds `deployment/Dockerfile.workers`, pushes the worker image to GHCR, and deploys it to the worker CapRover app.

Required deployment secrets are managed in GitHub Actions and CapRover.

## Data Notes

TalentLeads can store candidate contact details and profile context extracted from public posts. Treat exported profile data and sent outreach records as sensitive operational data, even when the original source is public.
