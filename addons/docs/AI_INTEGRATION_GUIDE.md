# AI Integration Guide (Add-on, No Code Risk)

This chatbot feature is implemented as a sidecar add-on using only new files under the addons folder.
No existing working project files were modified.

## What was integrated

1. Life Skill chatbot API sidecar on port 8010.
2. Single Course chatbot Streamlit sidecar on port 8511.
3. Dual Course chatbot Streamlit sidecar on port 8512.

## Faculty demo statement

"We integrated AI chatbot support as an additional module. It can answer allocation queries such as section-wise and course-wise student lists. If allocation is not available, it clearly responds: please run allocation first, and provides a short guideline checklist."

## Example prompts

1. Give me the list of the students in the ML course section 2 with their previous dept elective.
2. Show unallocated students and reasons.
3. Give allocation summary.
4. Tell me the steps to run allocation.

## Fallback behavior

If result data is not loaded, chatbot returns:
- Message: Please run allocation first.
- Checklist: short module-specific run steps.

## How to run

Use gateway script:

```powershell
powershell -ExecutionPolicy Bypass -File addons/gateway/run_all_modules_with_chatbot.ps1
```

Or run each sidecar independently from its folder.
