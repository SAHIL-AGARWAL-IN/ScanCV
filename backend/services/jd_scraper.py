import json
import logging
import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

from backend.services.groq_parser import _call_groq, _get_client

logger = logging.getLogger("ats_resume_scorer")

USER_AGENTS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Common selectors for specific ATS / job portals
SPECIFIC_SELECTORS = [
    # Greenhouse
    "#content",
    ".job-description",
    "div#app",
    # Lever
    ".section-wrapper",
    ".posting-headline",
    # LinkedIn public jobs
    ".show-more-less-html__markup",
    ".description__text",
    ".jobs-description__content",
    # Indeed
    "#jobDescriptionText",
    ".jobsearch-JobComponent-description",
    # Workable
    "[data-ui='job-description']",
    ".job-description",
    # Ashby
    "[class*='JobPosting']",
    "[class*='description']",
    # Generic semantic tags
    "article",
    "main",
    "[role='main']",
]


def _try_workday_cxs_api(url: str) -> Optional[Dict[str, Any]]:
    """
    Workday uses client-side SPA rendering with an internal CXS API:
    https://<tenant>.<cluster>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/job/...
    """
    parsed = urlparse(url)
    if "myworkdayjobs.com" not in parsed.netloc:
        return None

    # Example URL: /en-US/External_Career_Site/job/India---Bangalore/Summer-2027-Intern---Software-Engineer_JR337715
    # Target CXS: /wday/cxs/<tenant>/External_Career_Site/job/India---Bangalore/Summer-2027-Intern---Software-Engineer_JR337715
    tenant = parsed.netloc.split(".")[0]
    path_parts = [p for p in parsed.path.split("/") if p]

    # Find the career site and job path
    # Usually: [lang, site_name, 'job', ...]
    try:
        if len(path_parts) >= 3 and "job" in path_parts:
            job_idx = path_parts.index("job")
            site_name = path_parts[job_idx - 1]
            job_subpath = "/".join(path_parts[job_idx:])
            cxs_url = f"{parsed.scheme}://{parsed.netloc}/wday/cxs/{tenant}/{site_name}/{job_subpath}"

            headers = {
                "User-Agent": USER_AGENTS,
                "Accept": "application/json",
            }
            res = requests.get(cxs_url, headers=headers, timeout=12)
            if res.status_code == 200:
                data = res.json()
                job_info = data.get("jobPostingInfo", {})
                title = job_info.get("title") or "Workday Job Posting"
                raw_desc = job_info.get("jobDescription", "")
                clean_desc = BeautifulSoup(raw_desc, "html.parser").get_text(separator="\n", strip=True)

                company = tenant.replace("-", " ").title()
                return {
                    "title": title,
                    "company": company,
                    "description": clean_desc,
                }
    except Exception as exc:
        logger.debug(f"Workday CXS attempt skipped: {exc}")

    return None


