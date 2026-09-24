# Post-import flow findings and fixes

Tested on 2026-09-24 using the imported Deloitte job `fd8f1de7861e436986a7c2406690fe27`. No application was submitted or approved during this review.

| Issue | What happened | Change / status |
|---|---|---|
| Brief LinkedIn import | The Deloitte job first contained a 53-character search summary. AI preparation failed because it had no real requirements. | **Fixed:** LinkedIn import retries the public posting fetch once. If an imported job is still unverified, CV preparation fetches the full description first and stops with a clear repair action if that fails. Import messages now distinguish a summary from a full posting. |
| Wrong coverage inputs | Local extraction counted company background and marketing paragraphs as required qualifications. | **Fixed:** Extraction now reads responsibilities and qualification sections, and excludes unrelated sections. Deloitte changed from 45 noisy requirements to 24 relevant ones, including 4 preferred criteria. |
| Misleading AI status | The saved OpenRouter key appears “connected,” but a synthetic provider request returned HTTP 401, `User not found`. | **Partly fixed:** the app now says a key is saved but not verified, and a 401 gives an action: replace the key in Connections or prepare locally. **User action remains:** replace the invalid key to use AI tailoring. |
| Wrong list status | An AI connection error made the Opportunities row say “Needs full description,” even after the full posting was fetched. | **Fixed:** description status uses posting verification; other failures say “Needs attention.” |
| Contradictory application copy | LinkedIn was described as manual-only beside a Co-Pilot button. | **Fixed:** the page explains LinkedIn Co-Pilot and the separate manual path. |
| Unverified automatic answers | The answer engine could guess salary and technology-specific years from location or static defaults. | **Fixed:** missing salary preferences and unsupported experience remain unanswered. Legal, consent, salary, years, and availability questions are not delegated to a generic AI fallback. The user must review those fields. |
| Unattended submission risk | Full Auto-Apply could attempt to submit with screening answers generated during browser execution. | **Contained:** unattended mode is blocked at the API and disabled in the UI. Co-Pilot remains available only after package review and approval; the final employer form requires user review. |
| Package binding | Auto-Apply accepted an omitted package hash. | **Fixed:** the request must include the current approved package hash. |

## Verified path

1. **Import:** Deloitte job saved; its initial description was brief.
2. **Description:** “Retry fetching description” retrieved the complete 7,446-character LinkedIn posting.
3. **Preparation:** Local CV preparation completed without sending CV data to an AI provider.
4. **Coverage:** Rebuilt from the corrected extractor. The current provisional score is **15.6%** across **24** criteria. This low score reflects substantial Node.js/AWS operations requirements that the current frontend CV does not clearly support; it is not an employer ATS score.
5. **Review:** CV review, coverage review, and package approval remain pending. The Application page blocks approval and Co-Pilot until these steps are completed.

## Remaining limitations

- The OpenRouter credential is invalid (401). AI tailoring will remain unavailable until the key is replaced in **Connections**. The app does not yet provide a dedicated connection-test button.
- LinkedIn may show an auth wall in the agent's separate persistent browser profile even when the posting opens in the user's normal Chrome tab. Co-Pilot should identify that state and hand off for login; a real Co-Pilot run was not started in this review.
- The user must personally verify the generated CV and coverage before approving them. This review did not mark either as accurate or submit an application.
- Full unattended employer submission needs a reviewed, immutable set of screening answers and stronger end-to-end employer-form verification before it can be re-enabled. The earlier [Auto-Apply QA report](/D:/WORK/agent-jobs/AUTO_APPLY_FLOW_QA_2026-09-05.md) contains the broader backlog.

## Validation

- Auto-Apply, workflow, and search suite: **58 passed** after the fixes and test updates.
- Frontend TypeScript/Vite production build: **passed**.
- Live app was restarted, the Deloitte local CV was rebuilt, and the Application page was checked after the final build.
