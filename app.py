import datetime
import logging
import urllib
import requests
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

from server import Telegram_User, Control, Price_task, db
import steemit
from sqlalchemy import or_

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)



def message_push(text, chat_id):
    TOKEN = '535189587:AAEj7ebECt8MC9oVsjY1_XUz1QOWFfKqncc'
    URL = "https://api.telegram.org/bot{}/".format(TOKEN)
    text = urllib.parse.quote_plus(text)
    url = URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown&disable_web_page_preview=True".format(text, chat_id)
    response = requests.get(url)
    content = response.content.decode("utf8")
    return content


def register(bot, update):
    client_id = update.to_dict()['message']['from']['id']
    steem_name = update.to_dict()['message']['text'].replace(' ','').split('/register')[1]

    if Telegram_User().get_users(client_id):
        update.message.reply_text('Registration already exists.')
        return
    if steemit.validate_user(steem_name):
        update.message.reply_text('There is a problem. User name validation? Try again')        
        return
    try:
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

def utopianqa(bot, update):
    client_id = update.to_dict()['message']['from']['id']
    user = Telegram_User().get_users(client_id)
    if not user:
        update.message.reply_text('You need to register first. `/register steemitname` !')
        return 
    if user.activite:
        update.message.reply_text('You may be forbidden. @tolgahanuzun your communication!')
        return

    check_post = update.to_dict()['message']['text'].split('/utopianqa ')[1]
    if 'steemit.com' in check_post:
        check_post = check_post.split('steemit.com')[1]
    elif 'utopian.io':
        check_post = check_post.split('utopian.io')[1]        

    text = steemit.questions_details(check_post)
    message_push(text, client_id)

def other_account(bot, update):
    client_id = update.to_dict()['message']['from']['id']
    steem_name = update.to_dict()['message']['text'].split('/other ')[1]    
    json_user = steemit.get_user(steem_name).json()

    if not json_user:
        update.message.reply_text('There is a problem. User name validation? Try again')
        return

    text = "Name: {} \n".format(steem_name)
    text = text + "Voting Power : {}\n".format(steemit.get_vp_rp(steem_name)[0])
    text = text + "Reputation     : {}\n".format(steemit.get_vp_rp(steem_name)[1])
    text = text + "Total Balance : {} SBD\n".format(steemit.balance(steem_name))
    text = text + "Followers Count : {}\n".format(json_user[0]['followers_count'])
    text = text +  "Following Count : {}\n".format(json_user[0]['following_count'])

    message_push(text, client_id)


def help(bot, update):
    text = '''
Hello Dear! There are 7 commands available.. Example
/register username
/utopian
/pending
/price
/price_task 4.56
/price_destroy
/me
    '''
    update.message.reply_text(text)

def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def control():
    check_lists = Control.query.filter(or_(Control.is_vote == True, Control.is_comment == True)).all()
    for check_list in check_lists:
        #import ipdb; ipdb.set_trace()
        votes_status, commen_status, cashout = steemit.moderasyon(check_list.post)
        
        if check_list.is_comment:
            if votes_status or commen_status:
                if not commen_status:
                    text = 'It approved by moderators.. Check it out.\n--\nhttps://steemit.com{}'.format(check_list.post)
                    message_push(text, check_list.telegram_user.client_id)
                    text = steemit.questions_details(check_list.post)
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

       
        remove_lists = Control.query.filter(Control.is_vote == False, Control.is_vote == False).all()
        for remove in remove_lists:
            db.session.delete(remove)
            db.session.commit()

def price_control():
    task_list = Price_task.query.all()
    for task in task_list:
        now_price = float(steemit.get_coin('steem-dollars'))
        if  now_price >= task.price_task:
            text = 'Task completed. SBD, its current rate: ${}'.format(now_price)
            message_push(text, task.telegram_user.client_id)
            db.session.delete(task)
            db.session.commit()


def pending_post(bot, update):
    try:
        categories = pending['categories']
    except :
        text = 'No service data. The Utopian API may have changed.'
        update.message.reply_text(text)
        return
    text = """
Pending Post: {}
Development: {}
Bug hunting: {} 
Documentation: {}
Translations: {}
Analysis: {}
Ideas: {}
Graphics: {}
Tutorials: {}
Video_tutorials: {}
Blog: {}
Sub_projects: {}
Tasks: {}
Visibility: {}
Copywriting: {}
""".format(
pending['_total'], categories['development'], categories['bug_hunting'], categories['documentation'],
categories['translations'], categories['analysis'], categories['ideas'], categories['graphics'],
categories['tutorials'], categories['video_tutorials'], categories['blog'], categories['sub_projects'],
categories['tasks'], categories['visibility'], categories['copywriting'])
    update.message.reply_text(text)

