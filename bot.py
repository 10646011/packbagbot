import configparser
import logging
import random
import telegram
from flask import Flask, request, render_template
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, Dispatcher, CallbackQueryHandler
import db
from place.PAPI import getNear, getPlace

# Load data from config.ini file
config = configparser.ConfigParser()
config.read('config.ini')

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Initial Flask app
app = Flask(__name__)

# Initial bot by Telegram access token
bot = telegram.Bot(token=(config['TELEGRAM']['ACCESS_TOKEN']))

NAMING, DIRECTION, COUNTY, TYPE_ONE, TYPE_TWO, TYPE_THREE, TRAFFIC, PLACE, PLACE_TWO, = range(9)
travelname = {} #紀錄使用者當前行程名稱
cntplace = {} #紀錄使用者安排景點數量
tmpplace = {} #暫存使用者選擇景點
placebuttontmp = {} #暫存使用者按鈕資料
tmpplacedetail = {} #紀錄地點詳細資訊
tmpregion = {} #紀錄地區
tmptypes= {} #紀錄類型次數



@app.route('/')
def hi():
    return "<h1>Hello World!</h1>"


@app.route('/hook', methods=['POST'])
def webhook_handler():
    """Set route /hook with POST method will trigger this method."""
    if request.method == "POST":
        update = telegram.Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
    return 'ok'

# @app.route('/schedule/<name>')
# def hello(name=None):
#     return render_template('templates/schedule.html', name=name)

def greet(bot, update):
    update.message.reply_text('HI~我是旅泊包🎒 \n 我能依照你的喜好，推薦熱門景點給你')
    update.message.reply_text('準備要去旅行了嗎 ٩(ˊᗜˋ*)و \n立即輸入 /letsgo 開始使用！')


def naming(bot, update):
    logger.info("username: %s start",update.message.from_user)
    update.message.reply_text('請先替這次行程取個名字')
    return NAMING

