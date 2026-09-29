# Frontend verification

## Scope

Static product/documentation frontend added on top of the merged v0.2 upgrade.
No Python MCP implementation, credential configuration, or registered tool was changed.
Contributed by [SolutionsAsService](https://github.com/SolutionsAsService).

## Checks performed

- Generated catalog matches all **39** `@mcp.tool` registrations in `server.py`.
- **5** Node content tests pass (metadata, search, real tool examples, configuration JSON, local links/assets).
- **14** Chromium browser checks pass across desktop and mobile device emulation.
- Automated axe WCAG A/AA checks report **zero violations** in the tested initial desktop/mobile layouts.
- Tool filtering, expansion, details, no-match recovery, and domain links verified.
- Workflow switching, platform commands, clipboard success and denial fallback verified.
- Catalog-load failure and JavaScript-disabled explanatory content verified.
- Keyboard skip link and no horizontal overflow verified, including 320px width.
- Built output tested at `/dist/`, exercising project-subpath hosting rather than only `/`.
- No browser JavaScript errors or external service requests during tested initial page loads.
- Formatting check, dependency audit (zero reported vulnerabilities), and Git whitespace check pass.
- Production output contains only seven allowlisted static assets (approximately 88 KB on disk).

Full-page screenshots were captured from the built output and visually reviewed:
[desktop](frontend-desktop.png) · [mobile](frontend-mobile.png).

## Boundaries

Device emulation is not physical-device or cross-browser certification. Automated
accessibility scanning does not replace a full manual audit. The site makes no
live Autheo calls; example workflows are labeled, not fabricated response data.
No public hosting was provisioned or deployed during this work. The opt-in Pages
workflow requires repository Pages configuration and a manual run after merge.

Reproduction commands and deployment instructions are in
[the frontend guide](../frontend/README.md). CI runs the same frontend checks on PRs.
