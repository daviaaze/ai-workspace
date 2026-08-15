---
name: job-tracker
description: Track job applications, LinkedIn inbound messages, analyze job fit against your CV, and discover companies/opportunities. Use when the user wants to log a job application, check pipeline status, analyze fit for a role, find companies, or manage job search activity.
---

# Job Tracker

Self-hosted job search tracker with AI-powered fit analysis. No SaaS, no subscriptions — all data lives in your workspace as Markdown/JSON.

## Features

- **Application Pipeline** — track jobs from "interested" → "applied" → "interview" → "offer" / "rejected"
- **LinkedIn Inbound** — log recruiter outreach, messages, and referrals linked to companies/roles
- **Fit Analysis** — score any job description against your CV with gap analysis and tailoring suggestions
- **Company Discovery** — search and research companies, save to watchlist
- **Analytics** — pipeline stats, response rates, source effectiveness

## Data Layout

```
~/.pi/data/job-tracker/
├── applications.yaml     # All tracked jobs
├── linkedin-inbound.yaml # Recruiter messages & outreach
├── companies.yaml        # Company watchlist & research
├── cv.md                 # Your master CV (imported from existing analysis)
└── config.yaml           # Search preferences, target roles, locations
```

## Available Tools

### 1. Job Pipeline (CLI: `aiw-job`)

```bash
# Add a job
aiw-job add --company "Acme Corp" --role "Senior Backend Engineer" --source "linkedin" --url "..." --status applied

# List pipeline
aiw-job list --status interview

# Update status
aiw-job update <id> --status "offer" --notes "Accepted!"

# Search
aiw-job search --keyword "backend" --company "Acme"

# Stats
aiw-job stats
```

### 2. LinkedIn Inbound (CLI: `aiw-job-linkedin`)

```bash
# Log recruiter outreach
aiw-job-linkedin add --recruiter "Jane Smith" --company "Acme" --role "Backend Eng" --message "..." --date "2026-01-15"

# List all inbound
aiw-job-linkedin list

# Link to existing application
aiw-job-linkedin link <inbound-id> --application-id <app-id>
```

### 3. Fit Analysis (CLI: `aiw-job-fit`)

```bash
# Analyze fit against a job description
aiw-job-fit analyze --jd-file ./jd.txt

# Or paste directly
aiw-job-fit analyze --jd-text "We're looking for a senior backend engineer with Node.js..."

# Compare multiple JDs at once
aiw-job-fit compare --jd-files ./jd1.txt ./jd2.txt ./jd3.txt
```

