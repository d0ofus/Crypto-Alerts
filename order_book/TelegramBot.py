import telepot 

# General Alerts Bot: 6000669376:AAEfLjDq4DNscGh0WQj8RrH7QWTmyXPRziE
# Stock Alerts Bot: 5511454994:AAHx2avRN_jNYVO-91yUveKPJno8fTJ9UlE

def generateMessageTH(stock, timestamp, title):    
    message = '<b><u>' + stock + '</u></b>' + ' - ' + timestamp
    message += "\n<b>Title:</b> " + title 
    message += "\n\n"
   
    return message

def generateMessageSG(stock, timestamp, title, description):  
    message = '<b><u>' + stock + '</u></b>' + ' - ' + timestamp
    message += "\n<b>Title:</b> " + title 
    message += "\n<b>Description:</b> " + description
   
    return message

def sendMessage(text):
    token = "5511454994:AAHx2avRN_jNYVO-91yUveKPJno8fTJ9UlE" # Stock Alerts Bot
    receiver_id = 63259650
    bot = telepot.Bot(token)
    bot.sendMessage(receiver_id, text, parse_mode='HTML')

def sendScriptNotif(market, error):
    token = "6000669376:AAEfLjDq4DNscGh0WQj8RrH7QWTmyXPRziE"
    text = '<b>' + market + ' Earnings Scraper did not run due to:</b>\n\n' + error 
    receiver_id = 63259650
    bot = telepot.Bot(token)
    bot.sendMessage(receiver_id, text, parse_mode='HTML')

def sendNotif_restart():
    token = "6000669376:AAEfLjDq4DNscGh0WQj8RrH7QWTmyXPRziE"
    text = '<b>Thai Earnings Scraper is restarting... </b>' 
    receiver_id = 63259650
    bot = telepot.Bot(token)
    bot.sendMessage(receiver_id, text, parse_mode='HTML')

def sendScriptNotif_ThaiCap(error):
    token = "6000669376:AAEfLjDq4DNscGh0WQj8RrH7QWTmyXPRziE"
    text = '<b>Thai Cap Scraper did not run due to:</b>\n\n' + error 
    receiver_id = 63259650
    bot = telepot.Bot(token)
    bot.sendMessage(receiver_id, text, parse_mode='HTML')

def sendAlert(text):
    token = "6000669376:AAEfLjDq4DNscGh0WQj8RrH7QWTmyXPRziE"
    receiver_id = 63259650
    bot = telepot.Bot(token)
    bot.sendMessage(receiver_id,text, parse_mode='HTML')

#%%
# # Send tele message if too long
# while tele_message != '<b>[TH Earnings]</b>\n':
#     if len(tele_message) > 4096:
#         end = 4096
#         last_item = tele_message.rfind("<b><u>", 0, end)
#         sendMessage(tele_message[:last_item])
#         tele_message = 'Continued...' + '\n\n' + tele_message[last_item:]
#     else:
#         sendMessage(tele_message)
#         tele_message = '<b>[TH Earnings]</b>\n'
#         break
