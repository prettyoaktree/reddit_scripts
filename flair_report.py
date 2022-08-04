import praw
import json
import sys
from datetime import datetime

LOCAL_CONFIG_FILE='bot_config.json'
with open(LOCAL_CONFIG_FILE) as local_config_file:
    local_config = json.load(local_config_file)
APP_CLIENT_ID = local_config['app_client_id']
APP_CLIENT_SECRET = local_config['app_client_secret']
APP_USER_AGENT = local_config['app_user_agent']
APP_TOKEN = local_config['app_token']
SUBREDDIT_NAME = local_config['subreddit_name']
POST_LIMIT = local_config['post_limit']
WIKI_PAGE = local_config['wiki_page']

flair_counter = {}

# Get input
while True:
    try:
        year_month = input('Enter the month to collect data for using the format YYYY-MM (e.g. 2022-07): ')
        year = int(year_month.split('-')[0] or 0)
        month = int(year_month.split('-')[1] or 0)
    except:
        year = 0
        month = 0
    if not (1 <= month <= 12) or year < 2000:
        print('Invalid input. Try again.')
    else:
        break

# Connect to Reddit
with praw.Reddit(
    client_id = APP_CLIENT_ID,
    client_secret = APP_CLIENT_SECRET,
    user_agent = APP_USER_AGENT,
    refresh_token = APP_TOKEN
) as prawddit:

    # Iterate through posts and count by flair
    print(f"Checking for posts in r/{SUBREDDIT_NAME} matching the specified timeframe...")
    for post in prawddit.subreddit(SUBREDDIT_NAME).new(limit=POST_LIMIT):
        if datetime.fromtimestamp(post.created_utc).month == month and datetime.fromtimestamp(post.created_utc).year == year:
            print('*', end='')
            if flair_counter.get(post.link_flair_text, None) is None:
                flair_counter[post.link_flair_text] = 1
            else:
                flair_counter[post.link_flair_text] += 1
        else:
            print('.', end='')
    
if len(flair_counter) == 0:
    print('\nNo posts found for this time frame!')
    sys.exit()
else:
    print(f"\nFound {sum(flair_counter.values())} posts")

sorted_counter = dict(sorted(flair_counter.items(), key=lambda item: item[1], reverse=True))

# Prepare report
print('Generating report...', end='')
report_md = (
    f"# Posts by flair for {datetime(year=datetime.utcnow().year, month=month, day=1).strftime('%B, %Y')}\n"
    f"**Total posts**: {sum(sorted_counter.values())}  \n\n"
    '| **Flair** | **Posts** |\n'
    '|:--|:--:|\n'
)
for flair, count in sorted_counter.items():
    report_md += f"|{flair}|{count}|\n"
print(' Done\n')

# Prompt for update mode
print(f"About to update wiki page r/{SUBREDDIT_NAME}/wiki/{WIKI_PAGE}...")
while True:
    update = input('Enter [y] to overwrite page, [n] to update existing page, [q] to quit without updating: ')
    if update.lower() == 'y':
        overwrite = True
        break
    elif update.lower() == 'n':
        overwrite = False
        break
    elif update.lower() == 'q':
        print('Bye!')
        sys.exit()
    else:
        print('Invalid input. Try again.')

# Update the wiki page
with praw.Reddit(
    client_id = APP_CLIENT_ID,
    client_secret = APP_CLIENT_SECRET,
    user_agent = APP_USER_AGENT,
    refresh_token = APP_TOKEN
) as prawddit:
    wiki_page = prawddit.subreddit(SUBREDDIT_NAME).wiki[WIKI_PAGE]
    try:
        wiki_page_content = wiki_page.content_md
    except:
        print("Wiki page does not exist")
        overwrite = True
    if overwrite:
        print(f"Creating / overwriting wiki page r/{SUBREDDIT_NAME}/wiki/{WIKI_PAGE}")
        wiki_page_content = report_md
    else:
        print(f"Updating wiki page r/{SUBREDDIT_NAME}/wiki/{WIKI_PAGE}")
        wiki_page_content = report_md + '\n---\n' + wiki_page_content
    try:
        wiki_page.edit(content=wiki_page_content)
    except Exception as e:
        print(f"Error updating wiki page: {str(e)}")

print('All done.')
