# Practical Usage Examples - Glances MCP

This guide presents concrete examples of using the Glances MCP server with Claude.

## 🎯 Scenario 1: Daily Monitoring

### Example 1.1: Morning Check-up

**You**:
```
Good morning Claude! Can you give me a status report on my server this morning?
```

**Claude**:
```
Good morning! Here's your server status this morning:

✅ OVERALL STATUS: Healthy

📊 KEY METRICS:
• CPU: 12% usage (4 cores)
  - User: 8%, System: 3%, Idle: 89%
  - Load average: 0.45, 0.52, 0.48 (1/5/15 min)

• MEMORY: 8.2 GB / 16 GB (51%)
  - Available: 7.8 GB
  - Swap: 512 MB / 4 GB (12%)

• DISKS:
  - / (sda1): 285 GB / 500 GB (57%) ✅
  - /home (sda2): 156 GB / 200 GB (78%) ⚠️
  - /var (sda3): 42 GB / 50 GB (84%) ⚠️

• NETWORK (eth0):
  - Received: 2.5 Mbps
  - Sent: 0.8 Mbps

• TEMPERATURE: 48°C (normal)

⚠️ ATTENTION POINTS:
1. /home approaching 80% - consider cleanup
2. /var at 84% - check logs

Need to analyze anything in particular?
```

*MCP tools used: `check_glances_status()`, `get_cpu_usage()`, `get_memory_usage()`, `get_disk_usage()`, `get_network_stats()`, `get_system_sensors()`*

---

### Example 1.2: Simplified Monitoring

**You**:
```
Just CPU and RAM please
```

**Claude**:
```
📊 Quick Stats:

CPU: 15% (Load: 0.6)
RAM: 51% (8.2/16 GB)

All good! 👍
```

*MCP tools used: `get_cpu_usage()`, `get_memory_usage()`*

---

## 🔍 Scenario 2: Problem Diagnosis

### Example 2.1: Slow Computer

**You**:
```
My computer has been sluggish for 10 minutes, what's happening?
```

**Claude**:
```
Let me analyze what's slowing down your system...

🔴 PROBLEM IDENTIFIED!

CPU is at 94% usage - here are the culprits:

TOP 5 RESOURCE-INTENSIVE PROCESSES:
1. ❌ node (PID 3421) - 45% CPU, 2.8 GB RAM
   └─ Command: node --max-old-space-size=4096 build.js
   └─ Started: 12 min ago

2. ❌ chrome (PID 2156) - 28% CPU, 3.2 GB RAM
   └─ 47 tabs open

3. ⚠️ docker (PID 1234) - 12% CPU, 1.5 GB RAM
   └─ Container: mysql_prod

4. ✅ code (PID 4567) - 5% CPU, 800 MB RAM
5. ✅ spotify (PID 5678) - 4% CPU, 450 MB RAM

🎯 ANALYSIS:
The Node.js process is performing a build consuming 45% CPU.
Chrome with 47 tabs is making the situation worse.

💡 RECOMMENDATIONS:
1. Urgent: Close some Chrome tabs (will save ~15% CPU)
2. Wait for Node.js build to finish (2-3 min estimated)
3. Optional: Restart MySQL container if slowness persists

Would you like me to monitor progress every 30 seconds?
```

*MCP tools used: `get_cpu_usage()`, `get_top_processes(10)`, `get_process_info(3421)`, `get_process_info(2156)`*

---

### Example 2.2: Memory Saturation

**You**:
```
I'm getting "Out of memory" messages, help me!
```

