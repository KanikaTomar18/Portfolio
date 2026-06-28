import os
import re
import smtplib
from email.message import EmailMessage

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

# Allow your deployed frontend (and localhost while testing) to call this API.
# Replace these with your actual frontend URL(s) once deployed.
ALLOWED_ORIGINS = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "https://kanikatomar18.github.io",   # example if you host the frontend on GitHub Pages
    # "https://your-custom-domain.com",
]
CORS(app, origins=ALLOWED_ORIGINS, methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type"])
@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error(f"Unhandled error: {e}")
    return jsonify({"ok": False, "error": "Server error. Please try again."}), 500

EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")        # the Gmail account that SENDS the mail
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")      # a Gmail "App Password", not your normal password
TO_EMAIL = os.environ.get("TO_EMAIL", EMAIL_ADDRESS)   # where you want to RECEIVE messages

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@app.get("/")
def health_check():
    """Simple endpoint so you (or Render) can confirm the service is alive."""
    return jsonify({"status": "ok", "service": "kanika-portfolio-contact-api"})


@app.post("/api/contact")
def contact():
    data = request.get_json(silent=True) or request.form

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    subject = (data.get("subject") or "Portfolio contact form").strip()
    message = (data.get("message") or "").strip()

    # --- basic validation ---
    if not name or not email or not message:
        return jsonify({"ok": False, "error": "Name, email and message are required."}), 400

    if not EMAIL_RE.match(email):
        return jsonify({"ok": False, "error": "Please enter a valid email address."}), 400

    if len(message) > 5000:
        return jsonify({"ok": False, "error": "Message is too long."}), 400

    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        app.logger.error("EMAIL_ADDRESS / EMAIL_PASSWORD env vars are not set.")
        return jsonify({"ok": False, "error": "Server email is not configured."}), 500

    # --- build and send the email ---
    try:
        msg = EmailMessage()
        msg["Subject"] = f"Portfolio contact: {subject}"
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = TO_EMAIL
        msg["Reply-To"] = email
        msg.set_content(
            f"New message from your portfolio contact form\n\n"
            f"Name: {name}\n"
            f"Email: {email}\n"
            f"Subject: {subject}\n\n"
            f"Message:\n{message}\n"
        )

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)

        return jsonify({"ok": True, "message": "Thanks! Your message has been sent."})

    except Exception as exc:  # noqa: BLE001 - we want to log and return a clean error either way
        app.logger.error(f"Failed to send contact email: {exc}")
        return jsonify({"ok": False, "error": "Something went wrong sending your message. Please try again later."}), 500


if __name__ == "__main__":
    # Local dev only. In production, gunicorn runs this (see Procfile).
    app.run(debug=True, port=5000)
