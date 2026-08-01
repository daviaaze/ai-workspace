# DAVI ALVES DE AZEVEDO
## Senior Full Stack Engineer | Node.js + .NET Core | Distributed Systems

Londrina, PR, Brazil | daviaaze@gmail.com | +55 43 99155-5500 | linkedin.com/in/daviaaze | github.com/daviazeve

---

## PROFESSIONAL SUMMARY

I build backend systems that stay standing when things go wrong — scaled an IoT platform to 100K+ devices at 99.9% uptime, launched a new B2B2C business vertical generating ~$500K in its first 6 months, and led platform modernizations from whiteboard to production. My sweet spot is distributed systems and microservices (Node.js, TypeScript, .NET Core, PostgreSQL, Redis, AWS), but what I bring beyond the stack is the instinct to push back when "fast" means "fragile" — and the communication skills to make that case across engineering, product, and business teams. Fluent in English (C1 / IELTS 8.0), comfortable collaborating across time zones in Australia, Singapore, and the Americas.

---

## TECHNICAL SKILLS

**Backend:** Node.js, TypeScript, C# (.NET Core), REST APIs, Microservices, Event-Driven Architecture, SDK Design, GraphQL
**Cloud & Infrastructure:** AWS (SQS, S3, EC2, Lambda), Docker, CI/CD, Heroku, New Relic, Sentry
**Databases:** PostgreSQL, MongoDB, SQL Server, Redis, Query Optimization
**Frontend:** React.js, Next.js, Angular, Vue.js, React Native, TypeScript
**Testing & Quality:** Jest, xUnit, TDD, Integration Testing, E2E Testing, Code Review
**Practices:** System Design, Technical Leadership, Agile / Scrum, Mentorship, Stakeholder Management

---

## PROFESSIONAL EXPERIENCE

### LUXURY ESCAPES — Senior Full Stack Engineer
**Florianópolis, SC, Brazil | May 2023 – Present**

**Car Hire Provider Integration — New Business Vertical Launch**

- Launched a new Car Hire business vertical by architecting the complete backend integration with a major international provider — 510 bookings in Q1, 1,500+ in the first year, zero critical bugs post-launch
- Designed API contracts with the 3rd-party provider and built a real-time inventory system with dynamic pricing and fault-tolerant booking flows within the microservices ecosystem
- Drove cross-functional alignment across Product, Design, and the external provider's engineering team on UX flow, API SLAs, and launch timeline — delivered on schedule

**Stack:** Node.js, TypeScript, PostgreSQL, Redis, AWS, REST APIs, Microservices

---

**Agent Platform — B2B2C Travel Agent Distribution System**

- Architected and developed the full-stack Agent Platform enabling travel agents to purchase inventory directly from Luxury Escapes — generated ~$500K in agent-driven revenue in the first 6 months
- Built the commission calculation engine, automated invoicing with reconciliation, and agent management dashboard with role-based access control
- Pushed back on an implicit authorization model that would have blocked per-agent commission tiers and white-label access — advocated for and built a claims-based authorization layer supporting 3 permission tiers (Assistant, Worker, Admin) plus multi-agency oversight roles, scaling to 300+ agents without a single auth refactor
- Reduced manual commission processing by 90%, enabling rapid market expansion with 300+ agents onboarded

**Stack:** Node.js, TypeScript, React.js, PostgreSQL, Redis, AWS, Microservices

---

**Core Platform Engineering — Hotel Provider Integrations & Self-Service**

- Optimizing hotel provider integrations across the platform — improving data consistency, reducing booking errors, and streamlining API communication with multiple 3rd-party providers
- Building a self-service portal enabling hotel staff to directly manage inventory, property content, and bookings within the Luxury Escapes ecosystem — eliminating manual operational workflows
- Optimized dashboard API endpoints from 1.2s to 400ms (67% improvement) using New Relic observability data to identify and address bottlenecks

**Stack:** Node.js, TypeScript, React.js, PostgreSQL, Redis, Heroku, AWS, New Relic, Docker

---

### PORTER GROUP — Full Stack Developer
**Florianópolis, SC, Brazil | Aug 2021 – Mar 2023**

**IoT Security Platform — Large-Scale Device Management**

- Architected backend solutions supporting thousands of condominiums and 100,000+ IoT devices across Brazil
- Designed event-driven microservices for real-time security monitoring, access control, and alert management on AWS infrastructure
- Achieved 99.9% uptime for critical security systems by implementing fault-tolerant patterns — retry, dead-letter queues, and circuit breakers — learned scaling the hard way when message backpressure nearly took down the alert pipeline during peak hours
- Reduced alert latency by 60% through data-driven optimization of message processing pipelines

