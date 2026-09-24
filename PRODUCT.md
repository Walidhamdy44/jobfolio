# Personal job application agent

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Accepted implementation plan: React and TypeScript, Python/FastAPI, SQLite, Playwright, DOCX and PDF generation. Runs locally on Windows. 100% free operation using public job feeds (Remotive, Jobicy, Arbeitnow) and free AI models via OpenRouter or OpenCode. Optional paid providers (OpenAI, Brave Search) supported.

## Users

Walid Hamdy, a frontend engineer, reviewing relevant jobs and accurate tailored applications on his own computer.

## Product Purpose

Discover relevant jobs, tailor a CV using source evidence, explain requirement coverage, and submit only the exact package the user approves.

## Operating Context

100% free discovery via public tech feeds (Remotive, Jobicy, Arbeitnow) and employer job links; Greenhouse and Lever application adapters. The user reviews each application. Target 95% coverage, but queue the best truthful CV even below that target.

## Capabilities and Constraints

Original CV is immutable. Preserve dates, employers, titles, qualifications, achievements. No invented facts or guaranteed ATS score. 100% free out-of-the-box job search requires no API keys; free AI models supported via OpenRouter ($0 key) and OpenCode; manual job entry and local CV tailoring work completely offline without any API keys. Unknown answers, login challenges, unsupported forms, and uncertain submissions require handoff. No recruiter messages.

## Evidence on Hand

Walid_Hamdy_CV_Frontend_Software_Engineer.pdf: two-page master CV supplied by the user. There are no existing applications, saved jobs, or success statistics. Search geography, work authorization, and salary preferences are not confirmed.

## Product Principles

- Show evidence beside coverage.
- Keep approval bound to the exact package.
- Distinguish actual, estimated, and unknown states.
- Preserve local data and prevent duplicate submissions.
