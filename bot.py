import logging
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
import matplotlib.pyplot as plt 
from matplotlib.ticker import EngFormatter
import yaml
import updates
import db
from datetime import datetime

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

CRED = yaml.safe_load(open('credentials.yaml'))['TELEGRAM']
TOKEN = CRED['TOKEN']
USERS = CRED['USER_IDS']

async def get_updates(context: ContextTypes.DEFAULT_TYPE):
    u = updates.get_updates()
    
    for v in u[0]:
        db.add_payment(v['username'], v)
    
    for v in u[1]:
        db.update_user(v['username'], v)

async def cmd_get_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    await context.bot.send_message(chat_id, 'Send a username')

    return 1

async def cmd_get_user_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    username = update.message.text.strip()
    user = db.search_user(username)

    if user == None:
        await context.bot.send_message(chat_id, f'No user found matching {username}')
        return 0
    
    for (k, v) in user['payments_months'].items():
        user[k] = v
    
    user['last_login'] = datetime.fromtimestamp(user['last_login']).strftime('%Y/%m/%d %H:%M:%S')
    user['register'] = datetime.fromtimestamp(user['register']).strftime('%Y/%m/%d %H:%M:%S')

    del user['payments_months']
    del user['_id']
    
    s = ', '.join(user.keys()) + '\n' + ', '.join([str(v) for v in user.values()])

    fw = open('u.csv', 'w', encoding='utf-8')
    fw.write(s)
    fw.close()

    await context.bot.send_document(chat_id, open('u.csv', encoding='utf-8'), filename='user.csv')

    return 0

async def cmd_graph_new_user_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    months = db.months_new_users_stats()

    t = list(months.items())
    months = []

    for (m, l) in t:
        gt_1 = 0
        gt_50 = 0

        for v in l:
            if v > 1.0: gt_1 += 1
            if v > 50.0: gt_50 += 1

        pr_1 = gt_1 / len(l) * 100
        pr_50 = gt_50 / len(l) * 100

        months.append((m, (pr_1, pr_50)))

    def sort_months(v):
        (y, m) = v.split('/')
        y = int(y)
        m = int(m)

        return y * 12 + m
    
    months.sort(key=lambda x: sort_months(x[0]))
    months = months[-12:]

    x_labels = []
    y1_coord = []
    y2_coord = []

    [(x_labels.append(k[2:]), y1_coord.append(v[0]), y2_coord.append(v[1])) for (k, v) in months]

    plt.plot(x_labels, y1_coord, label='> $1')
    plt.plot(x_labels, y2_coord, label='> $50')
    plt.gca().yaxis.set_major_formatter(lambda x, _: f'{int(x)}%')

    plt.xlabel('Months')
    plt.ylabel('New Users %')

    plt.autoscale()
    plt.legend()

    plt.savefig('chart.png')
    plt.clf()

    await context.bot.send_photo(chat_id, open('chart.png', 'rb'), caption='New users payments monthly rate')

    return 0


async def cmd_graph_monthly_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    months = db.months_payments_stats()

    months = list(months.items())
    
    def sort_months(v):
        (y, m) = v.split('/')
        y = int(y)
        m = int(m)

        return y * 12 + m

    months.sort(key=lambda x: sort_months(x[0]))
    months = months[-12:]

    x_labels = []
    y_coord = []

    [(x_labels.append(k[2:]), y_coord.append(v)) for (k, v) in months]

    plt.plot(x_labels, y_coord)
    plt.gca().yaxis.set_major_formatter(lambda x, _: f'{str(int(x / 1000)) + "k"} $')

    plt.xlabel('Months')
    plt.ylabel('Payments')

    plt.savefig('chart.png')
    plt.clf()

    await context.bot.send_photo(chat_id, open('chart.png', 'rb'), caption='Total payments monthly')

    return 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if not str(chat_id) in USERS:
        print(chat_id)
        return 1
    
    chart1_btn = InlineKeyboardButton('📊 Monthly Payments', callback_data=1)
    chart2_btn = InlineKeyboardButton('📊 New Users Payments', callback_data=2)
    user_get_btn = InlineKeyboardButton('👤 User Info', callback_data=3)

    keyboard = InlineKeyboardMarkup([[chart1_btn], [chart2_btn], [user_get_btn]])

    await context.bot.send_message(chat_id, '<b>📈 SMM HEAVEN STATS 📈</b>', parse_mode=constants.ParseMode.HTML, reply_markup=keyboard)

    return 0


def init():
    application = ApplicationBuilder().token(TOKEN).build()
    application.job_queue.run_repeating(get_updates, 1800)

    start_hndl = CommandHandler('start', start)

    conv = ConversationHandler(
        [start_hndl],
        {
            0: [
                CallbackQueryHandler(cmd_graph_monthly_payments, pattern='^1$'),
                CallbackQueryHandler(cmd_graph_new_user_payments, pattern='^2$'),
                CallbackQueryHandler(cmd_get_user, pattern='^3$'),
            ],
            1: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_get_user_search)
            ]
        },
        [],
        allow_reentry=True
    )

    application.add_handler(conv)

    application.run_polling(timeout=60, pool_timeout=30)