from mordecai.mordecai import Geoparser
import collections

import utils

import base64
import datetime
import json
import os
import time

# Get the project ID and pubsub topic from the environment variables set in
# the 'bigquery-controller.yaml' manifest.
PROJECT_ID = os.environ['PROJECT_ID']
SUB_TOPIC = os.environ['SUB_TOPIC']
PUB_TOPIC = os.environ['PUB_TOPIC']
ES_HOST = os.environ['ELASTIC_HOST']
NUM_RETRIES = 3

def create_subscription(client, project_name, sub_name):
    """Creates a new subscription to a given topic."""
    print("using pubsub topic: %s" % SUB_TOPIC)
    name = utils.get_sub_path(client,project_name, sub_name)
    subscription = client.create_subscription(name, SUB_TOPIC )

    print('Subscription {} was created.'.format(subscription['name']))

def publish(client, pubsub_topic, data_lines):
    """Publish to the given pubsub topic."""
    resp = []
    for line in data_lines:
        pub = line.encode('utf-8')
        resp.append(client.publish(pubsub_topic, data=pub))
    return resp


def pull_messages(subscriber, project_name, sub_name):
    """Pulls messages from a given subscription."""
    BATCH_SIZE = 50
    tweets = []
    sub_path = utils.get_sub_path(subscriber, project_name, sub_name)
    try:
        resp = subscriber.pull(sub_path,max_messages=BATCH_SIZE)
    except Exception as e:
        print("Exception: %s" % e)
        time.sleep(0.5)
        return
    if resp.received_messages:
        ack_ids = []
        for r in resp.received_messages:
            if r.message:
                tweets.append(r.message.data.decode('utf-8'))
                ack_ids.append(r.ack_id)
            subscriber.acknowledge(sub_path, ack_ids)
    return tweets

def geo_cleanup(tweet):
    result = ""
    #Grabs Mordecai info and conencts to gazetter
    geo = Geoparser(es_hosts=[ES_HOST])
    #Combine user location and tweet test into one string for ananlysis
    loc_info = "{} {}".format(tweet['user']['location'],tweet['text'])
    #print(loc_info)
    # infer the location from the teext
    cntrys = collections.Counter()
    cntry = geo.infer_country(loc_info)
    #Take Country info and add bias/cleanup
    for c in cntry:
        if c['country_predicted'] == 'USA':
            result='USA'
        else:
             cntrys.update(c['country_predicted'])
    # USA bias if most_common or in array
    if result!='USA':
         if 'USA' in cntrys.most_common(1):
             result = "USA"
         elif 'USA' in cntrys:
             result="USA"
         else:
             if len(cntrys.most_common(1)) >0:
                result= cntrys.most_common(1)[0][0]
             else:
                 result = ""
    print("Cleaned! {} -> {}".format(tweet['user']['location'],result))
    tweet['user']['location']=result
    return tweet



def clean_geo(sub_client, pub_client, sub_name, sub_topic):
    """Write the data to BigQuery in small chunks."""
    tweets = []
    gtweets = []
    CHUNK = 50  # The size of the BigQuery insertion batch.
    # If no data on the subscription, the time to sleep in seconds
    # before checking again.
    WAIT = 2
    tweet = None
    count = 0
    count_max = 50000
    while count < count_max:
        while len(tweets) < CHUNK:
            twmessages = pull_messages(sub_client, PROJECT_ID, sub_name)
            if twmessages:
                for res in twmessages:
                    try:
                        tweet = json.loads(res)
                    except Exception as bqe:
                        print(bqe)
                    if 'delete' in tweet:
                        continue
                    if 'limit' in tweet:
                        continue
                    tweets.append(tweet)
                # Cleanup locations within tweets dict
                for t in tweets:
                    if not t['user']['location']:
                        gtweets.append(json.dumps(geo_cleanup(t)))
                    else:
                        gtweets.append(json.dumps(t))
                # Push cleaned up tweets back into PubSub-sub_topic for insert into bigquery
                response = publish(pub_client,sub_topic,gtweets)
            else:
                # pause before checking again
                print('sleeping...')
                time.sleep(WAIT)
        tweets = []
        count += 1
        if count % 25 == 0:
            print ("processing count: %s of %s at %s: %s" %
                   (count, count_max, datetime.datetime.now(), response))

if __name__ == '__main__':
    topic_info = PUB_TOPIC.split('/')
    topic_name = topic_info[-1]
    sub_name = "tweets_%s" % topic_name
    sub_topic = SUB_TOPIC
    print("starting pulling data to clean location")
    credentials = utils.get_credentials()
    pub_client = utils.create_pubsub_client(credentials,'pub')
    sub_client = utils.create_pubsub_client(credentials, 'sub')
#    try:
        # TODO: check if subscription exists first
#        subscription = create_subscription(pubsub, PROJECT_ID, sub_name)
#    except Exception as e:
#        print(e)
    clean_geo(sub_client, pub_client, sub_name, sub_topic)
    print('exited write loop')