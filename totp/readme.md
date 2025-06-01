# totp/

This directory contains Python scripts related to generating Time-based One-Time Passwords (TOTP), typically used for two-factor authentication.

## Contents:

*   `lacis_code_telegram_bot.py`: A script for a simple Telegram bot that generates and sends a TOTP code based on a hardcoded secret URI when a specific command is received. Requires the `python-telegram-bot` library and a Bot API key.
*   `main.py`: A standalone script that demonstrates the TOTP code generation process from a hardcoded secret URI, including detailed debug output for each calculation step.

## Dependencies:

*   `lacis_code_telegram_bot.py` depends on: `python-telegram-bot`, `base64`, `hmac`, `time`, `struct`, `urllib.parse`.
*   `main.py` depends on: `base64`, `hmac`, `time`, `struct`, `urllib.parse`.

Install necessary libraries:
```bash
pip install python-telegram-bot
```

## Usage:

*   **For `main.py`:**
    1.  Edit the `main.py` file and replace the placeholder `totp_uri` with your actual `otpauth://` secret URI.
    2.  Run the script:
        ```bash
        python totp/main.py
        ```
    It will print the parsed parameters, detailed calculation steps, and the final TOTP code.

*   **For `lacis_code_telegram_bot.py`:**
    1.  Obtain a Telegram Bot API Key from BotFather.
    2.  Edit `lacis_code_telegram_bot.py`:
        *   Replace `"YOUR_BOT_API_KEY"` with your actual API key.
        *   Replace `r"TOTP_URI"` with your actual `otpauth://` secret URI.
    3.  Run the script:
        ```bash
        python totp/lacis_code_telegram_bot.py
        ```
    The bot will start polling. Send the `/code` command to the bot in Telegram to receive the TOTP code.