**Claude**:
```
🚨 CRITICAL MEMORY ALERT!

CURRENT STATE:
• RAM: 15.4 GB / 16 GB (96%) ❌
• Swap: 3.8 GB / 4 GB (95%) ❌
• Available: Only 640 MB

🔴 PROCESSES CONSUMING MOST RAM:

1. docker (PID 1234) - 4.2 GB
   └─ Container postgres_db
   └─ SUGGESTION: Limit Docker RAM

2. chrome (PID 2345) - 3.8 GB
   └─ 63 tabs open
   └─ ACTION: Close immediately!

3. intellij-idea (PID 5678) - 2.9 GB
   └─ Heap size: 2048m
   └─ SUGGESTION: Reduce -Xmx

4. node (PID 8901) - 2.1 GB
   └─ Multiple active processes

5. firefox (PID 3456) - 1.4 GB

⚡ IMMEDIATE ACTIONS:
1. ❌ Close Chrome NOW (will free ~4 GB)
2. ⚠️ Restart IntelliJ with -Xmx1024m
3. 🔄 Restart Postgres container with RAM limit
4. 🧹 Kill unused Node processes

🔧 SUGGESTED COMMANDS:
```bash
# Kill Chrome cleanly
killall chrome

# Limit Docker Postgres
docker update --memory=2g postgres_db

# View Node processes
ps aux | grep node
```

Long-term configuration recommended: upgrade to 32 GB RAM
```

*MCP tools used: `get_memory_usage()`, `get_top_processes(15)`, RAM analysis*

---

## 📈 Scenario 3: Temporal Analysis

### Example 3.1: Performance Evolution

**You**:
```
Show me CPU evolution over the last 2 hours
```

**Claude**:
```
📊 CPU EVOLUTION - LAST 2 HOURS (120 measurements)

ASCII Chart:
100%|                    ██                            |
 90%|                   ████                           |
 80%|                  ██████                          |
 70%|                 ████████                         |
 60%|                ██████████                        |
 50%|      ▓▓       ████████████                       |
 40%|     ▓▓▓▓     ██████████████      ▓▓             |
 30%|    ▓▓▓▓▓▓   ████████████████    ▓▓▓▓            |
 20%|   ▓▓▓▓▓▓▓▓ ██████████████████  ▓▓▓▓▓▓           |
 10%|▓▓▓▓▓▓▓▓▓▓▓████████████████████▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓|
  0%|__________________________________________________|
     12:00              13:00              14:00 (now)

📈 STATISTICS:
• Average: 28%
• Minimum: 8% (at 12:15)
• Maximum: 94% (at 13:23)
• Current: 15%

🔍 NOTABLE EVENTS:

1. ⚠️ PEAK at 13:23 (94%) - Duration: 8 minutes
   Probable cause: Build or compilation

2. 📊 Stable usage 12:00-12:45 (~12%)
   Low activity period

3. 📈 Progressive increase 12:45-13:15
   Normal ramp-up

4. ✅ Back to normal since 13:30
   System stabilized

💡 ANALYSIS:
Normal behavior with an isolated peak probably caused by
a batch task. No performance issues detected.

Want to see details of the 13:23 peak?
```

*MCP tools used: `get_plugin_history("cpu", 120)`*

---

### Example 3.2: Disk Trend

**You**:
```
My disk is filling up quickly, how long until it's full?
```

**Claude**:
```
📊 PREDICTIVE ANALYSIS - DISK SPACE

CURRENT STATE (/):
• Used: 285 GB / 500 GB (57%)
• Available: 215 GB
• Inodes: 12% used

📈 HISTORICAL ANALYSIS (last 30 days):
```
Day 1:  ████████████████████░░░░░░░░░ 42%
Day 5:  █████████████████████░░░░░░░░ 44%
Day 10: ██████████████████████░░░░░░░ 46%
Day 15: ███████████████████████░░░░░░ 49%
Day 20: ████████████████████████░░░░░ 52%
Day 25: █████████████████████████░░░░ 55%
Day 30: ██████████████████████████░░░ 57% ← Today
```

🔮 PREDICTIONS:

Average growth: +500 MB/day (~0.1%/day)

• 70% (350 GB): In ~130 days (April 21, 2026)
• 80% (400 GB): In ~230 days (July 30, 2026)
• 90% (450 GB): In ~330 days (November 7, 2026)
• 95% (475 GB): In ~380 days (December 27, 2026)

📁 MAIN CONSUMERS:
1. /var/log: 45 GB (application logs)
2. /home/user/Downloads: 38 GB
3. Docker images: 32 GB
4. /tmp: 12 GB

💡 RECOMMENDATIONS:

✨ QUICK ACTIONS (gain: ~80 GB):
```bash
# Clean old logs
sudo journalctl --vacuum-time=7d

