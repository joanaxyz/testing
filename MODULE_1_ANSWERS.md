# GIT it! Module 1 Answer Key

Exact commands for every authored Module 1 variant. Match the variant label or scenario shown in the game, then enter its commands in order.

> Commands are evaluated by the game simulator. Do not enter extra commands unless the matching row lists them.

## 1. Initializing Repositories

### Easy

| Variant | Command sequence |
|---|---|
| Initialize the current folder | `git init` |
| Initialize with trunk as the first branch | `git init --initial-branch=trunk` |
| Initialize invoice-tracker | `git init invoice-tracker` |

### Medium

| Variant | Command sequence |
|---|---|
| Initialize oss-contrib | `git init oss-contrib` |
| Initialize docs-site | `git init docs-site` |
| Initialize api-playground with trunk | `git init -b trunk api-playground` |
| Initialize research-log quietly | `git init --quiet --initial-branch=main research-log` |

### Hard

| Variant | Command sequence |
|---|---|
| Initialize ci-configs | `git init ci-configs` |
| Initialize research-log subfolder only | `git init -q -b main research-log` |
| Initialize ui-kit with trunk, quietly | `git init --quiet --initial-branch=trunk ui-kit` |
| Safely reinitialize the current repository | `git init --quiet` |

## 2. Cloning Remote Repositories

### Easy

| Variant | Command sequence |
|---|---|
| Clone docs-portal | `git clone https://example.test/training/docs-portal.git` |
| Clone api-lab into api-workshop | `git clone https://example.test/training/api-lab.git api-workshop` |
| Clone profile-site at the starter branch | `git clone -b starter https://example.test/training/profile-site.git` |
| Clone oss-toolkit via SSH | `git clone git@github.com:open-dev/oss-toolkit.git` |
| Clone audit-logs into audit-logs-local | `git clone https://git.corp.example/it/audit-logs.git audit-logs-local` |

### Medium

| Variant | Command sequence |
|---|---|
| Clone backend-api at feature/auth | `git clone -b feature/auth https://github.com/acme-startup/backend-api.git` |
| Clone analytics-lab via SSH into analytics-worktree | `git clone git@example.test:training/analytics-lab.git analytics-worktree` |
| Clone cli-tool at starter into cli-starter-lab | `git clone --branch starter https://example.test/tools/cli-tool.git cli-starter-lab` |
| Shallow clone css-kit | `git clone --depth 1 https://example.test/frontend/css-kit.git` |

### Hard

| Variant | Command sequence |
|---|---|
| Shallow SSH clone of oss-toolkit into oss-review | `git clone --depth 1 git@github.com:open-dev/oss-toolkit.git oss-review` |
| Shallow clone mobile-ui at starter into mobile-ui-lab | `git clone --depth 1 -b starter https://example.test/frontend/mobile-ui.git mobile-ui-lab` |
| Shallow clone lab-notebook at review into notebook-review | `git clone --depth 1 --branch review https://example.test/docs/lab-notebook.git notebook-review` |
| Clone research-log via SSH into research-log-lab | `git clone git@example.test:docs/research-log.git research-log-lab` |

## 3. Staging and Committing

### Easy

| Variant | Command sequence |
|---|---|
| Initial commit for library-system | `git add .` &rarr; `git commit -m "Initial commit"` |
| Commit the auth module directory | `git add src/auth/` &rarr; `git commit -m "Add auth module"` |
| Commit form validation update | `git add src/form.js` &rarr; `git commit -m "Update form validation"` |
| Commit README clarification | `git add README.md` &rarr; `git commit --message "Clarify setup steps"` |
| Commit navbar spacing fix | `git add -A` &rarr; `git commit -m "Adjust navbar spacing"` |

### Medium

| Variant | Command sequence |
|---|---|
| Commit Docker configuration | `git add Dockerfile .env.example` &rarr; `git commit -m "Add Docker configuration"` |
| Commit profile card layout | `git add --all` &rarr; `git commit -m "Update profile card layout"` |
| Commit search results view | `git add src/search.js templates/search.html` &rarr; `git commit --message "Refine search results view"` |
| Commit export flow update | `git add src/export.py docs/export.md` &rarr; `git commit -m "Document export flow update"` |

### Hard

| Variant | Command sequence |
|---|---|
| Commit handler fix, leave experimental file out | `git add api/handler.py` &rarr; `git commit -m "Fix request handler null check"` |
| Commit parser and tests, leave debug/scratch files out | `git add src/parser.py tests/test_parser.py` &rarr; `git commit -m "Add parser module with unit tests"` |
| Commit profile card change, leave notes out | `git add src/profile-card.js` &rarr; `git commit -m "Update profile card behavior"` |
| Commit export fix, leave scratch output out | `git add src/export.py` &rarr; `git commit -m "Fix export validation"` |
| Commit search ranking display, leave notes out | `git add src/search.js templates/search.html` &rarr; `git commit -m "Refine search ranking display"` |

## 4. Partial Staging

### Easy

