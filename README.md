# VM Monitor System

An automated system to monitor VM activity and manage shutdowns with email notifications and manual override capabilities.

## Features

- Automatic VM monitoring between 10:00 PM and 10:30 PM
- Automatic shutdown at 10:30 PM if no activity is detected
- Email notifications 15 minutes before shutdown
- Manual override system allowing users to take control of shutdown
- Activity detection based on CPU usage and active users
- Daily reset of monitoring status

## Setup

### Prerequisites

- Python 3.6 or higher
- Required Python packages:
```bash
sudo apt update
sudo apt install python3-pip
pip3 install psutil schedule python-dateutil python-dotenv
```

### Email Configuration

The system uses email notifications for shutdown warnings and override confirmations. You can configure the email settings using a `.env` file:

1. Create a `.env` file in the project directory:
```bash
sudo nano /path/to/vm_monitor/.env
```

2. Add the following configuration (replace with your values):
```ini
VM_MONITOR_EMAIL=your-email@example.com
VM_MONITOR_EMAIL_PASSWORD=your-email-password
VM_MONITOR_RECIPIENTS=recipient1@example.com,recipient2@example.com
VM_MONITOR_SMTP_SERVER=smtp.gmail.com
VM_MONITOR_SMTP_PORT=587
```

3. Set proper permissions for the .env file:
```bash
sudo chown root:root /path/to/vm_monitor/.env
sudo chmod 600 /path/to/vm_monitor/.env
```

**Note for Gmail users**: You'll need to use an App Password if you have 2-factor authentication enabled.

Alternatively, you can still use system-wide environment variables by adding them to `/etc/environment` or `~/.bashrc` as described in the previous section.

## Installation as a Service

1. Create a systemd service file:
```bash
sudo nano /etc/systemd/system/vm-monitor.service
```

2. Add the following content (replace paths accordingly):
```ini
[Unit]
Description=VM Activity Monitor
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/path/to/vm_monitor
# Environment variables are now loaded from .env file
ExecStart=/usr/bin/python3 /path/to/vm_monitor/vm_monitor.py
Restart=always

[Install]
WantedBy=multi-user.target
```

3. Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable vm-monitor
sudo systemctl start vm-monitor
```

4. Check service status:
```bash
sudo systemctl status vm-monitor
```

## Usage

### Starting the Monitor

If not running as a service, start the monitor manually:
```bash
sudo python3 vm_monitor.py
```

The system will:
1. Start monitoring at 10:00 PM
2. Send a warning email at 10:15 PM
3. Initiate shutdown at 10:30 PM if no activity or override is detected

### Manual Override

To prevent automatic shutdown and take manual control:
```bash
sudo python3 vm_override.py <your_name>
```

Example:
```bash
sudo python3 vm_override.py john_doe
```

When using the override:
- The automatic monitoring system is disabled for the entire day
- An email notification is sent confirming manual control
- The VM will not shut down automatically
- The user who requested the override is responsible for manual shutdown
- Override status resets the next day before 10:00 PM

### Activity Detection

The system considers the VM active if:
- CPU usage is above 10%
- There are active user sessions

## Logging

The system maintains logs in:
- `/var/log/vm_monitor.log`: Contains monitoring events, shutdowns, and system status
- System journal (view with `journalctl -u vm-monitor`)

## Files

- `vm_monitor.py`: Main monitoring system
- `vm_override.py`: Command-line tool for manual override
- `vm_override.json`: Temporary file storing override status (automatically managed)
- `/var/log/vm_monitor.log`: Log file

## File Permissions

Set appropriate permissions:
```bash
sudo chown root:root vm_monitor.py vm_override.py
sudo chmod 755 vm_monitor.py vm_override.py
sudo chown root:root /var/log/vm_monitor.log
sudo chmod 644 /var/log/vm_monitor.log
```

## Shutdown Schedule

- 10:00 PM: Monitoring begins
- 10:15 PM: Warning email sent
- 10:30 PM: Automatic shutdown (if no activity/override)

## Troubleshooting

1. **Email notifications not working**
   - Check environment variables: `printenv | grep VM_MONITOR`
   - Verify SMTP settings in logs: `sudo journalctl -u vm-monitor | grep "email"`
   - For Gmail, ensure you're using an App Password

2. **Override not working**
   - Check file permissions: `ls -l /path/to/vm_override.json`
   - Verify log entries: `sudo tail -f /var/log/vm_monitor.log`
   - Check systemd journal: `sudo journalctl -u vm-monitor -f`

3. **Automatic shutdown not working**
   - Check service status: `sudo systemctl status vm-monitor`
   - Verify permissions: `sudo -l`
   - Review logs: `sudo journalctl -u vm-monitor --since "1 hour ago"`

## Security Notes

- Store email credentials in `/etc/environment` or use systemd environment variables
- Run the monitor with root privileges (required for shutdown)
- Keep the override command access restricted using sudo
- Consider using `sudoers` to allow specific users to run the override command

## Service Management

```bash
# Start the service
sudo systemctl start vm-monitor

# Stop the service
sudo systemctl stop vm-monitor

# Restart the service
sudo systemctl restart vm-monitor

# View logs
sudo journalctl -u vm-monitor -f
```

## Contributing

Feel free to submit issues and enhancement requests!
