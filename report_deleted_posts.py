import asyncpraw
import json
import asyncio
import os

# Coroutine to record every post submitted to the specified sub
async def save_posts(reddit, subreddit_name):
    print(f"Monitoring for new posts on r/{subreddit_name}")
    
    # Create directory for stroing the posts of the monitored subreddit 
    if not os.path.exists(subreddit_name):
        os.makedirs(subreddit_name)
    
    # Save each post to the directory so that we can retrieve the text later if the post is deleted
    try:
        subreddit = await reddit.subreddit(subreddit_name)
        async for post in subreddit.stream.submissions():
            await post.load()
            print(f"Found post on {subreddit_name}: {post.fullname}")
            file_name = f"{subreddit_name}/{post.fullname}.json"
            payload = {
                'title': post.title,
                'permalink': post.permalink,
                'body': post.selftext
            }
            if not os.path.exists(file_name):
                try:
                    print(f"Saving post {subreddit_name}:{post.fullname} to file")
                    with open(file_name, 'w') as json_file:
                        json.dump(payload, json_file)
                except:
                    print(f"Error saving post {subreddit_name}:{post.fullname} to file")
                    continue
    except Exception as e:
        print(str(e))

# Coroutine to check for deleted posts and notify mods 
async def check_deleted_posts(reddit, subreddit_name):
    print(f"Checking for deleted posts on r/{subreddit_name}")
    while True:
        await asyncio.sleep(10)

        # Get list of 100 most recent posts we previously saved
        try:
            recent_posts = [os.path.splitext(filename)[0] for filename in os.listdir(subreddit_name)]
            recent_posts = sorted(recent_posts, reverse=True)[:100]
        except: # Could fail if no posts were saved, in which case we do nothing
            continue
        
        # Get info on recent posts       
        try:
            async for post in reddit.info(recent_posts):

                # Check if any of the recent posts has been deleted
                if post.selftext in ['[deleted]']: # Add other languages??
                    print(f"Found deleted post on r/{subreddit_name}: {post.fullname})")

                    # Load original text from file
                    payload = {}
                    file_name = f"{subreddit_name}/{post.fullname}.json"
                    try:
                        with open(file_name, 'r') as json_file:
                            payload = json.load(json_file)
                    except:
                        
                        # Skip if error
                        print(f"Error loading file {file_name}. Skipping notification.")
                        continue

                    # Check if we already notified about this post
                    if payload.get('notified') is None:
                            
                        # Send modmail to the subreddit
                        modmail_subject = f"Deleted Post Notification for r/{subreddit_name}"
                        modmail_message = (
                            f"**Title:** {payload['title']}\n\n  "
                            f"**Link:** https://reddit.com{payload['permalink']}\n\n  "
                            f"**Original Text:** {payload['body']}"
                        )
                        try:
                            print(f"Sending modmail notification to r/{subreddit_name}")
                            subreddit = await(reddit.subreddit(subreddit_name))
                            await subreddit.message(modmail_subject, modmail_message)
                        except:
                            print('Error sending modmail notification')
                            continue

                        # Update the file to make sure we do not resend the notification
                        payload['notified'] = True
                        try:
                            with open(file_name, 'w') as json_file:
                                json.dump(payload, json_file)
                        except:
                            print(f"Error updating file {file_name}")
                    else:
                        print(f"Already notified about r/{subreddit_name}: {post.fullname}")
          
        except Exception as e:
            print(str(e))

# Main Event loop
async def main():
    SUBREDDITS = ['orangetheorytesting'] # Add the names of your monitored subreddits separated by commas
    tasks = []
    for subreddit in SUBREDDITS:
        tasks.append(save_posts(reddit, subreddit))
        tasks.append(check_deleted_posts(reddit, subreddit))
    await asyncio.gather(*tasks)

################
# MAIN PROGRAM #
################

# Initialize connection to Reddit
LOCAL_CONFIG_FILE='local_config.json'
with open(LOCAL_CONFIG_FILE) as local_config_file:
    local_config = json.load(local_config_file)
REDDIT_CLIENT_ID = local_config['reddit_client_id']
REDDIT_CLIENT_SECRET = local_config['reddit_client_secret']
REDDIT_USER_AGENT = local_config['reddit_user_agent']
REDDIT_USERNAME = local_config['reddit_username'],
REDDIT_PASSWORD = local_config['reddit_password']

reddit = asyncpraw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT,
    username=REDDIT_USERNAME,
    password=REDDIT_PASSWORD
)

# Initialize event loop
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())