def start(bot, update):
    UserID = update.message.from_user['id']
    travelname.update( { UserID : update.message.text} )
    db.storeTname([UserID,travelname[UserID]])
    logger.info("username: %s start",update.message.from_user)
    keyboard = [
        [InlineKeyboardButton("北部", callback_data='North'),
         InlineKeyboardButton("中部", callback_data='Central')],
         [InlineKeyboardButton("南部", callback_data='South'),
         InlineKeyboardButton("東部", callback_data='East')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('請問這次要去哪裡玩呢？',reply_markup=reply_markup)
    return DIRECTION

def selcounty(bot, update):
    UserID = update.update.callback_query.from_user['id']
    query = update.callback_query
    

    tmpregion.update( {UserID:query.data} )
    query.answer()

    if tmpregion[UserID] == 'North':
        keyboard = [
            [InlineKeyboardButton("基隆", callback_data="基隆")],
            [InlineKeyboardButton("台北", callback_data="台北")],
            [InlineKeyboardButton("新北", callback_data="新北")],
            [InlineKeyboardButton("桃園", callback_data="桃園")],
            [InlineKeyboardButton("新竹", callback_data="新竹")]
        ]
    elif tmpregion[UserID] == 'Central':
         keyboard = [
        [InlineKeyboardButton("苗栗", callback_data="苗栗")],
         [InlineKeyboardButton("台中", callback_data="台中")],
         [InlineKeyboardButton("彰化", callback_data="彰化")],
         [InlineKeyboardButton("南投", callback_data="南投")],
         [InlineKeyboardButton("雲林", callback_data="雲林")]
    ]
    elif tmpregion[UserID] == 'South':
        keyboard = [
        [InlineKeyboardButton("嘉義", callback_data="嘉義")],
         [InlineKeyboardButton("台南", callback_data="台南")],
         [InlineKeyboardButton("高雄", callback_data="高雄")],
         [InlineKeyboardButton("屏東", callback_data="屏東")]
    ]
    elif tmpregion[UserID] == 'East':
        keyboard = [
        [InlineKeyboardButton("宜蘭", callback_data="宜蘭")],
        [InlineKeyboardButton("花蓮", callback_data="花蓮")],
        [InlineKeyboardButton("台東", callback_data="台東")]
    ]



    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        text="請選擇縣市：",
        reply_markup=reply_markup
    )
    
    return COUNTY





def button(bot, update):
    UserID = update.callback_query.from_user['id']
    query = update.callback_query
    logger.info("username: %s chooses %s",update.callback_query.from_user['id'],query.data)
    
    db.storeCOUNTY([query.data, UserID, travelname[UserID]])
    reply_text=["我也喜歡"+query.data+"🙆",
                "我超愛"+query.data+"👏",
                query.data+"確實是個好玩的地方👍"]
    i = random.randint(0,2)
    query.edit_message_text(reply_text[i]+"\n確認地點沒問題的話請幫我點選👇\n               /chooseOK")
    
    return COUNTY


#####type#######
def type_one(bot, update):
    
    reply_keyboard=[['特色商圈','古蹟廟宇'],['人文藝術','景觀風景'],['休閒農業','戶外休閒'],['主題樂園','無礙障旅遊']]
    update.message.reply_text('請問有什麼想去的景點類型呢？',reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return TYPE_ONE

def type_two(bot, update):
    UserID = update.message.from_user['id']
    Text = update.message.text
    Text = Text.replace(" ","")
    db.storeTYPE_one([Text,UserID,travelname[UserID]])
        

    reply_keyboard=[['特色商圈','古蹟廟宇'],['人文藝術','景觀風景'],['休閒農業','戶外休閒'],['主題樂園','無礙障旅遊'],['/done']]
    update.message.reply_text(f'你選擇的是「{Text}」，\n還有其他有興趣的類型嗎？\n如果沒有，請幫我選擇「/done」',reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    if update.message.text != "/done":
        logger.info("%s is choose %s", update.message.from_user, update.message.text)

    return TYPE_TWO

def type_three(bot, update):
    UserID = update.message.from_user['id']
    Text = update.message.text
    Text = Text.replace(" ","")
    db.storeTYPE_two([Text,UserID,travelname[UserID]])
    

    reply_keyboard=[['特色商圈','古蹟廟宇'],['人文藝術','景觀風景'],['休閒農業','戶外休閒'],['主題樂園','無礙障旅遊'],['/done']]
    update.message.reply_text(f'你選擇的是「{Text}」，\n還有其他有興趣的類型嗎？\n如果沒有，請幫我選擇「/done」',reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    if update.message.text != "/done":
        logger.info("%s is choose %s", update.message.from_user, update.message.text)

    return TYPE_THREE
######traffic way ##########

def traffic(bot, update):
    UserID = update.message.from_user['id']
    Text = update.message.text
    cntplace.update( {UserID:1} )
    print(Text)
    if Text != '/done':
        Text = Text.replace(" ","")
        db.storeTYPE_three([Text,UserID,travelname[UserID]])

    logger.info("type is %s form %s",update.message.text,update.message.from_user)
    reply_keyboard=[['客運🚌','火車🚂'],['高鐵🚅','開車🚘']]
    update.message.reply_text('想如何前往呢？',reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return TRAFFIC

#####place####
def confirmbutton(bot, update):
    UserID = update.callback_query.from_user['id'] 
    query = update.callback_query
    print(tmpplace[UserID])
    
    db.storePlace(cntplace[UserID],[ tmpplace[UserID],UserID,travelname[UserID] ])
    print(tmpplacedetail[UserID])
    db.setPlacedetail(tmpplacedetail[UserID])

    cntplace[UserID]+=1
    print(cntplace[UserID])
    
    query.edit_message_text(text="如果要繼續選景點請輸入「 /next 」，\n如果完成行程請輸入「 /done 」")
    return PLACE

def placedetail(bot, update):  #按鈕暫時無作用
    UserID = update.callback_query.from_user['id'] 
    query = update.callback_query
    query.answer()
    
    detail=getPlace(query.data)
    name = detail['name']
    rating = str(detail['rating'])
    address = detail['formatted_address']

    try:
        detail['weekday_text']
    except:
        time = "尚未提供營業時間" + "\n"
    else:
        time =  detail['weekday_text'][0]+"\n"+detail['weekday_text'][1]+"\n"+detail['weekday_text'][2]+"\n"+detail['weekday_text'][3]+"\n"+detail['weekday_text'][4]+"\n"+detail['weekday_text'][5]+"\n"+detail['weekday_text'][6]+"\n"

    try:
        detail['formatted_phone_number']
    except:
        phone = "尚未提供電話" + "\n"
    else:
        phone = detail['formatted_phone_number']


    tmpplace.update( {UserID:name} )
    tmpplacedetail.update( {UserID:[name,address,rating,phone,time]} )
    
    keyboard = [
        [InlineKeyboardButton("上一頁", callback_data="上一頁")],
        [InlineKeyboardButton("加入景點", callback_data=str(confirmbutton))],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    
    
    query.edit_message_text(
        text="🔹名稱: "+name+"\n"+
        "🔹評價"+rating+" / 5\n"+
        "🔹地址: "+address+"\n"+
        "🔹電話："+phone+"\n"
        "🔹營業時間: \n"+ time
        
        
        ,
        reply_markup=reply_markup
    )

def returnbutton(bot, update):
    UserID = update.callback_query.from_user['id']
    keyboard = placebuttontmp[UserID]
    query = update.callback_query
    markup = InlineKeyboardMarkup(keyboard)
    print(markup)
    query.edit_message_text('想開車去哪裡玩呢？',reply_markup=markup)

    return PLACE

# def placeforcar(bot, update):
    UserID = update.message.from_user['id']
    logger.info("%s prees 自行前往", UserID)
    

    types = db.getTYPE([UserID,travelname[UserID]])
    county = db.getCOUNTY([UserID,travelname[UserID]])
    print(types)
    
    if ((len(types)-1) == 0):
        i = 0
    else:
        i = random.randint(0,len(types)-1)
        while types[i]==None:
            i = random.randint(0,len(types)-1)
    
    places = getNear(county[0],types[i]) #取得景點名稱
    
    button = []
    for name in places:
        button.append([InlineKeyboardButton(name['name'], callback_data=name['placeid'])],)
    

    keyboard = button
    
    placebuttontmp.update({UserID:keyboard})
    
    markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('想開車去哪裡玩呢？',reply_markup=markup)
    

    return PLACE





#############seconed place

def place_choose(bot, update):
    UserID = update.message.from_user['id']
    logger.info("%s prees 自行前往", UserID)


    types = db.getTYPE([UserID,travelname[UserID]])
    county = db.getCOUNTY([UserID,travelname[UserID]])
    print(types)
    if ((len(types)-1) == 0):
        i = 0
    else:
        i = random.randint(0,len(types)-1)
        while types[i]==None:
            i = random.randint(0,len(types)-1)
            
    print(types[i])

    places = getNear(county[0],types[i]) #取得景點名稱
    
    button = []
    for name in places:
        button.append([InlineKeyboardButton(name['name'], callback_data=name['placeid'])],)
    
    keyboard = button
    placebuttontmp.update({UserID:keyboard})
    markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('下個景點想去哪呢？',reply_markup=markup)




    return PLACE

















#################################
def help_handler(bot, update):
    update.message.reply_text('需要甚麼幫助嗎?')

def warnnn(bot,update):
    reply_text=["(๑•́ ₃ •̀๑)旅泊包不懂","( ˘･з･)這是什麼意思","旅泊包沒學過這個( ´•̥̥̥ω•̥̥̥` )"]
    i = random.randint(0,3)
    update.message.reply_text(reply_text[i])

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def restart(bot,update):
    UserID = [update.message.from_user['id']]
    update.message.reply_text('完成')
    db.Deleterecord(UserID)
    return ConversationHandler.END

def done(bot,update):
    UserID = update.message.from_user['id']
    landmarks = list(db.getPLACE([UserID,travelname[UserID]]))
    
    i = 1
    place_output = ""
    for landmark in landmarks:
        if landmark:
            place_output += str(i) +". "+landmark + "\n"
            i += 1
        else:
            break

    update.message.reply_text('旅泊包幫你安排好行程嘍')
    update.message.reply_text(place_output)
    update.message.reply_text('希望你喜歡旅泊包安排的行程🐾\n祝你玩得愉快！')
    return ConversationHandler.END


conv_handler = ConversationHandler(
        entry_points=[CommandHandler('letsgo', naming)],

        states={
            NAMING:[MessageHandler(Filters.text, start),],
            DIRECTION: [
                        CallbackQueryHandler(selcounty),
                        ],
            COUNTY: [ CallbackQueryHandler(start, pattern='^' + str(start) + '$'),
                      CallbackQueryHandler(button),
                      MessageHandler(Filters.regex('^(/chooseOK)$'), type_one),
                      MessageHandler(Filters.regex('^(Ok)$'), type_one),
                      MessageHandler(Filters.regex('^(OK)$'), type_one)],
            TYPE_ONE: [
                       MessageHandler(Filters.text, type_two),],
            TYPE_TWO:[
                       CommandHandler('done', traffic),
                       MessageHandler(Filters.text, type_three),],
            TYPE_THREE:[
                       CommandHandler('done', traffic),
                       MessageHandler(Filters.text, traffic),],
            TRAFFIC:[
                    MessageHandler(Filters.regex('^(開車🚘)$'), place_choose),
                    MessageHandler(Filters.regex('^(火車🚂)$'), place_choose),
                    MessageHandler(Filters.regex('^(客運🚌)$'), place_choose),
                    MessageHandler(Filters.regex('^(高鐵🚅)$'), place_choose),
            ],
            PLACE:[CommandHandler('restart', restart),
                CallbackQueryHandler(returnbutton, pattern='^(上一頁)$'),
                CallbackQueryHandler(confirmbutton, pattern='^' + str(confirmbutton) + '$'),
                CallbackQueryHandler(placedetail),
                CommandHandler('next', place_choose),
                CommandHandler('done', done),
                MessageHandler(Filters.regex('^(下一個)$'), place_choose),
                MessageHandler(Filters.regex('^(完成)$'), done)],

        },

        fallbacks=[CommandHandler('restart', restart),MessageHandler(Filters.regex('^Done$'), done)]
    )

# New a dispatcher for bot
dispatcher = Dispatcher(bot, None)



# Add handler for handling message, there are many kinds of message. For this handler, it particular handle text
# message.

dispatcher.add_handler(conv_handler)
dispatcher.add_handler(CommandHandler('help', help_handler))
dispatcher.add_handler(CommandHandler('start', greet))
dispatcher.add_handler(CommandHandler('restart', restart))
dispatcher.add_handler(MessageHandler(Filters.text, warnnn))

if __name__ == "__main__":
    # Running server
    app.run(debug=True,ssl_context=('ca/certificate.crt','ca/private.key'),port=443)