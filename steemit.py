import requests

# Steem         : https://api.coinmarketcap.com/v1/ticker/steem/
# Steem-dollars : https://api.coinmarketcap.com/v1/ticker/steem-dollars/
# Bitcoin       : https://api.coinmarketcap.com/v1/ticker/bitcoin/

API = 'https://api.steemjs.com/'

def steemit_api(steemit_name):
    url = '{}get_state?path=@{}'.format(API, steemit_name)
    return requests.get(url).json()

def blog_list(steemit_name, number=10):
    posts = steemit_api(steemit_name)
    post = posts['content']
    result = {'result_blog': [steemit_name], 'result_url': []}
    for pk in posts['accounts'][steemit_api]['blog'][:number]:
        if post[pk]['category'] == 'utopian-io':
            result['result_blog'].append(pk)
            result['result_url'].append(post[pk]['url'])
            
    return result

def validate_user(steemit_name):
    url = 'https://steemit.com/@{}.json'.format(steemit_name)
    data = requests.get(url).json()['status']
    status = True
    if data == '200':
        status = False
    return status
    

def moderasyon(link):
    url = 'https://steemit.com{}.json'.format(link)
    data = requests.get(url).json()['post']
    cashout = data['cashout_time']
    data = data['json_metadata']
    if 'moderator' in data.keys():
        if data['moderator']['flagged']:
            vote, comment = False, False
        else:
            vote, comment = True, False
    else:
        vote, comment = True, True
    return vote, comment, cashout
    

def blog_post(blog_permalink):
    author, permalink = blog_permalink.split('/')
    return steemit_api(author)['content']

def votes_list(blog_permalink):
    blog_permalink = blog_permalink.split('/utopian-io/@')[1]
    author, permalink = blog_permalink.split('/')
    url = '{}get_active_votes?author={}&permlink={}'.format(API, author, permalink)
    return [voter['voter'] for voter in requests.get(url).json()]

def comment_list(blog_permalink):
    "Two lists are returned"
    author, permalink = blog_permalink.split('/')
    url = '{}get_content_replies?author={}&permlink={}'.format(API, author, permalink)
    comments = requests.get(url).json()
    comment_list = [comment['author'] for comment in comments]
    comment_body = [comment['body'] for comment in comments]

    return comment_list, comment_body

def mod_list():
    url = 'https://utopian.team/users/team.json'
    data = requests.get(url).json()['results']
    teams = [i for i in data]

    all_list = []
    for team in teams:
        for member in data[team]['members']:
            all_list.append(member['account'])

    return all_list + teams

def post_status():
    api = 'https://utopian.plus/unreviewedPosts.json'
    data = requests.get(api).json()
    pending = data['posts']['pending']
    return pending

def get_coin(coin):
    url = 'https://api.coinmarketcap.com/v1/ticker/{}'.format(coin)
    data = requests.get(url).json()[0]
    return data['price_usd']