# 📈 WhatsApp Auto Gold & Silver Rate Bot



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
<img width="1919" height="1000" alt="image" src="https://github.com/user-attachments/assets/d7551866-061d-47b0-8e0e-bada77551f59" />


### Mobile Remote View
<img width="1206" height="2622" alt="WhatsApp Image 2026-08-19 at 1 22 25 PM" src="https://github.com/user-attachments/assets/47330401-c487-4a3c-a5fb-a60ac5bccd1e" />


<img width="1206" height="2622" alt="WhatsApp Image 2026-08-19 at 1 22 25 PM (1)" src="https://github.com/user-attachments/assets/f28127af-4b8a-4d3b-b715-6d85447c95cd" />


### Automated WhatsApp Broadcast

<img width="1206" height="2622" alt="WhatsApp Image 2026-08-19 at 1 22 25 PM (2)" src="https://github.com/user-attachments/assets/37d16a88-6d01-43d6-b0eb-b4f1e2fc928b" />


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
