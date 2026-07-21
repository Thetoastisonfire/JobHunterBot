"""Builds and sends the digest email."""
import re
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any


def _build_plain(jobs: list[dict[str, Any]], subject: str) -> str:
    lines = [subject, ""]
    for j in jobs:
        lines += [j["title"], "  " + j["company"] + "  ~  " + j["location"],
                  "  Keyword: " + j["keyword"], "  " + j["link"], ""]
    return "\n".join(lines)


def _build_html(jobs: list[dict[str, Any]], count: int) -> str:
    cards = ""
    for j in jobs:
        excerpt = re.sub(r"<[^>]+>", "", str(j["excerpt"])).strip()
        if excerpt and not excerpt.endswith("..."):
            excerpt += "..."
        company_loc = "   ".join(filter(None, [j["company"], j["location"]]))
        cards += (
            "<div style='border:1px solid #e5e7eb;border-radius:10px;padding:18px 20px;"
            "margin-bottom:14px;background:#fff;'>"
            "<p style='margin:0 0 4px;font-size:11px;color:#9ca3af;text-transform:uppercase;"
            "letter-spacing:.06em;'>via \"" + j["keyword"] + "\"</p>"
            "<h3 style='margin:0 0 4px;font-size:16px;color:#111827;line-height:1.35;'>" + j["title"] + "</h3>"
            + ("<p style='margin:0 0 10px;font-size:12px;color:#6b7280;'>" + company_loc + "</p>" if company_loc else "")
            + ("<p style='margin:0 0 12px;font-size:13px;color:#374151;line-height:1.5;'>" + excerpt + "</p>" if excerpt else "")
            + "<a href='" + j["link"] + "' style='display:inline-block;background:#1A56B0;color:#fff;"
            "padding:7px 16px;border-radius:6px;text-decoration:none;font-size:13px;font-weight:500;'>"
            "View job -></a></div>"
        )

    return (
        "<!DOCTYPE html><html><body style='margin:0;padding:0;background:#f9fafb;font-family:Arial,sans-serif;'>"
        "<div style='max-width:580px;margin:32px auto;padding:0 16px 40px;'>"
        "<div style='background:#1A56B0;border-radius:10px;padding:24px 28px;margin-bottom:24px;'>"
        "<h2 style='margin:0;color:#fff;font-size:22px;'>[!] " + str(count) + " new job" + ("s" if count > 1 else "") + " found</h2>"
        "<p style='margin:6px 0 0;color:#bfdbfe;font-size:13px;'>" + datetime.now().strftime("%B %d, %Y at %H:%M UTC") + " via Adzuna</p>"
        "</div>" + cards +
        "<p style='text-align:center;color:#9ca3af;font-size:11px;margin-top:24px;'>"
        "Edit config.json in your repo to change keywords, blacklist, or experience filter.</p>"
        "</div></body></html>"
    )


def send_email(jobs: list[dict[str, Any]], email_from: str, email_password: str, email_to: str) -> None:
    count = len(jobs)
    subject = "[!] " + str(count) + " new job" + ("s" if count > 1 else "") + " - " + datetime.now().strftime("%b %d, %Y")

    plain = _build_plain(jobs, subject)
    html = _build_html(jobs, count)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = email_from
    msg["To"]      = email_to
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html,  "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(email_from, email_password)
        server.sendmail(email_from, email_to, msg.as_string())

    print("['V'] Email sent - " + str(count) + " jobs")
