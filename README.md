# Infrastructure fault reporting bot deployment
Deployment branch for Infrastructure-reporting-bot

This branch contains some modifications to ```run.py``` and additional files to support deployment in Replit

For the documentation of original files please refer to ```infrastructure-fault-reporting``` branch

For the documentation additional files please refer to the respective files in this branch

## Additional files
- ReplitPersistence.py

3rd party persistence class customised for storing data on Replit key storage database

- webserver.py

Flask webserver to host the Telegram bot together with a website. This is to enable uptimerobot to ping the website to keep the Telegram bot alive