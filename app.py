import datetime
import logging
import urllib
import requests
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from server import Telegram_User, Control, db
import steemit
from sqlalchemy import or_

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def message_push(text, chat_id):
    TOKEN = 'KEY'
    URL = "https://api.telegram.org/bot{}/".format(TOKEN)
    text = urllib.parse.quote_plus(text)
    url = URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown&disable_web_page_preview=True".format(text, chat_id)
    response = requests.get(url)
    content = response.content.decode("utf8")
    return content


def register(bot, update):
    #import ipdb; ipdb.set_trace()
    client_id = update.to_dict()['message']['from']['id']
    steem_name = update.to_dict()['message']['text'].replace(' ','').split('/register')[1]

    if Telegram_User().get_users(client_id):
        update.message.reply_text('Registration already exists.')
        return
    if steemit.validate_user(steem_name):
        update.message.reply_text('There is a problem. User name validation? Try again')        
        return
    try:
        #import ipdb; ipdb.set_trace()
        telegram_user = Telegram_User()
        telegram_user.client_id = client_id
        telegram_user.steem_name = steem_name
        telegram_user.activite = False
        db.session.add(telegram_user)
        db.session.commit()
        update.message.reply_text('Registration is complete.')
    except:
        update.message.reply_text('There is a problem. User name validation? Try again')        

def utopian(bot, update):
    client_id = update.to_dict()['message']['from']['id']
    user = Telegram_User().get_users(client_id)
    if not user:
        update.message.reply_text('You need to register first. `/register steemitname` !')
        return 
    if user.activite:
        update.message.reply_text('You may be forbidden. @tolgahanuzun your communication!')
        return        
    try:
        count = 0
        steem_name = user.steem_name
        blog_dic = steemit.blog_list(steem_name)
        blog_url = blog_dic['result_url']
        name_list = []
        for blog_ in blog_url:
            if not Control().get_blog(blog_):
                votes_status, commen_status, cashout = steemit.moderasyon(blog_)
                if commen_status or votes_status:
                    if not commen_status:
                        if 'utopian-io' in steemit.votes_list(blog_):
                            votes_status = False
                        else:
                            votes_status = True
                    if votes_status or commen_status:
                        post_control = Control()
                        post_control.telegram_user = user
                        post_control.post = blog_ 
                        post_control.is_vote = votes_status
                        post_control.is_comment = commen_status
                        post_control.start_date = datetime.datetime.utcnow()
                        post_control.end_date = datetime.datetime.strptime(cashout, '%Y-%m-%dT%H:%M:%S')
                        db.session.add(post_control)
                        db.session.commit()
                        count = count+1
                        name_list.append(blog_)
                    else:
                        pass
        text = 'Task for {} articles was created.\n'.format(count)
        name_text = ''
        for name in name_list:
            name_text =  name_text + '\n----\n' + name  
        update.message.reply_text(text + name_text)
    except:
        update.message.reply_text('Something went wrong, try again or report..!')  



def help(bot, update):
    text = '''
Hello Dear! There are 2 commands available.. Example
/register username
/utopian
    '''
    update.message.reply_text(text)

def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def control():
    check_lists = Control.query.filter(or_(Control.is_vote == True, Control.is_vote == True)).all()
    for check_list in check_lists:
        votes_status, commen_status, cashout = steemit.moderasyon(check_list.post)

        if check_list.is_comment:
            if votes_status or commen_status:
                if not commen_status:
                    text = 'It approved by moderators.. Check it out.\n--\nhttps://steemit.com{}'.format(check_list.post)
                    message_push(text, check_list.telegram_user.client_id)
                    check_list.is_comment = False
                    db.session.add(check_list)
                    db.session.commit()
            else:
                text = 'This post has been rejected.. Check it out.\n--\nhttps://steemit.com{}'.format(check_list.post)
                message_push(text, check_list.telegram_user.client_id)
                check_list.is_comment = False
                check_list.is_vote = False
                db.session.add(check_list)
                db.session.commit()
        
        if check_list.is_vote:
            if 'utopian-io' in steemit.votes_list(check_list.post):
                votes_result = False
                text = 'utopian-io voteup.. Check it out.\n--\nhttps://steemit.com{}'.format(check_list.post)
                message_push(text, check_list.telegram_user.client_id)
                check_list.is_vote =  votes_result
                db.session.add(check_list)
                db.session.commit()

        # datetime.datetime.utcnow() > check_list.end_date
        #import ipdb; ipdb.set_trace()
       
        remove_lists = Control.query.filter(Control.is_vote == False, Control.is_vote == False).all()
        for remove in remove_lists:
            db.session.delete(remove)
            db.session.commit()


def main():
    """Start the bot."""
    # Create the EventHandler and pass it your bot's token.
    updater = Updater('KEY')
    j = updater.job_queue

    def callback_minute(bot, job):
        logger.warning('Start')
        control()
        logger.warning('End')


    job_minute = j.run_repeating(callback_minute, interval=60, first=0)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("register", register))
    dp.add_handler(CommandHandler("utopian", utopian))
    dp.add_handler(CommandHandler("help", help))


    dp.add_error_handler(error)
    updater.start_polling()
    updater.idle()
    


if __name__ == '__main__':
    main()
