import json
from datetime import datetime, tzinfo
from dateutil.tz import tzutc
import pandas as pd
import praw

# Retrieve settings and secrets
CONFIG_FILE='local_config.json'
with open(CONFIG_FILE) as config_file:
    config = json.load(config_file)
monitored_subreddit = config['monitored_subreddit']
reddit_username = config['reddit_username']
reddit_password = config['reddit_password']
reddit_user_agent = config['reddit_user_agent']
reddit_client_id = config['reddit_client_id']
reddit_client_secret = config['reddit_client_secret']

# Enter the range of blob datetime to retrieve
earliest_dt = datetime(2022, 7, 1, tzinfo=tzutc()) 
latest_dt = datetime(2022, 7, 31, tzinfo=tzutc())

# Generate Reddit post text in markdown format
post_title = f"Moderation Transparency Report for {latest_dt.strftime('%B %Y')}"
post_body_md = f"This report provides a summary of actions taken by the moderators of r/{monitored_subreddit.title()} during {latest_dt.strftime('%B %Y')}.\n"

# Initialize Reddit connection
with praw.Reddit(
    client_secret=reddit_client_secret,
    client_id=reddit_client_id,
    username=reddit_username,
    password=reddit_password,
    user_agent=reddit_user_agent
) as reddit:

    # Get modlog
    report_data = {}
    for item in reddit.subreddit(monitored_subreddit).mod.log(limit=None):
        item_created_dt = datetime.fromtimestamp(item.created_utc, tz=tzutc())
        if earliest_dt <= item_created_dt <= latest_dt:
            item_dict = report_data.get(item.target_fullname, {})
            if item.action == 'addremovalreason':
                item_dict['removal_reason'] = item.description
                report_data[item.target_fullname] = item_dict
            elif item.action in ['approvelink', 'approvecomment', 'removelink', 'removecomment']:
                if item_dict.get('type') is None:
                    item_dict['type'] = 'comment' if item.target_fullname.split('_')[0] == 't1' else 'post'
                    item_dict['mod_action'] = 'approve' if item.action.startswith('approve') else 'remove'
                    item_dict['date_time'] = item_created_dt.strftime('%Y/%m/%d')       
                    report_data[item.target_fullname] = item_dict
        
# Get results as DataFrame
print('Creating report...')
df_report = pd.DataFrame(report_data).transpose()
# df_report.to_csv(f"modlog_data_{earliest_dt.year}-{earliest_dt.month}.csv")

# Summarize mod action data
summary_data = pd.pivot_table(
    data=df_report,
    index=['type', 'mod_action'],
    values='date_time',
    aggfunc='count',
    fill_value=0    
)
# Summarize removal reason data
removal_reason_data = pd.pivot_table(
    data = df_report,
    index=['type', 'mod_action', 'removal_reason'],
    values='date_time',
    aggfunc='count',
    fill_value=0
)

# Add removal reason summary to the Reddit post
if 'post' in summary_data['date_time']:
    approved_posts = summary_data['date_time']['post'].get('approve', 0) + summary_data['date_time']['post'].get('chaos_mode', 0) 
    removed_posts = summary_data['date_time']['post'].get('remove', 0)
    total_posts = approved_posts + removed_posts
    post_body_md += (
        '## Post Removals\n'
        f"A total of **{total_posts}** posts were reviewed by the moderators, of which **{removed_posts}** " 
        f"({int(round(removed_posts / total_posts * 100, 0))}%) were removed for the following reasons:  \n"
    )
    for removal_reason, count in removal_reason_data['date_time']['post']['remove'].sort_values(ascending=False).items():
        post_body_md += f"- {removal_reason}: **{count}** ({int(round(count / removed_posts * 100, 0))}%)  \n"

if 'comment' in summary_data['date_time']:
    approved_comments = summary_data['date_time']['comment'].get('approve', 0) + summary_data['date_time']['comment'].get('chaos_mode', 0) 
    removed_comments = summary_data['date_time']['comment'].get('remove', 0)
    total_comments = approved_comments + removed_comments
    post_body_md += (
        '## Comment Removals\n'
        f"A total of **{total_comments}** comments were reported to the moderators by community users or by SplatBot, of which **{removed_comments}** " 
        f"({int(round(removed_comments / total_comments * 100, 0))}%) were removed for the following reasons:  \n"
    )
    for removal_reason, count in removal_reason_data['date_time']['comment']['remove'].sort_values(ascending=False).items():
        post_body_md += f"- {removal_reason}: **{count}** ({int(round(count / removed_comments * 100, 0))}%)  \n"


# Get information about bans
bans = []
for item in reddit.subreddit(monitored_subreddit).mod.log(action='banuser', limit=None):
    item_dt = datetime.fromtimestamp(item.created_utc, tz=tzutc())
    if earliest_dt <= item_dt <= latest_dt:
        bans.append({
            'timestamp': item.created_utc,
            'reason': item.description.split(':')[0],
            'duration': item.details
        })

if len(bans) > 0:
    # Clean up BotDefense ban reasons
    for ban in bans:
        if '/u/' in ban['reason']:
            ban['reason'] = 'Unauthorized bot'
    
    # Summarize and add to post
    df_bans = pd.DataFrame(bans)
    bans_summary_data = pd.pivot_table(
        data=df_bans,
        index=['reason'],
        columns=['duration'],
        values='timestamp',
        aggfunc='count',
        fill_value=0    
    )
    post_body_md += (
        '## Bans\n'
        f"A total of **{len(bans)}** bans were issued by the moderators. The table below breaks them down by reason and duration:  \n\n" 
    )
    """
    for ban_reason, count in bans_summary_data['timestamp'].sort_values(ascending=False).items():
        post_body_md += f"- {ban_reason}: **{count}** ({int(round(count / len(bans) * 100, 0))}%)  \n"
    """
    post_body_md += bans_summary_data.to_markdown() 


# Add closing statements
post_body_md += (
    '\n\n'
    'We hope you find this information useful and we welcome your feedback. '
    f"All reports are archived on our [wiki](https://www.reddit.com/r/{monitored_subreddit}/wiki/mod-transparency-reports).  \n\n"
    '-The Modsquad'
)

# Connect to Reddit
with praw.Reddit(
    client_secret=reddit_client_secret,
    client_id=reddit_client_id,
    username=reddit_username,
    password=reddit_password,
    user_agent=reddit_user_agent
) as reddit:

    # Post to Reddit
    print('Submitting post...')
    print(f"\n{post_body_md}")
    new_post = reddit.subreddit(monitored_subreddit).submit(title=post_title, selftext=post_body_md, flair_id='161cdb20-1a7d-11e8-affb-0e5c7ea2a678')
    new_post.mod.distinguish()
    print('... Done')

    # Update the wiki page
    print('Updating wiki...')
    WIKI_PAGE_NAME = 'mod-transparency-reports'
    wikipage = reddit.subreddit(monitored_subreddit).wiki[WIKI_PAGE_NAME]
    updated_content_md = wikipage.content_md + f"\n- [{latest_dt.strftime('%B %Y')}](https://reddit.com{new_post.permalink})"
    wikipage.edit(updated_content_md)
    print('... All done.')