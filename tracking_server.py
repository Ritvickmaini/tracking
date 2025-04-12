from flask import Flask, request, redirect, send_file
from apscheduler.schedulers.background import BackgroundScheduler
import pandas as pd
import os, csv, smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

app = Flask(__name__)
LOG_FILE = "tracking_log.csv"
REPORT_EMAIL = "b2bgrowthexpo@gmail.com"
SMTP_SERVER = "mail.miltonkeynesexpo.com"
SMTP_PORT = 587
SENDER_EMAIL = "mike@miltonkeynesexpo.com"
SENDER_PASSWORD = "dvnn-&-((jdK"  # For production, use environment variables instead

# Ensure log file exists
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["email", "event", "timestamp"])

@app.route('/')
def index():
    return "✅ Tracking Server is Running"

@app.route('/track/open')
def track_open():
    email = request.args.get('email')
    if email:
        log_event(email, 'open')
    return send_file("pixel.png", mimetype='image/png')

@app.route('/track/click')
def track_click():
    email = request.args.get('email')
    url = request.args.get('url')
    if email and url:
        log_event(email, 'click')
    return redirect(url or "https://miltonkeynesexpo.com")

@app.route('/send_report')
def send_report():
    send_tracking_report()
    return "✅ Tracking report sent successfully!"

def log_event(email, event):
    with open(LOG_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([email, event, datetime.utcnow().isoformat()])

def send_tracking_report():
    if not os.path.exists(LOG_FILE):
        return

    df = pd.read_csv(LOG_FILE)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    cutoff = datetime.utcnow() - timedelta(hours=12)
    df_recent = df[df['timestamp'] >= cutoff]

    if df_recent.empty:
        return

    summary = df_recent.groupby('email')['event'].agg(lambda x: set(x)).reset_index()
    summary['opened'] = summary['event'].apply(lambda x: 'Yes' if 'open' in x else 'No')
    summary['clicked'] = summary['event'].apply(lambda x: 'Yes' if 'click' in x else 'No')
    summary.drop(columns=['event'], inplace=True)

    report_filename = f"tracking_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    summary.to_csv(report_filename, index=False)

    try:
        msg = EmailMessage()
        msg['Subject'] = "📊 Email Tracking Report"
        msg['From'] = SENDER_EMAIL
        msg['To'] = REPORT_EMAIL
        msg.set_content("Attached is the latest email open/click tracking report.")

        with open(report_filename, 'rb') as f:
            msg.add_attachment(f.read(), maintype='application', subtype='octet-stream', filename=report_filename)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("✅ Tracking report sent.")
    except Exception as e:
        print(f"❌ Failed to send tracking report: {e}")

# Start scheduler to send report every 12 hours
scheduler = BackgroundScheduler()
scheduler.add_job(send_tracking_report, 'interval', hours=12)
scheduler.start()

# Optional: send report on startup for testing
send_tracking_report()

# Render-compatible server binding
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8000)