def _extract_json_ld_job(soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    """Extract schema.org JobPosting structured data embedded in script tags."""
    for script in soup.find_all("script", type="application/ld+json"):
        if not script.string:
            continue
        try:
            data = json.loads(script.string.strip())
            # Can be a single dict or @graph array
            items = data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []

            for item in items:
                if isinstance(item, dict) and item.get("@type") == "JobPosting":
                    title = item.get("title", "")
                    raw_desc = item.get("description", "")
                    clean_desc = BeautifulSoup(raw_desc, "html.parser").get_text(separator="\n", strip=True)

                    org_info = item.get("hiringOrganization") or {}
                    company = org_info.get("name", "") if isinstance(org_info, dict) else str(org_info)

                    if clean_desc and len(clean_desc) > 100:
                        return {
                            "title": title,
                            "company": company,
                            "description": clean_desc,
                        }
        except Exception:
            continue
    return None


def _clean_soup(soup: BeautifulSoup) -> None:
    """Strip navigation, footers, scripts, and invisible elements."""
    for element in soup(["script", "style", "noscript", "nav", "footer", "header", "aside", "form", "svg", "iframe"]):
        element.decompose()

    for tag in soup.find_all(attrs={"class": re.compile(r"cookie|banner|modal|popup|newsletter|signup", re.I)}):
        tag.decompose()
    for tag in soup.find_all(attrs={"id": re.compile(r"cookie|banner|modal|popup|newsletter", re.I)}):
        tag.decompose()


def scrape_job_url(url: str) -> Dict[str, Any]:
    """
    Scrapes a job posting from any website URL (including Workday, Greenhouse,
    Lever, LinkedIn, Indeed, or custom careers sites).
    """
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("Invalid URL. Please enter a full URL including http:// or https://")

    # 1. Check if site is Workday and try CXS API first
    workday_result = _try_workday_cxs_api(url)
    if workday_result and len(workday_result.get("description", "")) > 150:
        logger.info("Successfully extracted job posting from Workday CXS API")
        return {
            "success": True,
            "url": url,
            "title": workday_result["title"],
            "company": workday_result.get("company", ""),
            "job_description": workday_result["description"],
            "raw_character_count": len(workday_result["description"]),
        }

    headers = {
        "User-Agent": USER_AGENTS,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch job posting URL '{url}': {e}")
        raise ValueError(f"Could not reach {parsed.netloc}: {e}")

    soup = BeautifulSoup(response.text, "html.parser")
    page_title = soup.title.get_text(strip=True) if soup.title else "Job Posting"

    # 2. Check for Schema.org JSON-LD JobPosting BEFORE decomposing scripts!
    json_ld_job = _extract_json_ld_job(soup)
    if json_ld_job:
        logger.info("Successfully extracted JobPosting from JSON-LD schema")
        title = json_ld_job.get("title") or page_title
        company = json_ld_job.get("company", "")
        desc = json_ld_job.get("description", "")
        formatted_jd = f"Job Title: {title}\nCompany: {company}\n\n{desc}" if company else f"Job Title: {title}\n\n{desc}"
        return {
            "success": True,
            "url": url,
            "title": title,
            "company": company,
            "job_description": formatted_jd,
            "raw_character_count": len(formatted_jd),
        }

    # 3. Clean page of scripts/styles and parse HTML
    _clean_soup(soup)

    extracted_text = ""
    for sel in SPECIFIC_SELECTORS:
        matches = soup.select(sel)
        if matches:
            combined = "\n\n".join(m.get_text(separator="\n", strip=True) for m in matches if m.get_text(strip=True))
            if len(combined) > 200:
                extracted_text = combined
                break

    # 4. Universal fallback: find the largest text container or whole body
    if not extracted_text or len(extracted_text) < 150:
        body = soup.find("body")
        if body:
            extracted_text = body.get_text(separator="\n", strip=True)
        else:
            extracted_text = soup.get_text(separator="\n", strip=True)

    cleaned_lines = [line.strip() for line in extracted_text.splitlines() if line.strip()]
    raw_clean_text = "\n".join(cleaned_lines)

    # 5. OpenGraph fallback if text is still short
    if len(raw_clean_text) < 100:
        og_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
        if og_desc and og_desc.get("content"):
            raw_clean_text = og_desc["content"]

    if len(raw_clean_text) < 50:
        raise ValueError(
            "The target webpage did not contain readable text or is protected by a login wall. "
            "Please copy and paste the job description text directly."
        )

    # 6. AI structuring using Groq
    try:
        client = _get_client()
        system_prompt = (
            "You are a job description extraction assistant. Given raw scraped webpage text, "
            "extract the clean, comprehensive job description. "
            "Format the output clearly with: "
            "\nJob Title: ...\nCompany: ...\nKey Responsibilities: ...\nRequired Skills & Qualifications: ...\nPreferred Skills: ...\n"
            "Do NOT invent details. If company or title is unclear, state 'Not specified'. "
            "Do NOT include website navigation text, cookies, or unrelated website links."
        )
        user_prompt = f"Scraped Page URL: {url}\nPage Title: {page_title}\n\nWebpage Text:\n{raw_clean_text[:6000]}"
        structured_jd = _call_groq(client, system_prompt, user_prompt)
        final_jd = structured_jd.strip()
    except Exception as exc:
        logger.warning(f"Groq JD cleanup failed ({exc}), falling back to raw extracted text.")
        final_jd = raw_clean_text[:3000]

    return {
        "success": True,
        "url": url,
        "title": page_title,
        "job_description": final_jd,
        "raw_character_count": len(final_jd),
    }