**Stack:** C#, .NET Core, PostgreSQL, MongoDB, Redis, AWS SQS, Docker

---

**High-Volume Data Ingestion Service — 3rd Party Device Integration**

- Engineered a high-throughput ingestion service processing millions of events daily from 3rd-party IoT devices
- Built SDK adapters for multiple device protocols using event-driven architecture with AWS SQS, creating a unified data normalization layer across 15+ manufacturers
- Reduced new device integration time from weeks to days by defining throughput and error-rate KPIs to guide pipeline iteration

**Stack:** C#, .NET Core, AWS SQS, MongoDB, Redis, Docker, SDK Design

---

**Developer Experience & Legacy Modernization**

- Reduced deployment time by 40% through CI/CD pipeline improvements, legacy backend refactoring, and internal automation scripts adopted team-wide
- Mentored 2–3 junior developers on testing best practices (Jest, xUnit, TDD), code review standards, and system design patterns — two grew into senior roles after the engagement
- Built internal documentation and onboarding guides that standardized development workflows across the engineering team

**Stack:** C#, .NET Core, React.js, PostgreSQL, Redis, AWS

---

### HAVAN — Technical Lead Developer
**Brusque, SC, Brazil | Oct 2020 – Aug 2021** · Recruited by Porter Group for IoT platform role

**Product Modernization — Tech Lead**

- Promoted to Tech Lead within months of joining — led a squad of 4 developers through complete modernization of a legacy internal product
- Migrated from monolithic architecture to Angular and Vue.js frontends with .NET Core backends in an Agile/Scrum environment
- Managed stakeholder expectations across retail operations, engineering leadership, and end users — delivered on time with zero critical bugs
- Improved user satisfaction by 45%; mentored team on clean architecture, testing (xUnit), and code review — two members promoted to senior roles after the project

**Stack:** .NET Core, C#, Angular, Vue.js, SQL Server, Redis

---

**CRM & Business Process Systems**

- Maintained 5 critical internal systems — CRM, purchase processing, document emission, and operational dashboards — supporting retail operations across ~130 stores
- Built operational dashboards and a notification engine that gave retail teams real-time workflow visibility into daily operations for the first time
- Ensured system reliability for mission-critical retail processes, managing stakeholder expectations across operations, engineering, and business teams

**Stack:** .NET Core, C#, Angular, SQL Server, Redis

---

### FATEC OURINHOS — Software Engineer (Internship)
**Ourinhos, SP, Brazil | Mar 2020 – Oct 2020**

**Zona Azul Digital — Smart Parking Mobile App**

- Developed a complete mobile app and backend that digitized the city's rotational parking system, eliminating the need for physical vendors
- Built the React Native mobile app with payment gateway integration and a Node.js backend with REST APIs
- Created an administrative dashboard for city officials with usage KPIs and revenue tracking — 5,000+ downloads in the first month, adopted as the official city parking solution

**Stack:** React Native, Node.js, REST APIs, Payment Gateway Integration

---

## ADDITIONAL PROJECTS

**Student ID Platform — National Student Card Issuance (Volunteer Lead)**
Inherited and fully delivered a Next.js + Supabase platform serving 120+ student organizations across Brazil, processing 100,000+ digital student ID cards annually. Built two integrated applications: a configurable student-facing form (per-organization customization: rich text, form fields, dropdowns, image uploads) and an admin panel (PDF card generation, RBAC permission management, organization onboarding). Implemented comprehensive unit (Jest), integration, and E2E test suites. Extending with WhatsApp/email notifications, payment integration, and virtual ID cards compliant with Brazilian digital ID regulations.

**Self-Employed Workers Marketplace — Local Job Matching**
Designed a platform connecting self-employed workers (cleaning, construction, repair, gardening) with local clients. Workers create profiles and receive job requests — built for free, accessible job discovery in underserved communities.

---

## EDUCATION

**Bachelor's in Information Systems** — Centro Universitário de Brusque (UNIFEBE), Brazil | 2021 – 2023
**Bachelor's in Software Engineering** — Universidade Tecnológica Federal do Paraná (UTFPR), Brazil | 2018 – 2019

---

## LANGUAGES

**Portuguese:** Native | **English:** C1 (IELTS Overall 8.0) — Full Professional Proficiency
