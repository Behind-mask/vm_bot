import psutil
import time
import datetime
import schedule
import logging
import os
import subprocess
import json
from dateutil import parser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import pytz

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/ubuntu/logs/vm_monitor.log'),
        logging.StreamHandler()
    ]
)

class VMMonitor:
    def __init__(self):
        self.last_activity_time = datetime.datetime.now()
        self.inactivity_threshold = datetime.timedelta(minutes=30)
        # Times in UTC (IST - 5:30)
        self.monitoring_start_time = parser.parse('16:30').time()  # 10:00 PM IST
        self.warning_time = parser.parse('16:45').time()  # 10:15 PM IST
        self.shutdown_time = parser.parse('17:00').time()  # 10:30 PM IST
        self.is_monitoring = False
        self.email_sent = False
        self.override_user = None
        self.override_time = None
        self.warning_email_sent = False
        self.shutdown_executed = False
        
        # Email configuration from .env file
        self.email_sender = os.getenv('VM_MONITOR_EMAIL')
        self.email_password = os.getenv('VM_MONITOR_EMAIL_PASSWORD')
        self.email_recipients = os.getenv('VM_MONITOR_RECIPIENTS', '').split(',')
        self.smtp_server = os.getenv('VM_MONITOR_SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('VM_MONITOR_SMTP_PORT', '587'))
        
        # Validate email configuration
        if not all([self.email_sender, self.email_password, self.email_recipients]):
            logging.error("Email configuration is incomplete. Please check your .env file.")

    def send_email(self, subject, body):
        """Send email notification"""
        try:
            if not all([self.email_sender, self.email_password, self.email_recipients]):
                logging.error("Email configuration is incomplete. Please set all required environment variables.")
                return False

            msg = MIMEMultipart()
            msg['From'] = self.email_sender
            msg['To'] = ', '.join(self.email_recipients)
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_sender, self.email_password)
                server.send_message(msg)

            logging.info(f"Email notification sent: {subject}")
            return True
        except Exception as e:
            logging.error(f"Failed to send email: {e}")
            return False

    def process_override_command(self, username):
        """Process the override command from a user"""
        self.override_user = username
        self.override_time = datetime.datetime.now()
        logging.info(f"Shutdown override registered by user: {username}")
        
        # Send email notification about override
        subject = "VM Shutdown Override Notification"
        body = f"VM shutdown has been overridden by {username} at {self.override_time.strftime('%Y-%m-%d %H:%M:%S')}"
        self.send_email(subject, body)
        return True

    def check_override_validity(self):
        """Check if there's a valid override in place"""
        if not self.override_user or not self.override_time:
            # Check for override file
            override_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vm_override.json')
            if os.path.exists(override_file):
                try:
                    with open(override_file, 'r') as f:
                        data = json.load(f)
                        override_time = parser.parse(data['timestamp'])
                        
                        # Only accept override from the current day
                        if override_time.date() == datetime.datetime.now().date():
                            self.override_user = data['username']
                            self.override_time = override_time
                            # Remove the override file after reading
                            os.remove(override_file)
                            return True
                except Exception as e:
                    logging.error(f"Error reading override file: {e}")
                    return False
            return False
             
        # Override is valid for the current day only
        now = datetime.datetime.now()
        return self.override_time.date() == now.date()

    def should_start_monitoring(self):
        """Determine if monitoring should start (after 10:00 PM)"""
        current_time = datetime.datetime.now().time()
        return current_time >= self.monitoring_start_time

    def should_shutdown(self):
        """Determine if the system should be shut down"""
        # If there's an override, never auto-shutdown
        if self.check_override_validity():
            return False
            
        current_time = datetime.datetime.now()
        current_time_only = current_time.time()
        
        # Only consider shutdown after shutdown_time (10:30 PM IST / 17:00 UTC)
        if current_time_only >= self.shutdown_time:
            time_since_last_activity = current_time - self.last_activity_time
            
            if time_since_last_activity >= self.inactivity_threshold:
                logging.info(f"No activity detected for {time_since_last_activity}. Initiating shutdown...")
                return True
        
        # Send warning email 15 minutes before potential shutdown (10:15 PM IST / 16:45 UTC)
        if current_time_only >= self.warning_time and current_time_only < self.shutdown_time and not self.email_sent:
            subject = "VM Shutdown Warning"
            body = ("The VM is scheduled to shut down at 10:30 PM IST (5:00 PM UTC) if no activity is detected.\n\n"
                   "To prevent automatic shutdown and keep the VM running:\n"
                   "1. SSH into the VM\n"
                   "2. Run the following command:\n"
                   "   cd ~/joval/vm_bot\n"
                   "   python3 vm_override.py <your_name>\n\n"
                   "Example: python3 vm_override.py john\n\n"
                   "Note: Once you override, you will be responsible for manually shutting down the VM when you're done.")
            self.send_email(subject, body)
            self.email_sent = True
        
        return False

    def shutdown_system(self):
        """Initiate system shutdown"""
        try:
            logging.info("Initiating system shutdown...")
            if os.path.exists('/home/ubuntu/logs/vm_monitor.log'):  # Only log if we can still write
                logging.info("Shutdown command executed successfully")
                subprocess.run(['sudo', 'poweroff'], check=True)
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to execute shutdown command: {e}")
            return False
        except Exception as e:
            logging.error(f"Failed to initiate shutdown: {e}")
            return False

    def run_monitor(self):
        """Main monitoring loop"""
        current_time = datetime.datetime.now().time()
        # Reset flags and override at the start of each day
        if current_time < self.monitoring_start_time:
            self.warning_email_sent = False
            self.shutdown_executed = False
            self.override_user = None
            self.override_time = None
            self.is_monitoring = False
            return
        # Check for override first
        if self.check_override_validity():
            if not self.warning_email_sent:
                subject = "VM Shutdown Override Active"
                body = f"VM automatic shutdown is disabled for today as {self.override_user} has requested manual control. They will shut down the VM manually."
                self.send_email(subject, body)
                self.warning_email_sent = True
                logging.info(f"Monitoring disabled for today due to override by {self.override_user}")
            return  # Skip all monitoring when override is active
        # Send warning email at warning_time
        if current_time >= self.warning_time and not self.warning_email_sent:
            subject = "VM Shutdown Warning"
            body = ("The VM is scheduled to shut down at 10:30 PM IST (5:00 PM UTC) today.\n\n"
                   "To prevent automatic shutdown and keep the VM running:\n"
                   "1. SSH into the VM\n"
                   "2. Run the following command:\n"
                   "   cd ~/joval/vm_bot\n"
                   "   python3 vm_override.py <your_name>\n\n"
                   "Example: python3 vm_override.py john\n\n"
                   "Note: Once you override, you will be responsible for manually shutting down the VM when you're done.")
            self.send_email(subject, body)
            self.warning_email_sent = True
            logging.info("Warning email sent.")
        # Shutdown at shutdown_time
        if current_time >= self.shutdown_time and not self.shutdown_executed:
            logging.info("Shutdown time reached. Initiating shutdown...")
            self.shutdown_system()
            self.shutdown_executed = True

def main():
    monitor = VMMonitor()
    
    # Schedule the monitoring task to run every 5 minutes
    schedule.every(5).minutes.do(monitor.run_monitor)
    
    logging.info("VM Monitor service started")
    logging.info("Will begin monitoring at 10:00 PM")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Wait for 1 minute before next check

if __name__ == "__main__":
    main() 