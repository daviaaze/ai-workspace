"""CareerOps MVP — discovery de vagas (scraping direto + RSS + IMAP)."""
from __future__ import annotations

import email
import imaplib
import re
import socket
import ssl
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import httpx


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

TRAVEL_TERMS = re.compile(
    r"\b(backend|node|typescript|serverless|travel|booking|gds|sabre|engineer)\b",
    re.I,
)


def _get_text(node) -> str:
    return "".join(node.itertext()).strip() if node is not None else ""


def scrape_career_page(url: str, timeout: int = 20) -> list[dict[str, Any]]:
    """Scraping direto de career page via JSON-LD e heuristicas."""
    jobs: list[dict[str, Any]] = []
    try:
        r = httpx.get(url, headers=HEADERS, timeout=timeout, follow_redirects=True)
        r.raise_for_status()
    except Exception as e:
        return [{"erro": f"{url}: {e}", "fonte": url}]

    # JSON-LD
    for m in re.finditer(r'"@type"\s*:\s*"JobPosting"', r.text):
        start = r.text.rfind("{", 0, m.start())
        depth, end = 0, start
        for i in range(start, len(r.text)):
            if r.text[i] == "{":
                depth += 1
            elif r.text[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1; break
        import json
        try:
            data = json.loads(r.text[start:end])
            titulo = data.get("title", "")
            empresa = data.get("hiringOrganization", {}).get("name", url)
            descricao = data.get("description", "")
            if TRAVEL_TERMS.search(titulo + " " + descricao):
                jobs.append({
                    "empresa": empresa,
                    "titulo": titulo,
                    "url": data.get("url", url),
                    "descricao": descricao[:500],
                    "fonte": url,
                })
        except Exception:
            pass

    # Heuristic: links com textos de vaga
    seen = {j.get("url") for j in jobs}
    for m in re.finditer(r'href="([^"]+)"[^>]*>([^<]{10,80})</a>', r.text):
        href, text = m.group(1), m.group(2)
        if TRAVEL_TERMS.search(text) and any(
            k in text.lower() for k in ("engineer", "backend", "node", "typescript", "serverless", "senior")
        ):
            full = urljoin(url, href)
            if full not in seen:
                seen.add(full)
                jobs.append({
                    "empresa": url.split("//")[1].split("/")[0],
                    "titulo": text.strip(),
                    "url": full,
                    "descricao": "",
                    "fonte": url,
                })
    return jobs


def parse_rss_feed(url: str, timeout: int = 20) -> list[dict[str, Any]]:
    """Parser de RSS feed."""
    jobs: list[dict[str, Any]] = []
    try:
        r = httpx.get(url, headers=HEADERS, timeout=timeout, follow_redirects=True)
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception as e:
        return [{"erro": f"{url}: {e}", "fonte": url}]

    items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    for it in items:
        titulo = _get_text(it.find("title") or it.find("{http://www.w3.org/2005/Atom}title"))
        link = _get_text(it.find("link") or it.find("{http://www.w3.org/2005/Atom}link"))
        descricao = _get_text(it.find("description") or it.find("{http://www.w3.org/2005/Atom}summary"))
        if TRAVEL_TERMS.search(titulo + " " + descricao):
            jobs.append({
                "empresa": url.split("//")[1].split("/")[0],
                "titulo": titulo,
                "url": link or url,
                "descricao": descricao[:500],
                "fonte": url,
            })
    return jobs


def parse_imap_alerts(
    host: str, user: str, password: str, mailbox: str = "INBOX",
    folder_filter: str = "Alertas", limit: int = 20,
) -> list[dict[str, Any]]:
    """Parser IMAP da caixa de alertas."""
    jobs: list[dict[str, Any]] = []
    try:
        ctx = ssl.create_default_context()
        with imaplib.IMAP4_SSL(host, ssl_context=ctx) as m:
            m.login(user, password)
            m.select(mailbox)
            status, data = m.search(None, "UNSEEN")
            if status != "OK":
                return []
            ids = data[0].split()[-limit:]
            for num in ids:
                st, msg = m.fetch(num, "(RFC822)")
                if st != "OK":
                    continue
                raw = msg[0][1]
                msg_obj = email.message_from_bytes(raw)
                subject = email.header.decode_header(msg_obj["Subject"])
                subject_str = subject[0][0]
                if isinstance(subject_str, bytes):
                    subject_str = subject_str.decode(subject[0][1] or "utf-8", errors="replace")
                body = ""
                if msg_obj.is_multipart():
                    for part in msg_obj.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode(errors="replace")
                            break
                else:
                    body = msg_obj.get_payload(decode=True).decode(errors="replace")
                jobs.append({
                    "empresa": msg_obj.get("From", "?"),
                    "titulo": subject_str,
                    "url": "",
                    "descricao": body[:800],
                    "fonte": "imap",
                })
    except Exception as e:
        jobs.append({"erro": f"IMAP {e}", "fonte": "imap"})
    return jobs