**Output includes:**
- Match score (0-100)
- Strengths (what you have)
- Gaps (what's missing)
- Tailored CV suggestions
- Interview prep focus areas

### 4. Company Discovery (CLI: `aiw-job-company`)

```bash
# Search companies
aiw-job-company search --keyword "travel tech" --location "remote"

# Research a specific company
aiw-job-company research --name "Acme Corp"

# Add to watchlist
aiw-job-company watch --name "Acme Corp" --notes "Great benefits, Rust stack"

# List watchlist
aiw-job-company list
```

### 5. Dashboard (CLI: `aiw-job-dashboard`)

```bash
# Full pipeline dashboard
aiw-job-dashboard

# Export to CSV
aiw-job-dashboard export --format csv --output ./job-search.csv
```

## Quick Start

### Initialize the tracker

```bash
aiw-job init
```

This creates the data directory and seeds your CV from the existing JIRA analysis.

### Log your first application

```bash
aiw-job add \
  --company "PlanitEasy" \
  --role "Full Stack Engineer" \
  --source "linkedin" \
  --url "https://linkedin.com/jobs/view/..." \
  --status applied \
  --notes "Referred by John"
```

### Analyze a job description

```bash
# Copy JD to clipboard, then:
aiw-job-fit analyze --jd-text "$(xclip -o)"
```

### Check pipeline

```bash
aiw-job list
aiw-job stats
```

## Pipeline Stages

```
INTERESTED → APPLIED → PHONE_SCREEN → TECHNICAL → ONSITE → OFFER → ACCEPTED
                                                                  ↘ REJECTED
                                                    ↘ GHOSTED
```

## Fit Analysis Methodology

1. **Parse JD** — extract requirements, responsibilities, nice-to-haves
2. **Compare against CV** — match skills, experience, impact
3. **Score** — weighted by importance (must-have vs nice-to-have)
4. **Gap analysis** — identify missing skills/experience
5. **Tailoring** — suggest CV bullets to emphasize
6. **Interview prep** — predict likely technical/behavioral topics

## LinkedIn Inbound Categories

| Type | Description |
|------|-------------|
| `message` | Direct recruiter message |
| `inmail` | LinkedIn InMail |
| `referral` | Internal referral offer |
| `connection` | Connection request with job context |
| `post_reaction` | Recruiter engaging with your content |

## Data Schema

### applications.yaml

```yaml
- id: app_001
  company: Acme Corp
  role: Senior Backend Engineer
  url: https://linkedin.com/jobs/view/...
  source: linkedin
  status: interview
  date_applied: 2026-01-15
  date_updated: 2026-01-20
  salary_range: $150k-$180k
  location: Remote
  notes: Referred by John. Phone screen scheduled 1/25.
  linked_inbound: [inb_001]       # linked LinkedIn inbound IDs
  fit_score: 82
  tags: [nodejs, distributed-systems]
```

### linkedin-inbound.yaml

```yaml
- id: inb_001
  recruiter: Jane Smith
  company: Acme Corp
  role: Senior Backend Engineer
  type: message
  message: "Hi Davi, your profile looks great for..."
  date: 2026-01-12
  responded: true
  date_responded: 2026-01-12
  linked_application: app_001
  notes: Sent CV, waiting for reply
```

### companies.yaml

```yaml
- id: comp_001
  name: Acme Corp
  industry: Travel Tech
  size: 200-500
  location: Sydney / Remote
  website: https://acme.com
  careers_page: https://acme.com/careers
  notes: Rust + TypeScript stack. Series B.
  watch_status: watching          # watching | applied | interviewed | offer | rejected
  tags: [rust, travel, b2b]
  date_added: 2026-01-10
```

## Integration with pi

The job-tracker skill integrates with pi's existing tools:

- **Web search** — `web_search` for company research and job discovery
- **pi-worker-search** — parallel research on companies
- **fetch_content** — scrape job postings and career pages
- **LLM analysis** — fit scoring and CV tailoring via pi's model
- **Knowledge base** — store company research in `job-tracker` KB

## AI-Powered Workflows

### Auto-analyze a job posting URL

```
1. fetch_content the job posting URL
2. Extract structured JD (title, requirements, responsibilities)
3. Run fit analysis against cv.md
4. Save to applications.yaml with fit_score
5. Output: score, gaps, tailoring suggestions
```

### Weekly job search report

```
1. Summarize this week's applications (new, updated)
2. LinkedIn inbound received
3. Upcoming interviews
4. Pipeline conversion rates
5. Recommendations: roles to follow up, companies to research
```

### Company deep-dive

```
1. web_search for company news, funding, culture
2. fetch_content their careers page
3. Cross-reference with your skills
4. Save research to companies.yaml
5. Output: fit assessment, role recommendations, application strategy
```

## Ollama Models Available

| Model | Best for |
|-------|----------|
| `qwen3.5:9b` | General fit analysis, JD parsing |
| `qwen3:14b` | Deep analysis, company research |
| `gemma3:12b` | CV tailoring suggestions |
| `deepseek-r1:14b` | Complex reasoning, interview prep |

## Troubleshooting

**"Data directory not found":**
```bash
aiw-job init
```

**No CV found for fit analysis:**
```bash
aiw-job cv import ~/path/to/cv.md
```

**Corrupted YAML:**
```bash
aiw-job doctor
```
