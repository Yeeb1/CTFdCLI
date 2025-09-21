# 🚩 CTFd CLI

A command-line interface for interacting with [CTFd](https://ctfd.io) (Capture The Flag) platforms. Streamline your CTF workflow with **automatic challenge synchronization**, **organized file management**, and **seamless flag submission**.

![out](https://github.com/user-attachments/assets/1f8bc4f5-b50b-4a98-b7e0-ec1011f64e77)

## 🌟 Key Features

- **🔄 Smart Challenge Sync**: Automatically download and organize challenges into structured directories
- **🎯 Auto Flag Submission**: Submit flags directly from challenge directories or via command line
- **📁 Intelligent File Management**: Download challenge files and generate comprehensive README files
- **🏷️ Multi-Profile Support**: Manage multiple CTF competitions simultaneously
- **📊 Progress Tracking**: Track solved challenges and submission attempts
- **🛠️ Offline-First**: Work with downloaded challenges without constant connectivity

## 📦 Installation

### Option 1: Install with uv (Recommended)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install CTFd CLI
git clone https://github.com/Yeeb1/CTFdCLI.git
cd ctfdcli
uv sync

# Run directly with uv
uv run ctfdcli --help
```

### Option 2: Install with pipx (Global Installation)

```bash
# Install pipx if you haven't already
pip install pipx

# Install CTFd CLI globally
pipx install git+https://github.com/Yeeb1/CTFdCLI.git

# Run from anywhere
ctfdcli --help
```

### Option 3: Development Installation

```bash
# Clone the repository
git clone https://github.com/Yeeb1/CTFdCLI.git
cd ctfdcli

# Install in development mode
pip install -e .

# Or with uv for development
uv pip install -e .
```

## 🚀 Quick Start Guide

### 1. Connect to Your CTF

```bash
# Initialize your first CTF profile
ctfdcli init --url https://demo.ctfd.io --token your_api_token
```

**Example Output:**
```
🔧 CTF Profile Setup
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Field       ┃ Value                                                                                              ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Profile     │ demo-ctfd                                                                                          │
│ URL         │ https://demo.ctfd.io                                                                               │
│ Token       │ ********************************                                                                   │
│ Status      │ ✅ Connected successfully                                                                          │
│ Challenges  │ 23 available                                                                                       │
└─────────────┴────────────────────────────────────────────────────────────────────────────────────────────────┘

✅ Profile 'demo-ctfd' created successfully!
```

### 2. 🔄 **Sync All Challenges** (Core Feature)

```bash
# Download and organize all challenges
ctfdcli sync
```
![sync](https://github.com/user-attachments/assets/45eb4c57-a5e7-4339-80dd-463963991418)



**Neat Directory Structure:**
```
challenges/
├── crypto/
│   ├── rsa-basics/
│   │   ├── README.md          # Complete challenge info
│   │   ├── challenge.txt      # Downloaded files
│   │   ├── public_key.pem
│   │   └── flag.txt           # Your workspace
│   └── aes-cipher/
│       ├── README.md
│       ├── encrypted.bin
│       └── flag.txt
├── web/
│   ├── sql-injection/
│   │   ├── README.md
│   │   ├── source.php
│   │   └── flag.txt
│   └── xss-challenge/
│       ├── README.md
│       └── flag.txt
└── misc/
    └── steganography/
        ├── README.md
        ├── image.png
        ├── hints.txt
        └── flag.txt
```
### 3. 🚀 **List All Challenges** (Core Feature)

```bash
# List all available challenges
ctfdcli challenges list
```


```bash
Fetching challenges from https://scoreboard.ctrl-space.gg/...
                                           🚩 Scoreboard Ctrl-Space Gg - Challenges                                            
┏━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ ID     ┃ Status ┃ Name                       ┃ Category     ┃ Type       ┃ Points   ┃ Solves ┃ Attempts   ┃ Solved By       ┃
┡━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ 33     │ ✅     │ sanity                     │              │ STD        │ 1        │ 290    │ 0/0        │ Yeeb            │
│ 1      │ ❌     │ Satellite-as-a-Service     │              │ DYN        │ 50       │ 169    │ 0/0        │ -               │
│ 34     │ ❌     │ Satellite-as-a-Service 2   │              │ DYN        │ 50       │ 65     │ 0/0        │ -               │
│ 29     │ ❌     │ hal-9000-1                 │              │ DYNA       │ 103      │ 32     │ 0/0        │ -               │
│ 22     │ ❌     │ Satellite Messaging System │              │ DYN        │ 204      │ 18     │ 0/0        │ -               │
│ 13     │ ❌     │ sar                        │              │ DYN        │ 251      │ 14     │ 0/0        │ -               │
│ 11     │ ❌     │ spAES-1                    │              │ DYN        │ 278      │ 12     │ 0/0        │ -               │
│ 14     │ ❌     │ DANSAT - Restore Me        │              │ DYNA       │ 343      │ 8      │ 0/0        │ -               │
│ 17     │ ❌     │ orbital-mechanics          │              │ DYN        │ 382      │ 6      │ 0/0        │ -               │
│ 26     │ ❌     │ carbonara-satellite        │              │ DYNA       │ 382      │ 6      │ 0/0        │ -               │
│ 32     │ ❌     │ x-otp                      │              │ DYN        │ 382      │ 6      │ 0/0        │ -               │
│ 30     │ ❌     │ hal-9000-2                 │              │ DYNA       │ 403      │ 5      │ 0/0        │ -               │
│ 31     │ ❌     │ hal-9000-3                 │              │ DYNA       │ 425      │ 4      │ 0/0        │ -               │
│ 2      │ ❌     │ payloadcalc                │              │ DYNA       │ 449      │ 3      │ 0/0        │ -               │
│ 16     │ ❌     │ DANSAT - Photo Shooting    │              │ DYNA       │ 449      │ 3      │ 0/0        │ -               │
│ 19     │ ❌     │ avenging lfsrs             │              │ DYN        │ 449      │ 3      │ 0/0        │ -               │
│ 10     │ ❌     │ Hamming Bird               │              │ DYN        │ 474      │ 2      │ 0/0        │ -               │
│ 20     │ ❌     │ lone-explorer              │              │ DYN        │ 474      │ 2      │ 0/0        │ -               │
│ 23     │ ❌     │ stack-building             │              │ DYN        │ 474      │ 2      │ 0/0        │ -               │
│ 24     │ ❌     │ stack-smashing             │              │ DYN        │ 474      │ 2      │ 0/0        │ -               │
│ 25     │ ❌     │ cosmic-ray                 │              │ DYN        │ 474      │ 2      │ 0/0        │ -               │
│ 12     │ ❌     │ spAES-2                    │              │ DYN        │ 500      │ 0      │ 0/0        │ -               │
│ 15     │ ❌     │ DANSAT - Hidden Secrets    │              │ DYNA       │ 500      │ 0      │ 0/0        │ -               │
│ 18     │ ❌     │ AS-FwUpd                   │              │ DYNA       │ 500      │ 1      │ 0/0        │ -               │
│ 21     │ ❌     │ Three Rounds Crypto        │              │ DYN        │ 500      │ 1      │ 0/0        │ -               │
└────────┴────────┴────────────────────────────┴──────────────┴────────────┴──────────┴────────┴────────────┴─────────────────┘

Showing 25 of 25 challenges | 1 solved (4.0%)
```
![chall](https://github.com/user-attachments/assets/005a446b-69d4-450c-9147-fcb11e67f77d)

### 4. 🎯 **Auto Flag Submission** (Core Feature)

#### Method A: Directory-Based Auto-Submit (Recommended)
```bash
# Navigate to any challenge directory
cd challenges/crypto/rsa-basics

# Work on the challenge, save your flag
echo "flag{rsa_cracked_successfully}" > flag.txt

# Auto-submit from current directory (reads flag.txt automatically)
ctfdcli cwd submit
```

**Example Output:**
```
╭───────────────────────────── 🚀 Flag Submission ─────────────────────────────╮
│                                                                              │
│  Challenge: RSA Basics                                                       │
│  Category: Crypto                                                            │
│  Points: 150                                                                 │
│  Flag Source: flag.txt                                                       │
│  Flag: flag{rsa_cracked_successfully}                                        │
│  Attempts: 0/∞                                                               │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
Submitting flag...
Trying endpoint: /challenges/attempt with payload: {'challenge_id': 15, 'submission': 'flag{rsa_cracked_successfully}'}

╭────────────────────────────────── ✅ Flag Accepted ──────────────────────────────────╮
│                                                                                      │
│  🎉 Correct! You solved 'RSA Basics'!                                                │
│                                                                                      │
│  Points earned: 150                                                                  │
│  Message: Correct                                                                    │
│                                                                                      │
╰──────────────────────────────────────────────────────────────────────────────────────╯
```

#### Method B: Direct Command Line Submission
```bash
# Submit directly with challenge ID and flag
ctfdcli submit 15 "flag{rsa_cracked_successfully}"
```

#### Method C: Bulk Auto-Submit
```bash
# Prepare multiple flags in a file
cat > solved_flags.txt << EOF
15:flag{rsa_cracked_successfully}
23:flag{sql_injection_works}
31:flag{xss_payload_executed}
42:flag{steganography_revealed}
EOF

# Submit all flags at once
ctfdcli submit bulk solved_flags.txt
```

**Example Bulk Output:**
```
📊 Bulk Submission Results
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Challenge ID  ┃ Challenge Name          ┃ Status        ┃ Message                                                  ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 15            │ RSA Basics              │ ✅ Correct    │ Correct                                                  │
│ 23            │ SQL Injection Basic     │ ✅ Correct    │ Correct                                                  │
│ 31            │ XSS Challenge           │ ✅ Correct    │ Correct                                                  │
│ 42            │ Hidden Message          │ ✅ Correct    │ Correct                                                  │
└───────────────┴─────────────────────────┴───────────────┴──────────────────────────────────────────────────────────┘

🎉 Summary: 4/4 flags correct (100.0%)
```

## 📝 Complete Command Reference

### Profile Management
```bash
# List all profiles
ctfdcli profiles

# Initialize new profile
ctfdcli init --name myctf --url https://ctf.example.com --token TOKEN

# Test connection
ctfdcli info --profile myctf
```

### Challenge Operations
```bash
# List all challenges
ctfdcli challenges

# List by category
ctfdcli challenges --category crypto

# Show only unsolved
ctfdcli challenges --unsolved

# Get challenge details
ctfdcli challenge-info 15
```

### Sync Operations
```bash
# Sync all challenges (main feature)
ctfdcli sync

# Sync specific category
ctfdcli sync --category web

# Sync without files (README only)
ctfdcli sync --no-files

# Use different profile
ctfdcli sync --profile myctf
```

### Directory-Based Operations
```bash
# Show current challenge info (when in challenge directory)
ctfdcli cwd info

# Submit from current directory (auto-reads flag.txt)
ctfdcli cwd submit

# Submit with confirmation prompt
ctfdcli cwd submit --confirm

# Preview submission (dry run)
ctfdcli cwd submit --dry-run

# Override flag from command line
ctfdcli cwd submit --flag "flag{manual_override}"
```

### Flag Submission
```bash
# Direct submission
ctfdcli submit 15 "flag{answer}"

# Interactive mode (prompts for flag)
ctfdcli submit 15 --interactive

# Bulk submission from file
ctfdcli submit bulk flags.txt

# View submission history
ctfdcli submit history
```

### Scoreboard & Stats
```bash
# View scoreboard
ctfdcli scoreboard

# Show detailed scoreboard
ctfdcli scoreboard --detailed

# Show only top 10
ctfdcli scoreboard --count 10
```
![score](https://github.com/user-attachments/assets/643bf8c4-9be7-4ad0-bad9-35547ced3848)

## 🔧 Advanced Workflows

### Multi-CTF Management
```bash
# Set up multiple CTFs
ctfdcli init --name picoctf --url https://picoctf.org --token TOKEN1
ctfdcli init --name h1ctf --url https://ctf.hacker101.com --token TOKEN2

# Work with different CTFs
ctfdcli sync --profile picoctf
ctfdcli sync --profile h1ctf

# Submit to specific CTF
cd challenges/crypto/rsa-challenge
ctfdcli cwd submit --profile picoctf
```

## 📁 Generated Files Explained

### README.md (Auto-generated for each challenge)
```markdown
# RSA Basics

**Category:** Crypto
**Points:** 150
**Challenge ID:** `15`
**Status:** ✅ SOLVED

## Description
Can you break this RSA encryption? The modulus might have some weaknesses...

## Files
- `challenge.txt` - The encrypted message
- `public_key.pem` - RSA public key (n=1234567...)

## Hints
- Think about common RSA attack vectors
- Check if the modulus is easily factorizable
- Try factordb.com for known factors

## Connection Info
nc challenge.ctf.com 1337

## Solution Notes
*Add your solution approach here*

## Tags
- rsa
- crypto
- factorization
```

### flag.txt (Your workspace)
```bash
# Before solving
echo "flag{your_solution_here}" > flag.txt

# After successful submission (auto-updated)
# SOLVED! ✅
flag{rsa_cracked_successfully}
```
## 💡 Pro Tips

1. **Use `cwd submit`**: Always prefer directory-based submission for organized workflow
2. **Sync Early**: Run `sync` at the start of CTF for offline access
3. **Multiple Profiles**: Set up profiles for different CTFs you participate in
4. **Bulk Operations**: Use bulk submission for rapid flag submission
5. **Connection Details**: Use `challenges connection` to extract all Connection Endpoints like Websites or `nc` services


### Development Setup
```bash
# Clone and setup development environment
git clone https://github.com/Yeeb1/CTFdCLI.git
cd ctfdcli
uv sync

# Run tests
pytest

# Format code
black .
isort .

# Lint
ruff check .
mypy .
```

---

## 🎯 Happy Hacking!


*Made with ❤️ for the CTF community*
