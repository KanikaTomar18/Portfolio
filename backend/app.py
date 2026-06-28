import os
import re
import requests

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

ALLOWED_ORIGINS = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "https://kanikatomar18.github.io",
]
CORS(app, resources={r"/api/*": {"origins": ALLOWED_ORIGINS}})

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
TO_EMAIL = os.environ.get("TO_EMAIL")  # where YOU want to receive messages

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@app.get("/")
def health_check():
    return jsonify({"status": "ok", "service": "kanika-portfolio-contact-api"})


@app.post("/api/contact")
def contact():
    data = request.get_json(silent=True) or request.form

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    subject = (data.get("subject") or "Portfolio contact form").strip()
    message = (data.get("message") or "").strip()

    if not name or not email or not message:
        return jsonify({"ok": False, "error": "Name, email and message are required."}), 400

    if not EMAIL_RE.match(email):
        return jsonify({"ok": False, "error": "Please enter a valid email address."}), 400

    if len(message) > 5000:
        return jsonify({"ok": False, "error": "Message is too long."}), 400

    if not RESEND_API_KEY or not TO_EMAIL:
        app.logger.error("RESEND_API_KEY / TO_EMAIL env vars are not set.")
        return jsonify({"ok": False, "error": "Server email is not configured."}), 500

    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": "Portfolio Contact <onboarding@resend.dev>",
                "to": [TO_EMAIL],
                "reply_to": email,
                "subject": f"Portfolio contact: {subject}",
                "text": (
                    f"New message from your portfolio contact form\n\n"
                    f"Name: {name}\n"
                    f"Email: {email}\n"
                    f"Subject: {subject}\n\n"
                    f"Message:\n{message}\n"
                ),
            },
            timeout=10,
        )

        if resp.status_code >= 400:
            app.logger.error(f"Resend API error: {resp.status_code} {resp.text}")
            return jsonify({"ok": False, "error": "Something went wrong sending your message."}), 500

        return jsonify({"ok": True, "message": "Thanks! Your message has been sent."})

    except Exception as exc:
        app.logger.error(f"Failed to send contact email: {exc}")
        return jsonify({"ok": False, "error": "Something went wrong sending your message. Please try again later."}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)