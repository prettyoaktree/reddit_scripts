from ics import Calendar
import requests
from datetime import datetime, timedelta
import arrow
import praw
import json

def get_calendar_events(ical_url: str, num_days: int, footer_md='') -> str: 
    """
    Returns a markdown-formatted string of upcoming events from the provided ical calendar

    Parameters
    ----------
    ical_url : str
        The url of your ical calendar, e.g. "https://calendar.google.com/calendar/ical/youraccount/public/basic.ics"
    num_days : int
        The number of days, starting today, for which to retrieve upcoming events
    footer : str (optional)
        A footer markdown-formatted string to add after the list of events
    """    
    # Get data from the ics calendar
    data = requests.get(ical_url)
    cal = Calendar(data.text)
    
    # Create a markdown document of upcoming events
    start = arrow.get(datetime.utcnow())
    stop = arrow.get(start + timedelta(days=num_days))
    upcoming_events_md = ''
    for event in cal.timeline.included(start, stop):
        upcoming_events_md += f"{event.begin.format(fmt='MMMM Do')}  \n**{event.name}**\n\n---\n\n"

    # Add footer text if any
    upcoming_events_md += footer_md
    
    # Return markdown
    return upcoming_events_md

################
# MAIN PROGRAM #
################
# This code assumes that all the secrets are in a json file located in the same directory as this script.
# You can just enter these secrets here, but keep in mind that they are called "secrets" for a reason.
LOCAL_CONFIG_FILE='local_config.json'
with open(LOCAL_CONFIG_FILE) as local_config_file:
    local_config = json.load(local_config_file)
REDDIT_CLIENT_ID = local_config['reddit_client_id']
REDDIT_CLIENT_SECRET = local_config['reddit_client_secret']
REDDIT_USER_AGENT = local_config['reddit_user_agent']
REDDIT_USERNAME = local_config['reddit_username'],
REDDIT_PASSWORD = local_config['reddit_password']

# Create the text for the calendar widget
ICAL_URL = 'https://calendar.google.com/calendar/ical/otfreddit%40gmail.com/public/basic.ics' # replace with your ics link
md = get_calendar_events(ICAL_URL, 30)

# Connect to Reddit and update the widget
SUBREDDIT_NAME = 'orangetheory' # replace with your subreddit name (do not include r/)
WIDGET_TITLE = 'Upcoming Events' # Create a textarea widget in your subreddit "community appearance" section and provide the title here
with praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT,
    username=REDDIT_USERNAME,
    password=REDDIT_PASSWORD
) as prawddit:
    widgets = prawddit.subreddit(SUBREDDIT_NAME).widgets
    calendar_widget = None
    for widget in widgets.sidebar:
        if widget.shortName.lower() == WIDGET_TITLE.lower():
            calendar_widget = widget
            break

    calendar_widget.mod.update(text=md)        

