"""

This script will monitors the specified subs for deleted posts.
If a deleted post is found, it will send modmail to the sub from which the post was deleted with details about the deleted post, 
including the original text of the post.

"""

import asyncpraw
import json
import asyncio
import os

#################################################################
# Coroutine to record every post submitted to the specified sub #
#################################################################
async def save_posts(reddit, subreddit_name):
    print(f"Monitoring for new posts on [r/{subreddit_name}]")
    
    # Create directory for stroing the posts of the monitored subreddit 
    if not os.path.exists(subreddit_name):
        os.makedirs(subreddit_name)
    
    while True:

        try:
            
            # Save each post to the directory so that we can retrieve the text later if the post is deleted
            subreddit = await reddit.subreddit(subreddit_name)
            async for post in subreddit.stream.submissions():
                await post.load()
                print(f"Found post: [r/{subreddit_name}]: [{post.fullname}]")
                file_name = f"{subreddit_name}/{post.fullname}.json"
                payload = {
                    'title': post.title,
                    'author': post.author.name,
                    'permalink': post.permalink,
                    'body': post.selftext
                }
                
                # If a file named with the post id already exists, we don't want to overwrite!
                if not os.path.exists(file_name):
                    try:
                        print(f"Saving post: [r/{subreddit_name}]: [{post.fullname}]")
                        with open(file_name, 'w') as json_file:
                            json.dump(payload, json_file)
                    
                    except:
                        
                        # If there was an error saving the file, report it and move on.
                        print(f"Error saving post: [r/{subreddit_name}]: [{post.fullname}]")
                        continue

        except Exception as e:
            
            # Exceptions can occur because calls to Reddit fail, Reddit has an outage, etc. We just report them and try again.
            print(str(e))


########################################################
# Coroutine to check for deleted posts and notify mods #
########################################################
async def check_deleted_posts(reddit, subreddit_name):
    print(f"Checking for deleted posts on [r/{subreddit_name}]")
    while True:
        
        # We only need to have this coroutine executed periodically, so we sleep for one minute. 
        await asyncio.sleep(60) # Feel free to replace 60 with the number of seconds that work for you

        # Get list of 100 most recent posts we previously saved
        try:
            recent_posts = [os.path.splitext(filename)[0] for filename in os.listdir(subreddit_name)]
            
            # Note: the current method for sorting the list by latest post relies on the post id name (also the filename). Hopefully this is reliable enough.
            recent_posts = sorted(recent_posts, reverse=True)[:100]

        except: # Could fail if no posts were saved, in which case we do nothing and retry
            continue
        
        # Get info on recent posts       
        try:
            async for post in reddit.info(recent_posts):

                # Check if any of the recent posts has been deleted
                if post.selftext in ['[deleted]']: # Add other languages??
                    print(f"Found deleted post: [r/{subreddit_name}]: [{post.fullname})]")

                    # Load original text from file
                    payload = {}
                    file_name = f"{subreddit_name}/{post.fullname}.json"
                    try:
                        with open(file_name, 'r') as json_file:
                            payload = json.load(json_file)
                    except:
                        
                        # Skip if error
                        print(f"Error loading file: [{file_name}]. Skipping notification.")
                        continue

                    # Check if we already notified about this post
                    if payload.get('notified') is None:
                            
                        # Send modmail to the subreddit
                        modmail_subject = f"Deleted Post Notification for r/{subreddit_name}"
                        modmail_message = (
                            f"**Title:** {payload['title']}\n\n  "
                            f"**Author:** {payload['author']}\n\n  "
                            f"**Link:** https://reddit.com{payload['permalink']}\n\n  "
                            f"**Original Text:** {payload['body']}"
                        )
                        try:
                            print(f"Sending modmail notification to [r/{subreddit_name}]")
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
                            print(f"Error updating file: [{file_name}]")
                    
                    else:
                        # If we already notified about the file, no need to send modmail again
                        print(f"Already notified about post: [r/{subreddit_name}]: [{post.fullname}]")
          
        except Exception as e:
            print(str(e))


###################
# Main Event loop #
###################
async def main():
    SUBREDDITS = ['modguide'] # Add the names of your monitored subreddits in this list
    
    # For each specified subreddit, create tasks for saving posts and checking for deleted posts
    tasks = []
    for subreddit in SUBREDDITS:
        tasks.append(save_posts(reddit, subreddit))
        tasks.append(check_deleted_posts(reddit, subreddit))

    # Run all the tasks and hope for the best
    await asyncio.gather(*tasks)


################
# MAIN PROGRAM #
################

# Initialize connection to Reddit
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

# Initialize the asyncpraw Reddit instance
reddit = asyncpraw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT,
    username=REDDIT_USERNAME,
    password=REDDIT_PASSWORD
)

# Initialize the event loop
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())