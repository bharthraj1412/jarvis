# skills/builtin_extras.py
"""
Extra built-in skills for JARVIS MK37.
Importing this module registers 5 additional skills:
  - github_scan      — Scan and summarize a GitHub repository
  - screenshot_fix   — Screenshot screen, find errors, auto-fix code
  - docker_deploy    — Build and deploy Docker containers
  - project_scaffold — Generate a full project from a description
  - site_monitor     — Monitor website uptime and alert on downtime
"""
from __future__ import annotations
from skills.loader import SkillDef, register_builtin_skill


# ── /github-scan ──────────────────────────────────────────────────────────────

_GITHUB_SCAN_PROMPT = """\
You are an expert open-source analyst. Scan a GitHub repository and produce a
comprehensive summary.

## Task
Analyze: $ARGUMENTS

## Steps
1. If a full URL is given (e.g. https://github.com/user/repo), fetch the page
   directly with fetch_page. If only a repo name is given (e.g. "facebook/react"),
   construct the URL: https://github.com/<owner>/<repo>.
2. Extract from the page:
   - **README summary** (first 500 words)
   - **Tech stack** (languages, frameworks detected from README and repo topics)
   - **Stars / Forks / License**
   - **Last commit date** (if visible)
3. Fetch the issues page: https://github.com/<owner>/<repo>/issues
   - List the top 5 open issues (title + labels)
4. Produce a structured report:
   ```
   ## Repository: <name>
   **URL:** <url>
   **Stars:** <n>  |  **Forks:** <n>  |  **License:** <license>

   ### README Summary
   <summary>

   ### Tech Stack
   - <lang1>, <lang2>, <framework>

   ### Top 5 Open Issues
   1. <title> [labels]
   2. ...
   ```

## Rules
- If the repo is private or doesn't exist, report it clearly.
- Never fabricate data. Only report what you can fetch.
- Use fetch_page for rendered content, fetch_raw for API endpoints.
"""

_SCREENSHOT_FIX_PROMPT = """\
You are an expert debugger with vision capabilities. Your job is to screenshot
the user's screen, identify any errors visible, and auto-fix the code.

## Task
$ARGUMENTS

## Steps
1. Take a screenshot of the current screen using take_screenshot.
2. Analyze the screenshot:
   - Look for error messages, stack traces, terminal output, or red highlights.
   - Identify the file and line number if visible.
3. If a file path is mentioned in $ARGUMENTS or visible on screen:
   - Read the file with file_read.
   - Identify the bug based on the error message.
   - Write the corrected code with file_write.
4. If no file path is available:
   - Describe the error in detail.
   - Provide the fix as a code block.
5. After fixing, take another screenshot to confirm the fix if possible.

## Rules
- Always screenshot FIRST before doing anything else.
- Be precise about what error you see — quote error messages exactly.
- Make minimal, surgical fixes. Don't rewrite entire files.
- If you can't identify the error from the screenshot, say so clearly.
"""

_DOCKER_DEPLOY_PROMPT = """\
You are a DevOps engineer. Build and deploy a Docker container.

## Task
$ARGUMENTS

## Steps
1. Check if Docker is installed: `docker --version`
   - If not installed, tell the user and stop.
2. Look for a Dockerfile in the current directory or the path specified.
   - If no Dockerfile exists, create one based on the project type:
     - Python: `python:3.12-slim` base, copy requirements, install, copy app
     - Node.js: `node:20-alpine` base, copy package.json, npm install, copy app
     - Go: multi-stage build with `golang:1.22` builder and `alpine` runtime
3. Build the image:
   ```
   docker build -t <image_name> .
   ```
4. Run the container:
   ```
   docker run -d --name <container_name> -p <port>:<port> <image_name>
   ```
5. Verify the container is running: `docker ps`
6. Report the container ID, ports, and status.

## Rules
- Use descriptive image/container names based on the project.
- Default to port 8080 if no port is specified.
- If the build fails, read the error and fix the Dockerfile.
- Always clean up failed containers before retrying.
"""

_PROJECT_SCAFFOLD_PROMPT = """\
You are a senior software architect. Generate a complete project scaffold from
a one-line description.

## Task
Create: $ARGUMENTS

## Steps
1. Analyze the description to determine:
   - Language / framework (Python/Flask, Node/Express, React, Go, etc.)
   - Project type (API, web app, CLI tool, library, etc.)
   - Key features mentioned
2. Create the project directory structure. Standard layouts:
   **Python API:**
   ```
   project_name/
   ├── app/
   │   ├── __init__.py
   │   ├── main.py
   │   ├── routes/
   │   ├── models/
   │   └── utils/
   ├── tests/
   ├── requirements.txt
   ├── Dockerfile
   ├── .env.template
   └── README.md
   ```
   **Node.js:**
   ```
   project_name/
   ├── src/
   │   ├── index.js
   │   ├── routes/
   │   └── middleware/
   ├── tests/
   ├── package.json
   ├── .env.template
   └── README.md
   ```
3. Write actual working code for each file — not placeholders.
4. Include:
   - A working entry point that runs without errors
   - Basic error handling
   - A README with setup instructions
   - A .gitignore appropriate for the language
5. Report what was created and how to run it.

## Rules
- Every file must contain real, functional code.
- Use modern best practices for each language.
- Include at least one example route/endpoint/command.
- The project must be runnable immediately after scaffold.
"""

