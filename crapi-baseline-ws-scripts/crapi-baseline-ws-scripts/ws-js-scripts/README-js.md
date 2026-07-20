# crAPI Baseline Script (Node.js) - RHEL Setup Guide

This script baselines the crAPI environment by simulating realistic user traffic using Node.js. It registers and logs in users, adds vehicles, places orders, interacts with the community forum, and more.

**This script is intended to be used after the Noname platform has been installed, and the crAPI traffic has been integrated and the integration has been validated.**

By default, 100 users are simulated at a concurrency of 10. This can be tuned via environment variables (see below).

## Requirements

- RHEL 8 or 9
- Node.js 18+
- npm

## Install Node.js

First check if Node.js is already installed and what version:

```bash
node --version
```

If it's not installed or the version is below 18, install via NodeSource:

```bash
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo dnf install nodejs -y
```

Verify the install:

```bash
node --version
npm --version
```

## Install & Configure the Script

**1. Copy the script files to your server**

You need the following files in the same directory:

```
main.js
config.js
crapi.js
mailhog.js
user.js
helpers.js
package.json
```

**2. Install dependencies**

```bash
cd /path/to/script
npm install
```

You can safely ignore any warnings — they are geared toward web development and do not affect this script.

**3. Update config.js**

Edit `config.js` and replace the placeholder hostnames with your actual crAPI and Mailhog FQDNs:

```javascript
export default {
  crapi: 'https://YOUR_CRAPI_HOST',
  mailhog: 'https://YOUR_MAILHOG_HOST',
  vinRegex: /\b[(A-Z|0-9)]{17}\b/gm,
  pinRegex: />(\d{4})<\/font>/,
  usersToSimulate: parseInt(process.env.USERS_TO_SIMULATE ?? 100),
  batchSize: 10,
}
```

**4. (Optional) Download the required video file**

The script uploads a sample video for each user. Without it the video upload step will fail for every user, though the rest of the baseline will continue. To include it:

```bash
curl -L "https://file-examples.com/storage/fe48a63c7567b7a8626ada0/2017/04/file_example_MOV_480_700kB.mov" \
  -o file_example_MOV_480_700kB.mov
```

The file must be in the same directory as the script. If you don't want to use a video file, comment out these two lines in `main.js`:

```javascript
// const video = await crapi.setVideo(user)
// await crapi.changeVideoName(user, video.data.id, faker.system.commonFileName('mov'))
```

## Running the Script

**Standard run:**

```bash
node .
```

**First run mode** — also baselines four fixed accounts (Jane Doe, John Smith, crapi_user1, crapi_user2):

```bash
FIRST_RUN=true node .
```

**Control number of users:**

```bash
USERS_TO_SIMULATE=50 node .
```

**Both together:**

```bash
FIRST_RUN=true USERS_TO_SIMULATE=200 node .
```

## Running in the Background

The baseline takes 30-45 minutes for the default 100 users on a typical server. It is strongly recommended to run inside `tmux` so the script survives SSH disconnects.

```bash
# Start a new tmux session
tmux new -s baseline

# Run the script
node .

# Detach and leave running in background
# Press Ctrl+B, then D

# Reattach later to check progress
tmux attach -t baseline
```

## Notes

- Errors for individual users are caught and logged but will not stop the overall run — some failures are normal
- If you see `500 Server Error` on signup for all users, the crAPI database sequence is likely broken — restart crAPI with `docker compose down -v && docker compose up -d` to reset it
- Concurrency is controlled by `batchSize` in `config.js` (default: 10)
