# tampermonkey_scripts/

This directory contains JavaScript userscripts designed to be used with browser extensions like Tampermonkey, Violentmonkey, or Greasemonkey. Each script modifies the behavior of a specific website.

## Contents:

*   `tampermonkey_chatgpt_temporary.js`: A userscript that automatically appends the `temporary-chat=true` parameter to ChatGPT URLs to force temporary conversations.
*   `tampermonkey_regenerate_deepseek.js`: A userscript that attempts to automatically click the "Regenerate" button on DeepSeek Chat when a specific server busy error message is detected.

## Usage:

To use these scripts, you need a userscript manager browser extension (e.g., Tampermonkey).

1.  Install the extension.
2.  Open the extension's dashboard or editor.
3.  Create a new script.
4.  Copy the contents of the desired `.js` file into the editor.
5.  Save the script.

The script will then automatically activate when you visit the website(s) specified in its `@match` header directive.

These scripts are provided as-is and may require adjustments if the target websites change their structure or behavior.