| Variant | Command sequence |
|---|---|
| Stage the billing fix hunk only | `git add -p src/billing.py` &rarr; `git commit -m "Fix billing calculation rounding error"` |
| Stage the routes handler hunk only | `git add -p src/routes.py` &rarr; `git commit -m "Update API route handlers"` |
| Stage the auth validation hunk only | `git add -p src/auth.py` &rarr; `git commit -m "Isolate auth validation"` |
| Stage the search ranking hunk only | `git add -p src/search.py` &rarr; `git commit -m "Isolate search ranking"` |
| Stage the export formatting hunk only | `git add -p src/export.py` &rarr; `git commit -m "Isolate export formatting"` |

### Medium

| Variant | Command sequence |
|---|---|
| Stage only the parser bug fix hunk | `git add -p src/parser.py` &rarr; `git commit -m "Fix parser bug and refactor token handling"` |
| Stage only the profile validation hunk | `git add -p src/profile.py` &rarr; `git commit -m "Commit profile validation only"` |
| Stage only the payment rounding hunk | `git add -p src/payment.py` &rarr; `git commit -m "Commit payment rounding fix"` |
| Stage only the dashboard filter hunk | `git add -p src/dashboard.js` &rarr; `git commit -m "Commit dashboard filter change"` |

### Hard

| Variant | Command sequence |
|---|---|
| Stage only the network Terraform hunk | `git add -p terraform/main.tf` &rarr; `git commit -m "Update network Terraform configuration"` |
| Stage validation hunks across auth code and tests | `git add -p src/auth.py` &rarr; `git add -p tests/test_auth.py` &rarr; `git commit -m "Commit auth validation path"` |
| Stage ranking hunks across search code and tests | `git add -p src/search.py` &rarr; `git add -p tests/test_search.py` &rarr; `git commit -m "Commit search ranking path"` |
| Stage formatting hunks across export code and tests | `git add -p src/export.py` &rarr; `git add -p tests/test_export.py` &rarr; `git commit -m "Commit export formatting path"` |

## 5. Amending Commits

### Easy

| Variant | Command sequence |
|---|---|
| Fix a typo in the last commit message | `git commit --amend -m "Initial commit"` |
| Add a forgotten file to the last commit | `git add src/logout.py` &rarr; `git commit --amend -m "Add auth module"` |
| Clarify a vague commit message | `git commit --amend -m "Clarify login copy"` |
| Clarify the README commit message | `git commit --amend -m "Clarify setup requirements"` |
| Clarify the navbar commit message | `git commit --amend -m "Adjust navbar spacing"` |

### Medium

| Variant | Command sequence |
|---|---|
| Add changelog and correct the commit message | `git add docs/CHANGELOG.md` &rarr; `git commit --amend -m "Add parser feature and update changelog"` |
| Add missing profile CSS to the last commit | `git add styles/profile-card.css` &rarr; `git commit --amend -m "Update profile card layout"` |
| Add missing export docs to the last commit | `git add docs/export.md` &rarr; `git commit --amend -m "Document export flow update"` |
| Add missing search template to the last commit | `git add templates/search.html` &rarr; `git commit --amend -m "Refine search results view"` |

### Hard

| Variant | Command sequence |
|---|---|
| Correct a verbose passive-voice commit message | `git commit --amend -m "Update Terraform staging environment configuration"` |
| Add missing CSS and correct the commit message | `git add styles/profile-layout.css` &rarr; `git commit --amend -m "Polish profile card layout"` |
| Add missing test and correct the commit message | `git add tests/test_auth.py` &rarr; `git commit --amend -m "Add auth validation coverage"` |
| Add missing docs and correct the commit message | `git add docs/export.md` &rarr; `git commit --amend -m "Document export validation behavior"` |

## 6. Unstaging and Discarding Changes

### Easy

| Variant | Command sequence |
|---|---|
| Unstage notes.txt without discarding it | `git restore --staged notes.txt` |
| Discard experimental config.py changes | `git restore config.py` |
| Unstage src/app.py without discarding it | `git restore --staged src/app.py` |
| Unstage docs/guide.md without discarding it | `git restore --staged docs/guide.md` |
| Unstage styles/site.css without discarding it | `git restore --staged styles/site.css` |

### Medium

| Variant | Command sequence |
|---|---|
| Unstage experimental.py, discard README.md changes | `git restore --staged experimental.py` &rarr; `git restore README.md` |
| Preserve app.py, discard debug.log | `git restore --staged src/app.py` &rarr; `git restore debug.log` |
| Preserve guide.md, discard scratch.txt | `git restore --staged docs/guide.md` &rarr; `git restore tmp/scratch.txt` |
| Preserve source CSS, discard generated dist CSS | `git restore --staged styles/site.css` &rarr; `git restore dist/site.css` |

### Hard

| Variant | Command sequence |
|---|---|
| Unstage two files, discard experimental.py | `git restore --staged debug.log scratch/notes.txt` &rarr; `git restore api/experimental.py` |
| Unstage two files, discard debug log | `git restore --staged src/profile-card.js notes/profile-ideas.md` &rarr; `git restore debug/profile.log` |
| Unstage two files, discard generated output | `git restore --staged src/export.py notes/export-plan.md` &rarr; `git restore tmp/export-output.txt` |
| Unstage two files, discard debug search log | `git restore --staged src/search.js notes/search.md` &rarr; `git restore debug/search.log` |
