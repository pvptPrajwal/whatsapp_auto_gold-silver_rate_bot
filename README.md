# 📈 WhatsApp Auto Gold & Silver Rate Bot

![Banner Image](link_to_your_banner_image_here)

An automated, Flask-based application that scrapes real-time Gold and Silver bullion rates and broadcasts formatted updates to specific WhatsApp groups on a customized daily schedule.

---

## 🚀 Overview

This project automates the tedious task of tracking live commodity rates and manually sending them to business or client WhatsApp groups. It features a responsive web dashboard (accessible via PC or Mobile on the same network) to control settings, manage schedules, and monitor logs in real-time.

Instead of relying on expensive or restrictive official WhatsApp APIs, this bot uses a robust, custom Selenium WebDriver implementation to securely link and manage a persistent WhatsApp Web session in the background.

## ✨ Key Features

*   **Live Web Scraping:** Dynamically fetches real-time Gold and Silver rates directly from target bullion websites using targeted Selenium extraction and Regex.
*   **Automated Scheduling:** Set specific times (Morning, Afternoon, Evening) for the bot to automatically fetch rates and broadcast messages.
*   **Flask Web Dashboard:** A clean, intuitive UI to configure price margins, edit message templates, manage WhatsApp groups, and start/stop the bot.
*   **Mobile Remote Access:** Control the bot from your phone on the same Wi-Fi network, secured by an auto-generated local PIN.
*   **Persistent WhatsApp Session:** Log in once via QR code. The session is saved locally, and future broadcasts happen silently in an off-screen background browser.
*   **Custom Retry Logic:** Built-in error handling and retries ensure messages are delivered even if network delays occur.
*   **SQLite Database:** Keeps a persistent history of sent messages, success/failure statuses, and executed jobs.

---

## 📸 Screenshots

### Web Dashboard
![Web Dashboard Screenshot](<img width="1919" height="1075" alt="image" src="https://github.com/user-attachments/assets/75950ff6-d4da-4f06-b9c0-9be9739c17ad" />
)

### Mobile Remote View
![Mobile Dashboard Screenshot](link_to_your_mobile_view_image_here)

### Automated WhatsApp Broadcast
![WhatsApp Message Screenshot](link_to_your_whatsapp_message_image_here)

---

## 🛠️ Tech Stack

*   **Backend:** Python 3, Flask
*   **Automation & Scraping:** Selenium, WebDriver Manager, Regex
*   **Task Scheduling:** `schedule`, Python Threading
*   **System Operations:** `psutil`
*   **Database:** SQLite

---

## ⚙️ Prerequisites

Before you begin, ensure you have the following installed on your machine:
*   [Python 3.8+](https://www.python.org/downloads/)
*   Google Chrome browser

---

## 📥 Installation & Setup

**1. Clone the repository:**
```bash
git clone [https://github.com/pvptPrajwal/whatsapp_auto_gold-silver_rate_bot.git](https://github.com/pvptPrajwal/whatsapp_auto_gold-silver_rate_bot.git)
cd whatsapp_auto_gold-silver_rate_bot
