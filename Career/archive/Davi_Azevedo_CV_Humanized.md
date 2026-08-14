# DAVI ALVES DE AZEVEDO
## Senior Full Stack Engineer | Node.js + .NET Core | Distributed Systems

Londrina, PR, Brazil | daviaaze@gmail.com | +55 43 99155-5500 | linkedin.com/in/daviaaze | github.com/daviazeve

---

## PROFESSIONAL SUMMARY

I build backend systems that stay standing when things go wrong. Over 6 years, I've learned that the most interesting engineering problems live at the intersection of scale, product, and people — designing architectures that gracefully handle millions of events, shipping features that real users care about, and owning decisions from whiteboard to production. I get genuinely excited about elegant system design: the kind where you anticipate the failure modes before they happen and the architecture makes the right thing easy and the wrong thing hard.

My sweet spot is distributed systems and microservices (Node.js, .NET Core, AWS), but what I bring beyond the stack is the instinct to push back when "fast" means "fragile" — and the communication skills to make that case to stakeholders and engineers alike. I've led cross-functional teams through platform modernizations, mentored developers into senior engineers, and launched new business verticals from zero to production. Fluent in English (C1 / IELTS 8.0), comfortable collaborating across time zones.

---

## TECHNICAL SKILLS

**Backend:** Node.js, TypeScript, C# (.NET Core), REST APIs, GraphQL, Microservices, Event-Driven Architecture  
**Frontend:** React.js, Next.js, Angular, Vue.js, React Native, TypeScript  
**Database:** PostgreSQL, MongoDB, SQL Server, Redis, Query Optimization  
**Cloud & DevOps:** AWS (SQS, S3, EC2, Lambda), Heroku, Docker, CI/CD, New Relic, Sentry  
**Practices:** Agile / Scrum, TDD, Code Review, System Design, Stakeholder Management, Mentorship

---

## PROFESSIONAL EXPERIENCE

### LUXURY ESCAPES — Senior Full Stack Engineer
**Florianópolis, SC, Brazil | May 2023 – Present**

**Car Hire Provider Integration — New Business Vertical Launch**
*Travel & Hospitality — B2C Car Rental*

Led the complete backend integration of a major international Car Hire provider, launching an entirely new business vertical. Architected the integration middleware, designed API contracts with the 3rd-party provider, and built a real-time inventory system with fault-tolerant booking flows — all within our existing microservices ecosystem. Worked cross-functionally with Product, Design, and the provider's engineering team to align on API SLAs and launch timeline. Zero critical bugs post-launch; thousands of bookings processed in the first quarter.

**Stack:** Node.js, TypeScript, PostgreSQL, Redis, AWS, Microservices  
**Key Results:** New vertical launched on schedule; zero critical bugs; real-time inventory from major international provider.

---

**Agent Platform — B2B2C Travel Agent Distribution System**
*Travel & Hospitality — B2B2C Distribution*

Architected the full-stack Agent Platform enabling travel agents to purchase inventory directly from Luxury Escapes. Early in development, the team was converging on a rapid solution for agent authentication and role-based access that met the surface requirements. I pushed back — the implicit authorization model would have blocked us the moment we needed per-agent commission tiers, regional inventory rules, and white-label access controls. I made the case for investing upfront in a claims-based authorization layer, which the team ultimately adopted. That decision paid off within months as the platform scaled: we added fine-grained permissions without a single auth refactor. Built the commission engine, invoicing system, and agent dashboard on this foundation. Reduced manual commission processing by 90%; hundreds of agents onboarded.

**Stack:** Node.js, TypeScript, React.js, PostgreSQL, Redis, AWS, Microservices  
**Key Results:** 90% reduction in manual commission processing; hundreds of agents onboarded; authorization architecture scaled without refactoring.

---

**Core Platform Engineering — Microservices & Developer Tooling**
*Travel & Hospitality — Core Platform*

Engineered critical platform features for commissions, invoicing, and reservations within a distributed microservices architecture. Integrated multiple 3rd-party APIs with circuit breakers and retry logic. Built observability dashboards (New Relic) that drove targeted API performance work. Developed internal CLI tooling adopted across the engineering team, reducing onboarding time for new services.

**Stack:** Node.js, TypeScript, React.js, PostgreSQL, Redis, Heroku, AWS, New Relic, Docker  
**Key Results:** API response times reduced via observability-driven optimization; internal tooling adopted team-wide.

---

### PORTER GROUP — Full Stack Developer
**Florianópolis, SC, Brazil | Aug 2021 – Mar 2023**

**IoT Security Platform — Large-Scale Device Management**
*Smart Buildings & Security — IoT*

Architected backend solutions supporting thousands of condominiums and over 100,000 IoT devices across Brazil. Designed event-driven microservices for real-time security monitoring, access control, and alert management using AWS infrastructure. This was where I learned scaling the hard way — message backpressure during peak hours nearly took down the alert pipeline before we implemented dead-letter queues and backoff strategies. Achieved 99.9% uptime and reduced alert latency by 60%.