# Empty downloads
rm -rf ~/Downloads/old/*

# Remove unused Docker images
docker system prune -a
```

📅 PLANNING:
• Short term (OK): Nothing urgent
• Medium term: Implement automatic log rotation
• Long term: Disk extension or NAS

You're safe for at least 6 months! 👍
```

*MCP tools used: `get_plugin_history("fs", 30)`, `get_disk_usage()`*

---

## 🔧 Scenario 4: Advanced Operations

### Example 4.1: Monitoring a Critical Process

**You**:
```
I just launched an important Python script (PID 9876).
Monitor it and let me know if there's a problem.
```

**Claude**:
```
✅ Monitoring activated for process 9876

📍 INITIAL INFORMATION:
• Name: python3
• Command: python3 data_processing.py --batch-size=1000
• State: Running
• Started: 2 seconds ago
• CPU: 85% (normal for data processing)
• RAM: 1.2 GB / 16 GB
• Disk I/O: 45 MB/s read, 12 MB/s write
• Threads: 4

📊 SYSTEM RESOURCES:
• Global CPU: 89% (your script + others)
• Available RAM: 14.2 GB (plenty available)
• Temperature: 62°C (normal increase)

✅ EVERYTHING IS NORMAL

I will monitor:
1. CPU usage (alert if > 98% for 5 min)
2. RAM usage (alert if > 8 GB)
3. Process state (alert if crash)
4. Excessive I/O (alert if > 200 MB/s for 10 min)

[⏱️ I'll keep you informed every 5 minutes or in case of anomaly]

💡 TIP: Type "status 9876" for instant update
```

*MCP tools used: `get_process_info(9876)`, `get_cpu_usage()`, `get_memory_usage()`*

---

**5 minutes later...**

**Claude** (automatic update):
```
📊 UPDATE - Process 9876

Elapsed time: 5 min 23 sec

State: ✅ Running (all good)
• CPU: 78% (stable)
• RAM: 2.1 GB (+900 MB - normal growth)
• I/O: 38 MB/s (decreasing, end of reading?)
• Estimated progress: ~25% (based on I/O patterns)

No anomalies detected. Next update in 5 min.
```

---

### Example 4.2: Before/After Comparison

**You**:
```
I'm going to optimize my MySQL config. Note the current state,
I'll tell you when to compare.
```

**Claude**:
```
📸 SNAPSHOT SAVED - MySQL Performance

TIMESTAMP: 2025-12-11 14:23:45

🔍 MYSQL STATE (PID 1234):
• CPU: 23%
• RAM: 2.8 GB
• Threads: 156
• Connections: 48 active

📊 SYSTEM METRICS:
• Global CPU: 45%
• Total RAM: 12.1 GB / 16 GB (75%)
• Load average: 1.8, 2.1, 1.9
• Disk I/O: 85 MB/s

📈 QUERIES (via process analysis):
• Queries/sec: ~450 (estimated via CPU patterns)
• I/O operations: High

✅ Baseline saved!
Type "compare mysql" when you're done with the optimization.
```

---

**After optimization...**

**You**:
```
compare mysql
```

**Claude**:
```
📊 BEFORE/AFTER COMPARISON - MySQL Optimization

┌─────────────────┬──────────┬──────────┬──────────┐
│ Metric          │ Before   │ After    │ Δ        │
├─────────────────┼──────────┼──────────┼──────────┤
│ CPU Usage       │ 23%      │ 14%      │ -39% ✅  │
│ RAM Usage       │ 2.8 GB   │ 2.1 GB   │ -25% ✅  │
│ Threads         │ 156      │ 98       │ -37% ✅  │
│ Connections     │ 48       │ 45       │ -6%  ✅  │
│ Load Avg (1m)   │ 1.8      │ 1.2      │ -33% ✅  │
│ Disk I/O        │ 85 MB/s  │ 62 MB/s  │ -27% ✅  │
└─────────────────┴──────────┴──────────┴──────────┘

🎉 EXCELLENT RESULTS!

💡 GAINS ACHIEVED:
• CPU saved: 9 percentage points
• RAM freed: 700 MB
• System load reduced by 33%
• I/O lightened by 23 MB/s

📈 PERFORMANCE:
The optimization is very effective! The system breathes better
and should handle more load.

✅ RECOMMENDATION:
Keep this configuration. Monitor for 24h to
confirm stability.

Would you like me to generate a complete report?
```

*MCP tools used: `get_process_info()`, temporal snapshots, comparisons*

---

## 🐳 Scenario 5: Docker and Containers

### Example 5.1: Docker Overview

**You**:
```
Give me a status of my Docker containers
```

**Claude**:
```
🐳 DOCKER CONTAINERS - OVERVIEW

📊 SUMMARY:
• Total containers: 5
• Running: 4 ✅
• Stopped: 1 ⚠️

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. ✅ webapp_prod (nginx:alpine)
   ├─ Status: Running (uptime: 12d 5h)
   ├─ CPU: 2% (very low)
   ├─ RAM: 125 MB / 512 MB limit (24%)
   ├─ Network: ↓ 5.2 Mbps  ↑ 1.8 Mbps
   └─ Health: Healthy

2. ✅ postgres_db (postgres:14)
   ├─ Status: Running (uptime: 12d 5h)
   ├─ CPU: 15% (active)
   ├─ RAM: 1.8 GB / 4 GB limit (45%)
   ├─ Network: ↓ 2.1 Mbps  ↑ 3.4 Mbps
   ├─ I/O: 85 MB/s read, 42 MB/s write
   └─ Health: Healthy

3. ✅ redis_cache (redis:7-alpine)
   ├─ Status: Running (uptime: 12d 5h)
   ├─ CPU: 1%
   ├─ RAM: 89 MB / 256 MB limit (35%)
   ├─ Network: ↓ 0.8 Mbps  ↑ 0.3 Mbps
   └─ Health: Healthy

4. ✅ worker_queue (python:3.11-slim)
   ├─ Status: Running (uptime: 3h 22m)
   ├─ CPU: 8%
   ├─ RAM: 340 MB / 1 GB limit (34%)
   ├─ Network: ↓ 0.2 Mbps  ↑ 0.1 Mbps
   └─ Health: Healthy

5. ⚠️ backup_service (custom/backup:latest)
   ├─ Status: Exited (code 0) - 2h ago
   ├─ Last seen: OK (normal, scheduled task)
   └─ Note: Launches automatically

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 TOTAL DOCKER USAGE:
• CPU: 26% (all containers)
• RAM: 2.36 GB / 5.77 GB allocated (41%)
• Network: ↓ 8.3 Mbps  ↑ 5.6 Mbps

💾 IMAGES:
• Total size: 4.2 GB
• Unused images: 1.8 GB (cleanable)

✅ OVERALL HEALTH: Excellent
All critical services are operational.

💡 SUGGESTION:
```bash
# Clean unused images
docker image prune -a
# Estimated gain: ~1.8 GB
```
```

*MCP tools used: `get_plugin_data("docker")`, Docker process analysis*

---

## 📊 Scenario 6: Reports and Exports

### Example 6.1: Weekly Report

**You**:
```
Generate a system health report for my DevOps team
```

**Claude**:
```markdown
# 📊 System Health Report
**Period**: Week of December 4-11, 2025
**Server**: prod-server-01
**Generated on**: December 11, 2025 at 2:30 PM

---

## 🎯 Executive Summary

✅ **Overall Status**: HEALTHY
⚠️ **Attention Points**: 2
❌ **Critical Issues**: 0

---

## 📈 Key Metrics

### CPU
- **Average usage**: 28%
- **Maximum peak**: 94% (Dec 8 at 3:23 PM)
- **Load average**: 1.2 / 1.5 / 1.4
- **Trend**: ↗️ +5% vs previous week

### Memory
- **Average usage**: 12.2 GB / 16 GB (76%)
- **Maximum peak**: 15.1 GB (94%) on Dec 9
- **Swap used**: Minimal (< 500 MB)
- **Trend**: → Stable

### Disks
| Partition | Used | Capacity | Evolution |
|-----------|------|----------|-----------|
| /         | 285 GB | 500 GB (57%) | +2 GB/week |
| /home     | 156 GB | 200 GB (78%) | +5 GB/week ⚠️ |
| /var      | 42 GB | 50 GB (84%) | +1 GB/week ⚠️ |

### Network
- **Average traffic**: ↓ 25 Mbps / ↑ 12 Mbps
- **Inbound peak**: 180 Mbps (backup on Dec 10)
- **Packet loss**: 0%
- **Average latency**: < 1ms

---

## ⚠️ Attention Points

### 1. Disk space /home (78%)
- **Priority**: Medium
- **Action**: Cleanup recommended within 30 days
- **Estimate**: Saturation in ~4 months at current rate

### 2. Disk space /var (84%)
- **Priority**: Medium
- **Action**: Implement log rotation
- **Detail**: 28 GB of logs in /var/log

---

## 🎯 Service Performance

### Docker Applications
| Service | Uptime | Avg CPU | Avg RAM | Status |
|---------|--------|---------|---------|--------|
| webapp_prod | 99.9% | 2% | 125 MB | ✅ |
| postgres_db | 100% | 12% | 1.8 GB | ✅ |
| redis_cache | 100% | 1% | 89 MB | ✅ |
| worker_queue | 98.2% | 8% | 340 MB | ✅ |

**Note**: worker_queue restarted 1x (planned maintenance)

---

## 📊 Incidents & Events

### Notable events
1. **Dec 8, 3:23 PM** - CPU peak 94% (duration: 8 min)
   - Cause: Scheduled application build
   - Impact: None

2. **Dec 9, 3:15 AM** - RAM usage 94%
   - Cause: Database backup
   - Impact: None, resolved automatically

3. **Dec 10, 2:00 AM** - Network peak 180 Mbps
   - Cause: Offsite backup
   - Impact: None

**Total alerts**: 3 (all resolved)

---

## 💡 Recommendations

### Short term (this week)
1. ✅ Implement automatic log rotation
   ```bash
   sudo logrotate -f /etc/logrotate.conf
   ```

2. ✅ Clean /home/user/Downloads (estimated gain: 35 GB)

### Medium term (this month)
1. 📋 Plan thorough /home cleanup
2. 📋 Evaluate RAM upgrade need (frequently approaches 90%)

### Long term (Q1 2026)
1. 💾 Extend disk capacity or implement NAS
2. 🔄 Migrate to server with 32 GB RAM

---

## 📞 Contacts & Support
**Team**: DevOps
**Contact**: devops@company.com
**Documentation**: wiki.company.com/infra

---

*Report generated automatically via Glances MCP*
```

Would you like this report in PDF or sent via email?
```

*MCP tools used: `get_all_system_stats()`, 7-day historical analysis, aggregation*

---

## 🎮 Scenario 7: Conversational Interactions

### Example 7.1: Natural Dialogue

**You**:
```
My computer is heating up a lot, is that normal?
```

**Claude**:
```
Let me check the temperature sensors...

🌡️ CURRENT TEMPERATURE: 78°C

⚠️ That's indeed elevated! Normal temperature is
between 40-60°C at idle, and up to 70°C under load.

Let's see what's causing this heat...

🔥 ANALYSIS:
• CPU: 89% usage → Main heat source
• Fans: 2800 RPM (85% of max speed)
• Resource-intensive processes detected:
  1. blender (3D rendering) - 52% CPU
  2. chrome (23 tabs) - 25% CPU
  3. docker - 12% CPU

💡 EXPLANATION:
Blender is doing a 3D render, heating is normal!
The fans are spinning fast to compensate.

POSSIBLE ACTIONS:
1. ✅ Let the render finish (fans are doing their job)
2. 💨 Make sure vents aren't blocked
3. 🧹 Clean fans if you haven't done so recently
4. ❌ Avoid using Chrome in parallel (closing = -10°C)

Want me to monitor the temperature and alert you if it
exceeds 85°C?
```

---

**You**:
```
Yes please monitor it
```

**Claude**:
```
✅ Temperature monitoring activated!

Alert threshold: 85°C
Current temperature: 78°C

I'll notify you if:
- Temperature > 85°C (critical)
- Temperature > 80°C for > 10 min (attention)
- Fans reach 100% (saturation)

🧘 Meanwhile, everything is under control.
The fans are managing heat dissipation well.
```

---

## 🤖 Scenario 8: Automation and Scripts

### Example 8.1: Monitoring Script

**You**:
```
Create a script that checks every hour if
my disks exceed 85% and sends me an email if so
```

**Claude**:
```python
#!/usr/bin/env python3
"""
Disk monitoring script with email alerts
Checks disk space every hour via Glances API
"""

import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
from datetime import datetime

# Configuration
GLANCES_URL = "http://localhost:61208"
THRESHOLD = 85  # Threshold in %
EMAIL_FROM = "monitoring@your-server.com"
EMAIL_TO = "you@example.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
CHECK_INTERVAL = 3600  # 1 hour in seconds

def check_disk_usage():
    """Check disk usage via Glances API"""
    try:
        response = requests.get(f"{GLANCES_URL}/api/4/fs")
        response.raise_for_status()
        disks = response.json()

        alerts = []
        for disk in disks:
            usage_percent = disk.get('percent', 0)
            mount_point = disk.get('mnt_point', 'Unknown')

            if usage_percent >= THRESHOLD:
                alerts.append({
                    'mount_point': mount_point,
                    'percent': usage_percent,
                    'size': disk.get('size', 0) / (1024**3),  # GB
                    'used': disk.get('used', 0) / (1024**3),  # GB
                    'free': disk.get('free', 0) / (1024**3),  # GB
                })

        return alerts
    except Exception as e:
        print(f"Error during check: {e}")
        return None

def send_email_alert(alerts):
    """Send email alert"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        msg['Subject'] = f"⚠️ Disk Space Alert - {len(alerts)} saturated partition(s)"

        # Email body
        body = f"""
        <html>
        <body>
            <h2>🚨 Disk Space Alert</h2>
            <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Threshold:</strong> {THRESHOLD}%</p>

            <h3>Affected partitions:</h3>
            <table border="1" style="border-collapse: collapse; padding: 10px;">
                <tr>
                    <th>Mount point</th>
                    <th>Usage</th>
                    <th>Used</th>
                    <th>Free</th>
                    <th>Total</th>
                </tr>
        """

        for alert in alerts:
            body += f"""
                <tr>
                    <td>{alert['mount_point']}</td>
                    <td style="color: red;"><strong>{alert['percent']:.1f}%</strong></td>
                    <td>{alert['used']:.1f} GB</td>
                    <td>{alert['free']:.1f} GB</td>
                    <td>{alert['size']:.1f} GB</td>
                </tr>
            """

        body += """
            </table>

            <h3>Recommended actions:</h3>
            <ul>
                <li>Clean temporary files</li>
                <li>Check for large logs</li>
                <li>Delete unnecessary files</li>
                <li>Consider capacity extension</li>
            </ul>

            <p><em>This message was automatically generated by the monitoring script.</em></p>
        </body>
        </html>
        """

        msg.attach(MIMEText(body, 'html'))

        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_FROM, "your_password")  # To configure
            server.send_message(msg)

        print(f"✅ Alert email sent for {len(alerts)} partition(s)")
        return True
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False

def main():
    """Main monitoring loop"""
    print("🚀 Starting disk monitoring...")
    print(f"   Threshold: {THRESHOLD}%")
    print(f"   Interval: {CHECK_INTERVAL}s ({CHECK_INTERVAL/3600}h)")
    print(f"   Email: {EMAIL_TO}")
    print()

    while True:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking...")

        alerts = check_disk_usage()

        if alerts is None:
            print("   ⚠️ Glances connection error")
        elif len(alerts) > 0:
            print(f"   🚨 {len(alerts)} partition(s) above threshold!")
            for alert in alerts:
                print(f"      - {alert['mount_point']}: {alert['percent']:.1f}%")
            send_email_alert(alerts)
        else:
            print("   ✅ All disks OK")

        print(f"   💤 Next check in {CHECK_INTERVAL/3600}h...\n")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping monitoring")
```

📋 **INSTALLATION INSTRUCTIONS:**

1. Install dependencies:
```bash
pip install requests
```

2. Configure the script:
```python
EMAIL_FROM = "your-email@example.com"
EMAIL_TO = "recipient@example.com"
# Also configure SMTP credentials
```

3. Run the script:
```bash
# Foreground (test)
python3 disk_monitor.py

# Background
nohup python3 disk_monitor.py > monitor.log 2>&1 &

# Or with systemd (production)
sudo systemctl start disk-monitor
```

4. Systemd configuration (optional):
```bash
# Create /etc/systemd/system/disk-monitor.service
sudo nano /etc/systemd/system/disk-monitor.service
```

Would you also like the complete systemd configuration?
```

*Conceptual MCP tools: API integration demonstration*

---

## 🎓 Scenario 9: Learning and Explanations

### Example 9.1: Understanding Metrics

**You**:
```
What is Load Average and why is mine at 2.5?
```

**Claude**:
```
📚 EXPLANATION - Load Average

Load Average represents the average system load over 3 periods:
• 1 minute
• 5 minutes
• 15 minutes

🔍 YOUR SYSTEM CURRENTLY:
Load Average: 2.5, 2.3, 1.8
Number of CPUs: 4 cores

💡 HOW TO INTERPRET IT:

Load Average indicates the average number of processes waiting
for execution. For a 4-core system:

• 0.0 - 1.0  →  Underutilized system ✅
• 1.0 - 4.0  →  Normal usage ✅
• 4.0 - 8.0  →  Loaded system ⚠️
• > 8.0      →  Overloaded system ❌

🎯 YOUR CASE (2.5):
Load: 2.5 / CPUs: 4 = 62.5% load

This is PERFECTLY NORMAL! Your system is using ~63% of its
capacity, with 37% margin remaining.

📊 DETAIL:
• Load 1m: 2.5 (current load)
• Load 5m: 2.3 (slight increase)
• Load 15m: 1.8 (upward trend over 15min)

📈 TREND:
Load is gradually increasing. Currently active processes:
1. python (build) - 45% CPU
2. chrome - 28% CPU
3. docker - 12% CPU

🎓 GOLDEN RULE:
Load Average < Number of CPUs = All good!

In your case: 2.5 < 4 ✅

Questions about other metrics?
```

---
