# <img src="logo.png" width="48" align="center" alt="Money Mate Logo"> Money Mate 💸
An AI-powered Telegram bot landing page that enables lightning-fast expense tracking and ledger management directly from your chat.

## Overview
Money Mate revolutionizes personal finance tracking by eliminating the need for complex apps. Built entirely on Telegram, it acts as your personal AI accountant. Simply chat naturally—send text or voice notes—and Money Mate will parse the intent, categorize the transaction, and manage your ledgers in real-time.

This repository contains the sleek, highly interactive, and responsive frontend landing page for the Money Mate platform, featuring Apple-style Bento Grids, hyper-realistic iPhone mockups, and scroll-triggered animations with haptic feedback.

## Features ✨
- **Hyper-Realistic iPhone Mockup:** Fully interactive hardware buttons (Power, Volume HUD, Silent Switch dropdown) built purely with CSS and JS.
- **Statement Image (Aapka Hisaab):** Generates clean, branded, high-resolution mini-statement images right in Telegram chat using Playwright headless rendering with Indian currency formatting (`₹1,00,000`), breakdown cards (Total Kharcha, Udhaar Diya, Wapas Mila, Baaki), and active udhaar pending strip.
- **Scroll-triggered Haptic Feedback:** Uses the Web Vibration API (after the first user interaction, as browsers require) on supported devices.
- **Interactive Parsing Demo:** Type an expense in Hindi, Hinglish or English and watch an in-browser preview parse the intent, amount (₹, commas, `k`/`lakh`), category and people. Press Enter, `/` to focus, or tap an example chip.
- **How it works + QR code:** 3-step onboarding and a scannable QR for desktop visitors.
- **Mobile-first navigation:** Accessible hamburger menu on every page.
- **SEO ready:** Unique meta per page, absolute Open Graph images, JSON-LD (SoftwareApplication + FAQPage), `sitemap.xml`, `robots.txt`.
- **Accessible:** Skip link, keyboard focus styles, ARIA labels, `prefers-reduced-motion` support.
- **Zero Dependencies:** Built with pure HTML, CSS, and Vanilla JavaScript.

## Project Structure
- `index.html` - The main interactive landing page.
- `Documentation.html` - Guides on how to use the Telegram bot.
- `FAQ.html` - Frequently Asked Questions (accordion).
- `Privacy.html` - Privacy Policy.
- `Terms.html` - Terms of Service.
- `styles.css` - Shared design tokens, nav, footer and layout used by every page.
- `main.js` - Shared scripts: mobile menu, Telegram links, toasts.
- `logo.png` (original, 1024px) · `logo-512.png` (social previews) · `logo-128.png` (favicon/UI).
- `qr-telegram.svg` - QR code for `https://t.me/HeyMoneyMate_bot`.
- `vercel.json` - Clean URLs, caching and security headers.

## Telegram Bot & Statement Generation 🤖
MoneyMate includes a full-featured Telegram bot located in `bot/`:
- **Natural Language Parsing:** Log expenses and lending (udhaar) using natural Hinglish (e.g. `20 ki water bottle`, `Rahul ko 1000 diye`).
- **Statement Generation (`/statement` or `/hisab`):**
  - **Quick Ranges:** Today (`aaj`), This Week (`week` / default 7 days), This Month (`month`), Previous Month (`prev_month`).
  - **Inline Actions:** Switch ranges with a single tap or download the uncompressed original document (`Original Document`).
  - **Devanagari (Hindi) Support:** Pre-configured with fallback to `Nirmala UI` and `Noto Sans Devanagari` to prevent tofu/boxes.
  - **Testing & Previews:** Run `python bot/test_render_statement.py` to generate sample statement PNGs into the `preview/` folder.

## Deployment 🚀
This project is deployment-ready for platforms like Vercel, Netlify, or GitHub Pages. The main entry point is configured as `index.html`.

1. Clone the repository
2. Drag and drop the folder into your Vercel Dashboard, or use Vercel CLI:
   ```bash
   npm i -g vercel
   vercel
   ```

## SEO & Meta 
The site includes pre-configured Open Graph tags, descriptions, and theme colors optimized for sharing across social platforms (like WhatsApp, Twitter, and Telegram).

> **Custom domain?** All absolute URLs use `https://moneymate-website.vercel.app`. If you move to a custom domain, search-and-replace it across the HTML files, `robots.txt` and `sitemap.xml`.

---
*Money Mate - Log expenses just by chatting.*
