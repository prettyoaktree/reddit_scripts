"""
Use this program to generate refresh tokens that our bot will need to use
Best to run this locally because it is only needed when you initially set up the bot
"""

from flask import Flask, request
import praw
from bot_logger import get_bot_logger
import json
from random import randint
import sys

application = Flask(__name__)
app = application

#######################################################################################
# This API endpoint is used to request a Reddit refresh token for a mod using the bot #
#######################################################################################
@app.route('/api/authorize', methods=['GET'])
def authorize_bot():
    
    REDDIT_OAUTH_SCOPES = ['read', 'wikiread', 'wikiedit']  # List of scopes: https://praw.readthedocs.io/en/stable/tutorials/refresh_token.html
    scopes = REDDIT_OAUTH_SCOPES 

    # Call Reddit to authorize the bot
    logger.info('Generating auth url')
    prawddit = praw.Reddit(
        redirect_uri=APP_REDIRECT_URI,
        user_agent=APP_USER_AGENT,
        client_id=APP_CLIENT_ID,
        client_secret=APP_CLIENT_SECRET

    )
    state = APP_AUTH_STATE
    url = prawddit.auth.url(duration="permanent", scopes=scopes, state=state)
    logger.info(f"Auth url: {url}")

    # Display instructions and auth link
    page_html = (
        '<h1>Bot Authorization</h1>'
        '<p>Click the link below to go to Reddit and authorize the bot to access your account.</p>'
        f'<p><a href={url}>Click here!</a></p>'
    )
    return page_html

##########################################################################################################
# This endpoint receives a refresh token from Reddit when the app is authorized and shows it to the user #
##########################################################################################################
@app.route('/api/token', methods=['GET'])
def receive_token():
    logger.info('Received token request')
    
    # If the request is valid, display the auth token to the user
    error_getting_token = False
    if request.args.get('state') == APP_AUTH_STATE:
        logger.info('Request is valid')        
        
        # Get refresh token from Reddit
        logger.info('Getting refresh token from Reddit')
        prawddit = praw.Reddit(
            redirect_uri=APP_REDIRECT_URI,
            user_agent=APP_USER_AGENT,
            client_id=APP_CLIENT_ID,
            client_secret=APP_CLIENT_SECRET
        )
        try:
            refresh_token = prawddit.auth.authorize(request.args.get('code'))       
            page_html = (
                '<h1>Success!</h1>'
                f"<p>Your referesh token is {refresh_token}</p>"
            )
        except Exception as e:
            logger.error(str(e))
            error_getting_token = True
    else:
        logger.info('Bad request state')
        error_getting_token = True
    
    # If there was an error, construct error message
    if error_getting_token:
        logger.info(f"Bad request with error [{request.args.get('error')}]")
        page_html = (
            '<h1>This Did Not Work!</h1>'
            f"<p>Reddit returned the following error message: {request.args.get('error')}</p>"
            f"<p>If you want to try again, <a href={APP_REDIRECT_URI}/api/authorize>click here</a>.</p>"
        )

    return page_html 

################
# Main program #
################

# Set up logging
logger = get_bot_logger()
logger.info('Python version is %s.%s.%s' % sys.version_info[:3])
logger.info('Initializing api endpoints')

# Retrieve settings and secrets from a local_config.json file (make sure to add this file to .gitignore)
CONFIG_FILE='local_config.json'
with open(CONFIG_FILE) as config_file:
    config = json.load(config_file)
logger.info('Loading environment variables from config file') 
APP_CLIENT_ID = config['app_client_id']
APP_CLIENT_SECRET = config['app_client_secret']
APP_REDIRECT_URI = config['app_redirect_uri']
APP_USER_AGENT = config['app_user_agent']

# Generate random number to be used for verifying auth requests
APP_AUTH_STATE = str(randint(1, 65000))

# Start flask and wait for user to hit any of the endpoints
logger.info('Starting Flask')
logger.info('Ready to receive api requests!')
if __name__ == "__main__":
    app.run(port=5555)