# Engine — Senior Software Engineer, Backend — LATAM

- **Requisition:** 7994754003
- **Official URL:** https://job-boards.greenhouse.io/engine/jobs/7994754003
- **Model:** Full-time contractor, candidates based in Latin America
- **Status:** Revised materials ready; prior Greenhouse verification rejected two codes; NOT submitted. User requested Orca's embedded browser, which is unavailable in this session.
- **Fit:** Strong domain match; Java/Kotlin and IaC/monitoring stack gaps remain (no ATS score can be verified)

## Requirement mapping

| Requirement | Evidence | Assessment |
|---|---|---|
| AI tools as primary development interface | Davi confirmed daily primary use of Orca with OMP for implementation, review, and verification | Meets |
| Strong system design | Travel booking/supplier systems; B2B2C platform; IoT architecture supporting 100K+ devices | Meets |
| Delivery of complex systems | Car-hire vertical, agent platform, event-driven IoT platform | Meets |
| Self-directed delivery | End-to-end architecture, provider coordination, production ownership | Meets |
| Ambiguity and shifting priorities | External provider contracts, cross-functional travel launches, legacy modernization | Meets |
| Communication with non-technical stakeholders | Product, Design, provider engineering, Commercial Operations, business workflows | Meets |
| Java/Kotlin | Not confirmed; explicitly nice-to-have, not required | Gap accepted by posting |
| SQL and relational databases | PostgreSQL and SQL Server; query optimization | Meets |
| Terraform, Datadog, Splunk | Not confirmed; nice-to-have only | Gap accepted by posting |

## Form answers

| Field | Answer |
|---|---|
| First Name | Davi |
| Last Name | Alves de Azevedo |
| Preferred First Name | Davi |
| Email | daviaaze@gmail.com |
| Phone | +55 43 99155-5000 |
| Location | Londrina, Paraná, Brazil |
| LinkedIn | https://www.linkedin.com/in/daviaaze |
| Based in Latin America? | Yes |
| Years of experience | 5–10 |
| Salary expectations | USD 100,000 annual gross contractor compensation, negotiable based on scope, equity, and the total package. |
| Legally authorized to work where the position is based? | No — Davi confirmed he does not have US work authorization. The listing body describes a LATAM contractor role, but Greenhouse displays `Remote - US`; do not claim US work authorization. |
| Resume | Revised one-page `CV_Davi_Azevedo_Engine.pdf` (DOCX and Markdown source also available) |
| Cover letter | Revised `cover-letter.txt` |

## Application notes

- Greenhouse's top-level location metadata says `Remote - US`, but the title, office object, and job description explicitly say `Remote - LATAM` and `full-time contractor role for candidates based in Latin America`.
- The official posting does not publish compensation. Third-party copies suggest USD 75K–120K, but this is not company-confirmed.
- Davi explicitly authorized submitting **Engine only**. The submit action triggered email verification. Two user-provided codes were entered exactly, but Greenhouse returned `Incorrect security code` and HTTP 428 on the later attempt. No success page or receipt was observed. Stop automated retries; Davi should complete the verification manually in his own browser or contact Greenhouse support. Checkly is not authorized for submission.
- The previous attempt used isolated headless Chromium, not a browser Davi could interact with. Davi clarified that he wants Orca's embedded browser and supplied the `orca-work` launcher. Its wrapper passes `--user-data-dir` to CLI commands, which that build rejects; the exact same underlying Orca 1.4.207 executable works with `ORCA_USER_DATA_PATH=$HOME/.config/orca`. However, `orca status` reports the app not running, and `orca open --json` times out waiting for a desktop window because this session has no display. `xd://open_url` opened the Engine URL in the user's browser, but it did not prove an Orca tab or enable remote control. Do not substitute a headless browser or OMP relay for Orca.

## Pre-submission review (29 Sep 2026)

- The first PDF had split words, compressed skill/education extraction, and a page break inside Luxury Escapes. The regenerated one-page PDF is tagged, visually legible, and extracts contact details, skills, roles, dates, and education in order.
- Removed a student-ID claim of 100,000 annually: the verified record has only 10,000+ cards over 18 months for that project. Removed precise performance/reliability metrics not documented in the validated metric register; retained 100,000+ IoT devices.
- The resume emphasizes direct travel integrations, system design, stakeholder communication, and primary AI-assisted coding. Its strongest missing nice-to-haves are Java/Kotlin and Terraform/Datadog/Splunk; do not imply those skills.
- Recruiter risks: the employer's primary Java/Kotlin stack differs from Davi's production Node.js/.NET stack; Orca/OMP is less familiar than Claude/Cursor and needs a concrete interview example; USD 100k is unconfirmed against Engine's unpublished LATAM band; Greenhouse's `Remote - US` location and authorization question may create a false-negative despite explicit LATAM-contractor wording.
- No automated ATS ranking can be measured without Engine's actual screening rules. Checkly remains outside this authorization.