**Stack:** C#, .NET Core, PostgreSQL, MongoDB, Redis, AWS SQS, Docker  
**Key Results:** Scaled to 100,000+ devices; 99.9% uptime; alert latency reduced by 60%.

---

**High-Volume Data Ingestion Service — 3rd Party Device Integration**
*IoT — Data Integration*

Engineered a high-throughput ingestion service processing millions of events daily from 3rd-party IoT devices. Built SDK adapters for multiple device protocols with AWS SQS event-driven pipelines and a unified data normalization layer. Defined throughput and error-rate KPIs to guide iteration. Reduced new device integration time from weeks to days, unifying data from 15+ manufacturers.

**Stack:** C#, .NET Core, AWS SQS, MongoDB, Redis, Docker, SDK Design  
**Key Results:** Millions of events processed daily; 15+ manufacturers unified; integration time reduced from weeks to days.

---

**Developer Experience & Legacy Modernization**
*Internal — Developer Tooling*

Led CI/CD pipeline improvements and legacy backend refactoring, reducing deployment time by 40%. Mentored junior developers on testing practices and system design patterns. Built automation scripts and documentation adopted across the engineering team.

**Stack:** C#, .NET Core, React.js, PostgreSQL, Redis, AWS  
**Key Results:** 40% faster deployments; improved team velocity through tooling and mentorship.

---

### HAVAN — Technical Lead Developer
**Brusque, SC, Brazil | Oct 2020 – Aug 2021**

**Product Modernization — Tech Lead**
*Retail — Internal Enterprise Systems*

Promoted to Tech Lead within months of joining. Led a squad of 4 developers through a complete modernization of a legacy internal product — migrating from a monolith to Angular and Vue.js frontends with .NET Core backends in an Agile environment. Managed stakeholder expectations across retail operations, engineering leadership, and end users. Delivered on time with zero critical bugs and a 45% improvement in user satisfaction. Mentored team members on clean architecture and testing — two of them grew into senior roles after this project.

**Stack:** .NET Core, C#, Angular, Vue.js, SQL Server, Redis  
**Key Results:** 4-person squad; on-time delivery with zero critical bugs; 45% user satisfaction improvement; 2 team members promoted to senior.

---

**CRM & Business Process Systems**
*Retail — Operations*

Maintained critical internal systems (CRM, purchase processing, document emission). Built operational dashboards that gave retail teams real-time visibility into workflows for the first time. Managed stakeholder relationships across operations to ensure reliability of day-to-day systems.

**Stack:** .NET Core, C#, Angular, SQL Server, Redis  
**Key Results:** Operational visibility improved through dashboards; critical business processes maintained.

---

### FATEC OURINHOS — Software Engineer (Internship)
**Ourinhos, SP, Brazil | Mar 2020 – Oct 2020**

**Zona Azul Digital — Smart Parking Mobile App**
*Smart City — Municipal Parking*

Developed a complete mobile app and backend that digitized the city's parking system, eliminating physical vendors. Built the React Native app with payment gateway integration and a Node.js backend with REST APIs. Created an admin dashboard with usage and revenue tracking. 5,000+ downloads in the first month; adopted as the official city solution.

**Stack:** React Native, Node.js, REST APIs, Payment Gateway Integration  
**Key Results:** 5,000+ downloads in first month; adopted as official city parking system.

---

## EDUCATION

**Bachelor's in Information Systems** — UNIFEBE, Brazil | 2021 – 2023  
**Bachelor's in Software Engineering** — UTFPR, Brazil | 2018 – 2019

---

## LANGUAGES

**Portuguese:** Native | **English:** C1 (IELTS Overall 8.0) — Full Professional Proficiency

---

## PROJECTS & COMMUNITY

**Student ID Platform — National Student Card Issuance (Volunteer Lead)**
When the original developer leading this project left abruptly, I inherited a half-built Next.js and Supabase codebase with 120+ student organizations waiting. Rather than starting over, I owned the full product lifecycle — from stabilizing the architecture to shipping the complete platform. Built two integrated applications: a configurable student-facing form (each organization customizes rich text, form fields, dropdowns, and image uploads independently) and an admin panel for PDF ID card generation, permission management, and organization onboarding. Wrote comprehensive unit, integration, and E2E test suites covering every feature. The platform now processes 100,000+ IDs annually. Currently extending it with WhatsApp/email notifications, payment processing, and virtual ID cards compliant with Brazilian digital identification laws.

**Self-Employed Workers Marketplace — Local Job Matching**
Designed and built a platform connecting self-employed workers (cleaning, construction, repair, gardening) with local clients. Workers create profiles, advertise services, and receive job requests through the platform. Built to give independent workers in underserved communities a free, accessible way to find work without intermediary fees.
