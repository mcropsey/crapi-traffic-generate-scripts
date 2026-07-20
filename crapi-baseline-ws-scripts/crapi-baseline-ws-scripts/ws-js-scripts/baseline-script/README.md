# crAPI Baseline Script

This script provides a simple way to baseline the crAPI environment. While the baselining is not exhaustive, it does provide enough traffic to generate a model with a high enough accuracy for usage with the educational exercise. **This script is intended to be used after the Noname platform has been installed, and the crAPI taffic has been integrated and the integration has been validated.**

By default, this script simulates (using Faker) 3,000 users (50 user concurrency) which takes approximately 30-45 minutes on a `t3.small`.

## Install & Execution

1. Ensure machine running script has node and npm installed
2. Download baseline script to machine you will be running script from
3. Change directoy to baseline script folder
4. Run `npm install` to install `node_modules`. You can ignore any warnings as warnings are geared for web development
5. Modify `config.js`, replacing `CRAPI_HOST` with the FQDN for crAPI and `MAILHOG_HOST` with the FQDN for mailhog.
6. If necessary, tweak `usersToSimulate`.
6. Run baseline script: `node .`