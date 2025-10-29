# Orbio IT Setup Guide for New Employees

Welcome to Orbio! This guide will walk you through setting up your technology and accounts. Our IT team is here to help every step of the way.

## First Day IT Checklist

On your first day, you'll meet with IT support to complete your initial setup. Plan for about 1-2 hours for this process.

### What to Expect
- [ ] Receive your laptop and starter kit equipment
- [ ] Set up your Orbio email account
- [ ] Configure laptop with security software
- [ ] Connect to Orbio networks (Wi-Fi and VPN)
- [ ] Install required software and tools
- [ ] Set up multi-factor authentication (MFA)
- [ ] Receive IT support contact information

## Laptop Setup

### Initial Configuration

Your laptop will arrive partially configured with Orbio's security software and system preferences. During your first day:

1. **Create your user account** - IT will help you set up your primary login
2. **Set a strong password** - Minimum 12 characters with mixed case, numbers, and symbols
3. **Enable full disk encryption** - Required for all Orbio devices
4. **Install security updates** - Make sure your OS is fully updated

### Required Software

The following software will be pre-installed or installed during setup:

**Security and Access**:
- **Endpoint protection**: CrowdStrike Falcon (antivirus and threat detection)
- **VPN**: GlobalProtect VPN client for secure remote access
- **Password manager**: 1Password (company license)

**Communication**:
- **Email**: Microsoft Outlook or Gmail (your choice)
- **Slack**: Company-wide communication platform
- **Zoom**: Video conferencing
- **Google Meet**: Alternative video conferencing

**Productivity**:
- **Google Workspace**: Gmail, Calendar, Drive, Docs, Sheets, Slides
- **Microsoft Office**: Word, Excel, PowerPoint (optional, if preferred)
- **Notion**: Company wiki and documentation

**Development Tools** (for engineering roles):
- **VS Code**: Recommended code editor
- **Git**: Version control
- **Docker**: Container management
- **Programming language tools**: Python, Node.js, or others based on your team

### Optional Software

You can request installation of additional software through the IT self-service portal:
- Additional code editors (IntelliJ, PyCharm, Sublime Text)
- Design tools (Figma, Sketch, Adobe Creative Suite)
- Database clients (DataGrip, DBeaver, MongoDB Compass)
- Project management tools (Jira, Asana)

## Email and Calendar Setup

### Orbio Email Account

Your Orbio email address will be: **[firstname.lastname]@orbio.com**

If your name is common, it might be: **[firstname.lastname][number]@orbio.com**

**Email Setup**:
1. Check your personal email for an invitation from IT
2. Click the activation link to set your password
3. Set up multi-factor authentication (Duo or Google Authenticator)
4. Configure your email signature (template provided in welcome packet)

**Email Client Options**:
- **Gmail Web Interface**: Access at mail.google.com (recommended for most users)
- **Outlook**: Desktop client available for Windows/Mac users
- **Mobile**: Configure Gmail or Outlook app on your phone

### Calendar Best Practices

- Keep your calendar up-to-date so colleagues can find meeting times
- Block out focus time for deep work
- Set your working hours in Calendar settings
- Use "Out of Office" for vacations and extended absences
- Accept/decline meeting invites promptly

### Email Signature Template

```
[Your Name]
[Your Title]
Orbio Inc.

📧 [firstname.lastname]@orbio.com
📱 [Your direct line, if applicable]
🌐 orbio.com

555 Market Street, Suite 1200
San Francisco, CA 94105
```

## Slack Setup

Slack is our primary internal communication tool. You'll receive an invitation during your first day.

### Joining Slack
1. Check your Orbio email for Slack invitation
2. Click "Join Orbio Workspace"
3. Download the Slack desktop app (recommended) or use the web version
4. Complete your profile:
   - Add profile photo
   - Add your title and team
   - Set your timezone
   - Add pronouns (optional)

### Essential Channels
You'll be automatically added to:
- **#general**: Company-wide announcements
- **#random**: Water cooler chat and fun stuff
- **#it-support**: Get help from IT team
- **#onboarding**: Connect with other new hires
- **#[your-team]**: Your team's main channel

### Slack Best Practices
- Use threads to keep conversations organized
- Set "Do Not Disturb" hours for work-life balance
- Use status updates to indicate availability
- React with emoji instead of "Thanks!" messages
- Search before asking - someone may have answered already

## VPN Setup (Remote Access)