_SITE_MONITOR_PROMPT = """\
You are a site reliability engineer. Monitor a website's availability.

## Task
Monitor: $ARGUMENTS

## Steps
1. Extract the URL from the arguments. If no protocol, prepend https://.
2. Check the site using fetch_raw:
   - Record the HTTP status code.
   - Measure response time (note start/end).
   - Check if the response body is non-empty.
3. Perform 3 checks with a 2-second delay between each (use run_code to sleep).
4. Produce a status report:
   ```
   ## Site Monitor Report: <url>

   | Check | Status | Response Time | Result |
   |-------|--------|--------------|--------|
   | 1     | 200    | 0.34s        | UP     |
   | 2     | 200    | 0.28s        | UP     |
   | 3     | 200    | 0.31s        | UP     |

   **Overall:** HEALTHY / DEGRADED / DOWN
   **Average Response Time:** 0.31s
   ```
5. If any check fails:
   - Report the error (timeout, DNS failure, 5xx, etc.)
   - Mark as DEGRADED (1 failure) or DOWN (all failures)

## Rules
- Use https:// by default unless the user specifies http://.
- A response time > 5s counts as degraded.
- A non-2xx status counts as a failure.
- Never make more than 5 requests to avoid abuse.
"""


def _register_extra_builtins() -> None:
    """Register all extra built-in skills."""

    register_builtin_skill(SkillDef(
        name="github_scan",
        description="Scan and summarize a GitHub repository: README, tech stack, issues",
        triggers=["/github-scan", "/gh-scan", "/repo-scan"],
        tools=["web_search", "fetch_page", "fetch_raw"],
        prompt=_GITHUB_SCAN_PROMPT,
        file_path="<builtin>",
        when_to_use="Use when the user wants to analyze or summarize a GitHub repository.",
        argument_hint="<github URL or owner/repo>",
        arguments=[],
        user_invocable=True,
        context="inline",
        source="builtin",
    ))

    register_builtin_skill(SkillDef(
        name="screenshot_fix",
        description="Screenshot the screen, find visible errors, and auto-fix the code",
        triggers=["/screenshot-fix", "/screen-fix", "/fix-screen"],
        tools=["take_screenshot", "screen_find", "run_code", "file_read", "file_write"],
        prompt=_SCREENSHOT_FIX_PROMPT,
        file_path="<builtin>",
        when_to_use="Use when the user wants to fix an error visible on their screen.",
        argument_hint="[optional file path or description]",
        arguments=[],
        user_invocable=True,
        context="inline",
        source="builtin",
    ))

    register_builtin_skill(SkillDef(
        name="docker_deploy",
        description="Build and deploy a Docker container from a Dockerfile",
        triggers=["/docker-deploy", "/docker", "/deploy"],
        tools=["run_code", "file_read", "file_write"],
        prompt=_DOCKER_DEPLOY_PROMPT,
        file_path="<builtin>",
        when_to_use="Use when the user wants to build or deploy a Docker container.",
        argument_hint="[project path or description]",
        arguments=[],
        user_invocable=True,
        context="inline",
        source="builtin",
    ))

    register_builtin_skill(SkillDef(
        name="project_scaffold",
        description="Generate a complete project scaffold from a one-line description",
        triggers=["/scaffold", "/create-project", "/new-project"],
        tools=["run_code", "file_write", "file_read"],
        prompt=_PROJECT_SCAFFOLD_PROMPT,
        file_path="<builtin>",
        when_to_use="Use when the user wants to create a new project from scratch.",
        argument_hint="<project description>",
        arguments=[],
        user_invocable=True,
        context="inline",
        source="builtin",
    ))

    register_builtin_skill(SkillDef(
        name="site_monitor",
        description="Monitor a website's uptime and report status with response times",
        triggers=["/monitor", "/site-monitor", "/uptime"],
        tools=["web_search", "fetch_raw", "run_code"],
        prompt=_SITE_MONITOR_PROMPT,
        file_path="<builtin>",
        when_to_use="Use when the user wants to check if a website is up or monitor its availability.",
        argument_hint="<URL to monitor>",
        arguments=[],
        user_invocable=True,
        context="inline",
        source="builtin",
    ))


_register_extra_builtins()
