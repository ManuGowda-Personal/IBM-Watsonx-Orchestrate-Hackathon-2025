import sys, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ✅ Fix encoding for Windows terminals
sys.stdout.reconfigure(encoding='utf-8')

to_addr = sys.argv[1]
subject = sys.argv[2]
body_html = sys.stdin.read()

from_addr = "manohara.arm@gmail.com"
smtp_server = "smtp.gmail.com"
smtp_port = 587
smtp_user = "manohara.arm@gmail.com"
smtp_pass = "yzse lfce ghqm fusj"

msg = MIMEMultipart("alternative")
msg["Subject"] = subject
msg["From"] = from_addr
msg["To"] = to_addr
msg.attach(MIMEText(body_html, "html"))

try:
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(from_addr, [to_addr], msg.as_string())
    print("✅ Email sent successfully.")
except Exception as e:
    try:
        print(f"❌ Email send failed: {e}")
    except Exception:
        print("Email send failed.")
    sys.exit(1)
