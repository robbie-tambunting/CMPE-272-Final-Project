# AI Notes

Documentation of AI-assisted interactions for this project. Each prompt is logged automatically via a Claude Code `UserPromptSubmit` hook (`.claude/hooks/log-prompt.py`).

## How It Works

- **Hook:** `.claude/hooks/log-prompt.py` runs on every user prompt submission
- **Settings:** `.claude/settings.json` registers the hook under `UserPromptSubmit`
- **Log format:** Each entry records the timestamp, model, and full prompt text

## Automation Implementation

### Hook: `UserPromptSubmit`

Configured in [.claude/settings.json](.claude/settings.json) under the `UserPromptSubmit` event. This hook fires automatically every time a prompt is submitted to Claude Code — no manual action required.

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/log-prompt.py",
            "timeout": 10,
            "async": true
          }
        ]
      }
    ]
  }
}
```

The hook runs **async** so it never blocks the AI response.

### Script: `.claude/hooks/log-prompt.py`

Reads the hook's stdin JSON payload (which contains the `prompt` field), then appends a formatted entry to `AI-NOTES.md`. The model name is read from the `CLAUDE_MODEL` environment variable (falls back to `claude-sonnet-4-6`).

**Entry format:**

```
### YYYY-MM-DD HH:MM — <model>

<prompt text>
```

### Skill: `/update-config`

Used to configure the hook in [.claude/settings.json](.claude/settings.json). This is a built-in Claude Code skill invoked with `/update-config` that knows how to safely read, merge, and write settings files without clobbering existing config. It was used to register the `UserPromptSubmit` event and validate the hook JSON schema before writing.

## Personal Notes

- Plans were cross-referenced with Google Gemini Pro 3.1 for other implementation ideas, tracking regressions, and determining edge cases

-  At 5:20 PM (17:20), Claude Code temporarily went down due to a server error. As a result, we switched to using Cursor, utilizing the Gemini 3.1 Pro and GPT 5.5 models instead.

- Claude came back online at 5:40 PM PST (17:40).

- GPT 5.5 Was used against Claude's Plan to run a check against it.

## Human Decided Plan Improvements
1. Plan did not specify exact implementation of crypto hash function. I told it to use SHA-256 specifically
2. The pytest unit tests did not have guidance on what size files to use. Given the specs, the agent could run with 4GB file transfers for each unit test. For these tests, instead we will be using smaller file sizes. The main 4GB transfer is reserved for demo purposes
3. Reviewed the test cases for the SHA-256 hash helper function (`tests/test_hashing.py`) and verified the tests are sufficient for checking the hash algorithm function

---

## Prompts

### 2026-05-14 17:03 — claude-sonnet-4-6

create a claude skills folder or optimization pattern in this repo to write to AI-NOTES.md with each prompt. The end goal of this .md file is to document how I interacted with AI. add a prompts section with each major prompt I use as reference. This will be at the end. Include this prompt as well and write the model used

### 2026-05-14 17:04 — claude-sonnet-4-6

Your Task
Design and implement two distinct ways for the sender to deliver the 4 GB file to the receiver such that CIAA holds end-to-end. The two approaches must differ in a meaningful architectural way — not just by tweaking a cipher suite. Examples of meaningful differences include:
Transport-layer security vs. application-layer envelope (e.g. mutually-authenticated TLS streaming vs. an offline-encrypted file pushed over plain TCP/HTTP).
Online interactive key exchange (ECDHE) vs. pre-distributed long-lived keys (PSK or recipient public key).
Single streamed channel vs. chunked-and-signed manifest with resumable parts.
Direct sender → receiver vs. sender → broker/storage → receiver (the broker must not be trusted with plaintext).
For each approach you must produce: a one-page design, a working implementation that successfully transfers a 4 GB test file (a generated 4 GB file of random or zero bytes is fine), and a short threat analysis showing how each CIAA property is achieved.

### 2026-05-14 17:12 — claude-sonnet-4-6

<ide_opened_file>The user opened the file /Users/tambunting/coding-projects/school/cmpe-272/CMPE-272-Final-Project/AI-NOTES.md in the IDE. This may or may not be related to the current task.</ide_opened_file>
generate a a 4 GB file of random or zero bytes within the codebase

### 2026-05-14 17:13 — claude-sonnet-4-6

we will use this to file as a payload between receiver and sender in our project

### 2026-05-14 17:15 — claude-sonnet-4-6

/update-config write a section in AI_NOTES.md outlining the hook and skill we are using to automatically record prompts and note implementation in the AI_NOTES.md

### 2026-05-14 17:17 — claude-sonnet-4-6

update the plan to have a DESIGN.md file per approach (DESIGN1.MD and DESIGN2.md)

### 2026-05-14 17:18 — claude-sonnet-4-6

continue planning

### 2026-05-14 17:19 — claude-sonnet-4-6

testing, is claude code down?

### 2026-05-14 17:20 — claude-sonnet-4-6

testing is claude down right now

### 2026-05-14 17:21 — claude-sonnet-4-6

testing is claude down right now

### 2026-05-14 17:39 — claude-sonnet-4-6

<ide_opened_file>The user opened the file /Users/tambunting/coding-projects/school/cmpe-272/CMPE-272-Final-Project/AI-NOTES.md in the IDE. This may or may not be related to the current task.</ide_opened_file>
testing

### 2026-05-14 17:40 — claude-sonnet-4-6

/update-config add a note in the Human notes section stating Claude came back online 5:40PM PST

### 2026-05-14 17:42 — claude-sonnet-4-6

<ide_opened_file>The user opened the file /Users/tambunting/coding-projects/school/cmpe-272/CMPE-272-Final-Project/AI-NOTES.md in the IDE. This may or may not be related to the current task.</ide_opened_file>
Create a plan for the following. We already have a GPT 5.5 generate plan for this file, but we need a few additions. 

add the following additions to the plan in the right order

1. Create a SHA 256 helper function for use in both approaches
2. ensure approach A is built first, then approach B
3. Add a deferred frontend phase (likely next.js for ease and popularity)

### 2026-05-14 17:49 — claude-sonnet-4-6

implement just phase 0, the shared crypto helper

### 2026-05-14 17:50 — claude-sonnet-4-6

<ide_opened_file>The user opened the file /Users/tambunting/coding-projects/school/cmpe-272/CMPE-272-Final-Project/tests/test_hashing.py in the IDE. This may or may not be related to the current task.</ide_opened_file>
state what each of the test cases in test_hashing.py does

### 2026-05-14 17:56 — claude-sonnet-4-6

/update-config add note stating we reviewed test cases for hash function and verified the tests are sufficient for checking the hash algorithm function

### 2026-05-14 17:57 — claude-sonnet-4-6

great, implement approach a (phase 1)

### 2026-05-14 18:15 — claude-sonnet-4-6

implement the next phase (approach B)

### 2026-05-14 18:26 — claude-sonnet-4-6

<ide_opened_file>The user opened the file /Users/tambunting/coding-projects/school/cmpe-272/CMPE-272-Final-Project/DESIGN1.md in the IDE. This may or may not be related to the current task.</ide_opened_file>
great, design a simple Next.js frontend for testing each approach

### 2026-05-14 18:29 — claude-sonnet-4-6

do not add a new design3.md, go off the plan and implement the deferred frontend plan
