#!/usr/bin/env python3
import sqlite3
import time
import praw
import requests
from retrying import retry
import raven
from systemd import journal


client = raven.Client(
    dsn='',

    include_paths=[__name__.split('.', 1)[0]],
)


reply_template = '''
[MIRROR: {0}](https://streamable.com/{1})


Credit to {2} for the content.

-----------------------------
^(I am a bot. |) [^feedback](https://discord.gg/N8AN9NW)
''' 

#@retry(wait_fixed=600000, stop_max_attempt_number=6)
def main():
    global cur
    global sql
    sql = sqlite3.connect('replyposts.db')
    journal.send('loaded SQL database', SYSLOG_IDENTIFIER='reddit-bot' )
    print('Loaded SQL Database')
    cur = sql.cursor()

    cur.execute('CREATE TABLE IF NOT EXISTS oldsubmissions(ID TEXT)')
    cur.execute('CREATE INDEX IF NOT EXISTS oldsubmissions_index ON oldsubmissions(id)')
    print('Loaded Completed table')
    

    sql.commit()
    
    print('logging in....')
    journal.send('logging in', SYSLOG_IDENTIFIER='reddit-bot' )
    reddit = praw.Reddit(client_id='',
                         client_secret='',
                         password='',
                         user_agent='mirrorbot V1.0.1 by /u/powerjaxx',
                         username='')

    print('retreiving subreddit....')
    journal.send('retreiving subreddit', SYSLOG_IDENTIFIER='reddit-bot' )
    subreddit = reddit.subreddit('')
    for submission in subreddit.stream.submissions():
        process_submission(submission)

def streamable(clip_url, submission):
    api_url = 'https://api.streamable.com/import'
    payload = {'url': clip_url}
    headers = {'User-Agent': 'A bot that creates mirrors of Twitch clips'}
    global shortcode
    r = requests.get(api_url, params=payload, auth=('', ''), headers=headers)
    print(r.status_code)
    if r.status_code == 200:
        json = r.json()
        shortcode = json['shortcode']
        clipinfo(clip_url)
        reply_text = reply_template.format(title_clip, shortcode, broadcaster_url)
        reply = submission.reply(reply_text)
        reply.mod.distinguish(sticky=True)
    else:
        pass

def clipinfo(clip_url):
    global broadcaster_url
    global title_clip
    #global vod_link
    headers = {'Accept': 'application/vnd.twitchtv.v5+json', 'Client-ID': ''}
    if clip_url.startswith('https://clips.twitch.tv'):
        url_end = clip_url[24:]
        print(url_end)
    else:
        pass
    api_url = 'https://api.twitch.tv/kraken/clips/{0}'.format(url_end)
    r = requests.get(api_url, headers=headers)
    json = r.json()
    broadcaster_url = json["broadcaster"]["channel_url"]
    title_clip = json["title"]
    #vod_link = json["vod"]["url"]



def process_submission(submission):
    clip_url = submission.url
    sid = submission.id
    cur.execute('SELECT * FROM oldsubmissions WHERE ID=?', [sid])
    if cur.fetchone() is None:
        if clip_url.startswith('https://clips.twitch.tv'):
            streamable(clip_url, submission)
            cur.execute('INSERT INTO oldsubmissions VALUES(?)', [sid])
            sql.commit()
            print('Added id {0} to database'.format(sid))
            journal.send('added id {0} to database', SYSLOG_IDENTIFIER='reddit-bot'.format(sid))
            #not really needed
            time.sleep(600)
    else:
        pass

if __name__ == '__main__':
    main()
    