If you work remotely or need to access internal systems from outside the office, you'll need VPN access.

### Installing GlobalProtect VPN

**macOS**:
1. IT will provide the installer during setup
2. Install GlobalProtect from the DMG file
3. Open GlobalProtect from Applications
4. Enter portal address: **vpn.orbio.com**
5. Log in with your Orbio email and password
6. Approve MFA prompt on your phone

**Windows**:
1. IT will provide the installer during setup
2. Run the GlobalProtect MSI installer
3. Open GlobalProtect from the Start menu
4. Enter portal address: **vpn.orbio.com**
5. Log in with your Orbio email and password
6. Approve MFA prompt on your phone

### When to Use VPN
- Working from home or remote locations
- Accessing internal systems (databases, admin panels, etc.)
- Connecting to file servers
- Accessing development environments

**Note**: You don't need VPN for regular work like email, Slack, or Google Drive. Only connect when accessing internal systems.

### VPN Troubleshooting
- **Can't connect**: Check your internet connection first
- **Authentication fails**: Verify your password in the IT portal
- **Slow performance**: Try disconnecting and reconnecting
- **Still having issues**: Contact IT support (see contact info below)

## Password Manager (1Password)

Security is critical at Orbio. We use 1Password to securely store and share passwords.

### Setting Up 1Password
1. You'll receive an invitation email to join the Orbio 1Password team
2. Click "Join Team" and create your master password
   - **This is the only password you'll need to remember**
   - Make it strong and unique (12+ characters)
   - Write it down and store it securely (not digitally!)
3. Install 1Password on your devices:
   - Download from 1password.com for desktop
   - Download from App Store or Google Play for mobile
4. Install the 1Password browser extension for easy password access

### Using 1Password
- **Generating passwords**: Use the built-in generator for new accounts
- **Saving passwords**: 1Password will prompt to save credentials when you log in
- **Shared vaults**: Your team will share access to common accounts
- **Emergency access**: IT maintains emergency access procedures

**Important**: Never share passwords via email or Slack. Use 1Password's secure sharing features.

## Wi-Fi Access

### Office Wi-Fi

**Orbio-Secure** (Recommended for employees):
- Network: **Orbio-Secure**
- Authentication: Your Orbio email and password
- Automatically configured on company laptops

**Orbio-Guest** (For personal devices and visitors):
- Network: **Orbio-Guest**
- Password: Available at reception desk or in #it-support Slack channel
- Resets monthly for security

### Home Wi-Fi Security
When working from home:
- Use a strong Wi-Fi password
- Enable WPA3 or WPA2 encryption
- Keep your router firmware updated
- Consider connecting VPN for sensitive work

## Multi-Factor Authentication (MFA)

MFA adds an extra layer of security to your accounts. You'll need to set this up during your first day.

### Supported MFA Methods
1. **Duo Mobile** (Recommended): Push notifications to your phone
2. **Google Authenticator**: Time-based codes
3. **SMS**: Text message codes (backup method)
4. **Hardware token**: YubiKey available upon request

### Setting Up Duo Mobile
1. Download Duo Mobile from App Store or Google Play
2. During account setup, scan the QR code with Duo Mobile
3. Approve the test push notification
4. Save backup codes in a secure location

### When You'll Need MFA
- Logging into Orbio email
- Accessing VPN
- Logging into internal systems (databases, admin tools)
- Accessing 1Password vault

## Software Installation Requests

Need additional software? Submit requests through our IT self-service portal.

### How to Request Software
1. Go to **it.orbio.com/requests**
2. Click "New Software Request"
3. Provide:
   - Software name and version
   - Business justification
   - License type (free or paid)
   - Urgency level
4. IT will review and approve within 1-2 business days

### Pre-Approved Software
The following software is pre-approved and can be self-installed:
- Chrome, Firefox, Safari, Edge (browsers)
- VS Code, Sublime Text (code editors)
- Slack, Zoom, Microsoft Teams (communication)
- Notion, Evernote (note-taking)
- Spotify, iTunes (music, for personal use)

### Restricted Software
Some software requires special approval due to security or licensing:
- Database management tools
- Remote desktop software
- File sharing applications
- Virtualization software

## Development Environment Setup

For engineering roles, you'll need to set up your development environment.