def price_all(bot, update):
    coin_name = update.to_dict()['message']['text'].split('/price ')
    if len(coin_name) > 1:
        try:
            coin_price_btc = steemit.get_coin(coin_name[1])
            update.message.reply_text('{} : {} $'.format(coin_name[1].title(), coin_price_btc))            
        except:
            update.message.reply_text('There is a problem. Coin name validation? Try again')
        return

    choose = ['steem', 'steem-dollars', 'bitcoin']
    text  = "Steem : $ {}\nSDB : $ {}\nBitcoin : $ {}".format(steemit.get_coin(choose[0]), steemit.get_coin(choose[1]) ,steemit.get_coin(choose[2]))
    update.message.reply_text(text)

def price_task(bot, update):
    client_id = update.to_dict()['message']['from']['id']
    price = update.to_dict()['message']['text'].replace(' ','').split('/price_task')[1]
    
    user = Telegram_User().get_users(client_id)
    if not user:
        update.message.reply_text('You need to register first. `/register steemitname` !')
        return 
    try:
        price = float(price)
    except:
        update.message.reply_text('Please enter a numeric: (for example: /price_task 4.56 )')
        return

    price_status = Price_task().get_task(user)

    if price_status:
        update.message.reply_text('You can only create one task.')
        return

    create_task = Price_task()
    create_task.telegram_user = user
    create_task.price_task = price
    db.session.add(create_task)
    db.session.commit()
    update.message.reply_text('Task created.')

def price_destroy(bot, update):
    client_id = update.to_dict()['message']['from']['id']
    user = Telegram_User().get_users(client_id)

    if not user:
        update.message.reply_text('You need to register first. `/register steemitname` !')
        return 

    price_status = Price_task().get_task(user)

    if price_status:
        db.session.delete(price_status)
        db.session.commit()
        update.message.reply_text('The task was destroyed.')

def profile_me(bot, update):
    keyboard = [
        [telegram.InlineKeyboardButton("My Profile", callback_data='1')],
        [telegram.InlineKeyboardButton("Steemit", callback_data=2)],
        [telegram.InlineKeyboardButton("Rocks", callback_data=3)],
        [telegram.InlineKeyboardButton("Steemd", callback_data='4')]
        ]

    reply_markup = telegram.InlineKeyboardMarkup(keyboard)

    update.message.reply_text('Please choose:', reply_markup=reply_markup)

def button(bot, update):
    query = update.callback_query

    bot.edit_message_text(text="Selected option: %s" % query.data,
                          chat_id=query.message.chat_id,
                          message_id=query.message.message_id)
    steem_name = Telegram_User().get_users(query.message.chat_id).steem_name

    if int(query.data) == 1:
        json_user = steemit.get_user(steem_name).json()
        text = "Name: {} \n".format(steem_name)
        text = text + "Voting Power : {}\n".format(steemit.get_vp_rp(steem_name)[0])
        text = text + "Reputation     : {}\n".format(steemit.get_vp_rp(steem_name)[1])
        text = text + "Total Balance : {} SBD\n".format(steemit.balance(steem_name))
        text = text + "Followers Count : {}\n".format(json_user[0]['followers_count'])
        text = text +  "Following Count : {}\n".format(json_user[0]['following_count'])
    elif int(query.data) == 2:
        text = "https://steemit.com/@{}".format(steem_name)
    elif int(query.data) == 3:
        text = "https://steem.rocks/@{}".format(steem_name)
    elif int(query.data) == 4:
        text = "https://steemd.com/@{}".format(steem_name)
    bot.send_message(query.message.chat_id, text)

def main():
    """Start the bot."""
    # Create the EventHandler and pass it your bot's token.
    updater = Updater('535189587:AAEj7ebECt8MC9oVsjY1_XUz1QOWFfKqncc')
    approved_controll = updater.job_queue
    pending_data = updater.job_queue
    price_tast_control = updater.job_queue

    def callback_minute(bot, job):
        logger.warning('Start')
        control()
        logger.warning('End')

    def peding_controll(bot, job):
        global pending
        pending = steemit.post_status()

    def price_controler(bot, job):
        price_control()


    approved_controll.run_repeating(callback_minute, interval=60, first=0)
    #pending_data.run_repeating(peding_controll, interval=600, first=0)
    price_tast_control.run_repeating(price_controler, interval=600, first=0)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("register", register))
    dp.add_handler(CommandHandler("utopian", utopian))
    dp.add_handler(CommandHandler("utopianqa", utopianqa))    
    dp.add_handler(CommandHandler("pending", pending_post))
    dp.add_handler(CommandHandler("price", price_all))
    dp.add_handler(CommandHandler("price_task", price_task))
    dp.add_handler(CommandHandler("price_destroy", price_destroy))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("me", profile_me))
    dp.add_handler(CommandHandler("other", other_account))
    dp.add_handler(CallbackQueryHandler(button))


    dp.add_error_handler(error)
    updater.start_polling()
    updater.idle()
    


if __name__ == '__main__':
    main()
