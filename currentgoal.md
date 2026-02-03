For Module 4 – Week 1 (Data sources + ingestion), you want sources that are (1) practical to integrate, (2) legally/operationally safer than heavy scraping, and (3) give structured fields you can normalize into MongoDB. Below are the best “things we can use” for StudentHub (no code), with exactly what you’ll store and why.

1) Jobs/Internships source: Apify scrapers (Internshala example)
What it is
Apify provides “Actors” (hosted scrapers) that return structured JSON/CSV for sites that don’t offer easy public APIs. An example you can use in StudentHub is Internshala Scrapper (community actor) which scrapes internships from Internshala using filters like category, location, WFH, etc.
​

Why it fits Module 4 Week 1
It gives you external internship listings with filters, which matches your Module 4 requirement (external job/internship listings).
​

It outputs structured data so your backend mainly does normalization + ranking, not “HTML parsing”.
​

What data you can expect to store (normalization plan)
Create a unified opportunities_jobs schema (even if sources differ):

source: "internshala_apify"
​

source_url: original listing URL (for click-through)

title, company, location, work_mode (WFH/onsite/hybrid if available)
​

stipend/salary (if available)

skills_required (important for your matching/reco engine)

posted_at / scraped_at

apply_by (deadline if available)

description_snippet (short, to avoid storing large copyrighted text)

Important real-world considerations
Cost: the example actor lists pricing like “$5 / 1,000 results” and supports “Try for free”, so decide your weekly pull size and cache results.
​

Reliability: community actors can change; Week 1 should include adding a fallback plan (another actor / another source).
​

2) Competitions/Hackathons: Devpost as a discovery hub (metadata-first)
What it is
Devpost is a well-known hub where hackathons are listed and hosted. It’s useful as an external “opportunity discovery” source.
​

Why it fits Module 4 Week 1
You can start without scraping deep pages: store only metadata + links (title, organizer, dates if visible, tags, URL), then rank based on student profile.
​

This aligns with your rule: external data is for opportunities; StudentHub curates/ranks it, not necessarily hosts it.
​

What you store (minimal safe schema)
Create opportunities_hackathons:

source: "devpost"

event_name, event_url, theme_tags (AI, Web3, HealthTech, etc.)

start_date, end_date (if available), status (open/closed)

eligibility (student/any, if visible)

scraped_at

Practical note
Devpost doesn’t present itself as a simple public API in the same way as typical platforms; treat Devpost as a link directory + metadata in Week 1 and only automate more later if needed.
​

3) Trending industry insights: Google News RSS (keyword/location feeds)
What it is
Google News provides RSS feeds that you can query by topic, location, or custom search query (keywords, site filters, time windows). This is lightweight compared to scraping full news pages.
​

Why it fits Module 4 Week 1
You can build “industry insights” and “trending content” recommendations using RSS entries (title, link, publish time) rather than copying article content.
​

It supports keyword-based feeds like “intitle:AI when:1h” and location feeds, which is perfect for personalizing by student interests (AI/ML, backend, etc.).
​

What you store (content feed schema)
Create opportunities_content:

source: "google_news_rss"
​

title, url, publisher (often in RSS item), published_at
​

topic: e.g., "AI", "Data Science", "Hiring" (your internal tag)

query_used: store the RSS query string for traceability
​

language/country: based on feed parameters (hl/gl/ceid)
​

Key limits/behavior to design around
Google News RSS is capped (e.g., up to ~100 items per feed call), so design ingestion to run multiple targeted feeds rather than one huge feed.
​

Week 1 deliverable (for Module 4) — what “done” should look like
By end of Week 1 you should have:

A clear Source Registry document listing which sources you use for:

internships/jobs (Apify Internshala actor)
​

hackathons (Devpost metadata links)
​

content/news (Google News RSS queries)
​

A Unified Opportunity Schema (3 collections or 1 collection with type) with normalized fields.

An Ingestion schedule decision: e.g., jobs daily, hackathons daily/weekly, news every 3–6 hours (RSS is light).
​

A “policy” decision: store only metadata + links for news/articles to avoid copying full copyrighted content.