### Version Control (Git)
```bash
# Configure Git with your Orbio email
git config --global user.name "Your Name"
git config --global user.email "[firstname.lastname]@orbio.com"

# Set up SSH key for GitHub
ssh-keygen -t ed25519 -C "[firstname.lastname]@orbio.com"
# Add the public key to your GitHub account
```

### Access to Repositories
- **GitHub Organization**: github.com/orbio-inc
- Request access from your manager or IT
- You'll be added to your team's repositories

### Development Tools
Your team lead will provide specific setup instructions for:
- Programming language environments
- Package managers
- Database clients
- API testing tools
- CI/CD tools

## Mobile Device Setup

### Adding Orbio Email to Your Phone

**iPhone**:
1. Open Settings > Mail > Accounts > Add Account
2. Select "Google" for Gmail-based email
3. Enter your Orbio email and password
4. Enable Mail, Contacts, and Calendar sync

**Android**:
1. Open Gmail app > Settings > Add account
2. Select "Google"
3. Enter your Orbio email and password
4. Configure sync settings

### Recommended Apps
- **Slack**: Stay connected with your team
- **Google Calendar**: Manage your schedule
- **Duo Mobile**: MFA authentication
- **1Password**: Access passwords securely
- **Google Drive**: Access company documents

### Mobile Device Security
- Set a strong passcode or biometric lock
- Enable "Find My Device" (iPhone) or "Find My Phone" (Android)
- Don't jailbreak or root your device
- Keep OS and apps updated

## Getting IT Support

Our IT team is here to help! Here's how to reach us:

### IT Support Channels

**Slack** (Fastest for quick questions):
- Post in **#it-support** channel
- Response time: Usually within 15 minutes during business hours

**Email**:
- **it@orbio.com**
- Response time: Within 4 hours during business hours

**Phone**:
- **(415) 555-0123**
- Available Monday-Friday, 8:00 AM - 6:00 PM Pacific Time
- For urgent issues only

**IT Self-Service Portal**:
- **it.orbio.com**
- Submit tickets, track requests, browse knowledge base

**In-Person**:
- Visit the IT desk near reception (12th floor)
- Walk-in hours: Monday-Friday, 9:00 AM - 5:00 PM

### When to Contact IT

Contact IT support for:
- Login or password issues
- Software installation requests
- Hardware problems (broken laptop, mouse, etc.)
- Network or VPN issues
- Security concerns
- Access requests (systems, tools, repositories)

### IT Support Tips
- Provide detailed information about the issue
- Include error messages if applicable
- Let us know if it's urgent
- Have your laptop model and serial number ready (printed on laptop bottom)

## Security Best Practices

### Protect Company Data
- **Lock your screen** when stepping away (Cmd+Ctrl+Q on Mac, Win+L on Windows)
- **Don't share passwords** - use 1Password for secure sharing
- **Be cautious with emails** - watch for phishing attempts
- **Report suspicious activity** to security@orbio.com
- **Use VPN** when accessing internal systems remotely
- **Encrypt sensitive files** before sharing externally

### Laptop Security
- Never leave your laptop unattended in public places
- Store your laptop securely when not in use
- Don't let others use your company laptop
- Report lost or stolen devices immediately to IT

### Data Handling
- Store company documents in Google Drive, not on your laptop
- Don't use personal cloud storage (Dropbox, iCloud) for company data
- Follow data classification guidelines (available in Notion)
- Shred or securely delete sensitive documents

## Troubleshooting Common Issues

### Can't Log Into Email
1. Verify you're using the correct email address
2. Reset your password at **accounts.orbio.com**
3. Check that MFA device is working
4. Contact IT support if still unable to access

### VPN Won't Connect
1. Check your internet connection
2. Restart the GlobalProtect application
3. Try disconnecting and reconnecting
4. Verify your password hasn't expired
5. Contact IT if problem persists

### Laptop Running Slow
1. Restart your computer
2. Close unnecessary applications
3. Check for software updates
4. Clear browser cache
5. Contact IT if performance doesn't improve

### Software Not Working
1. Restart the application
2. Check for updates
3. Restart your computer
4. Try uninstalling and reinstalling
5. Contact IT if issue continues

## Welcome to Orbio!

You're all set! If you have any questions during your setup process, don't hesitate to reach out to our IT team. We're here to ensure your technology works seamlessly so you can focus on doing great work.

**IT Support**:
- Slack: #it-support
- Email: it@orbio.com
- Phone: (415) 555-0123
- Portal: it.orbio.com

Happy computing!
