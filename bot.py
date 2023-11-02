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

async def cmd_graph_daily_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    await context.bot.send_message(chat_id, 'Send month date - YYYY/MM')

    return 2

async def cmd_graph_new_user_payments_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    date = update.message.text.strip()

    days = {}
    try:
        days = db.days_new_users_stats(date)
    except BaseException:
        await context.bot.send_message(chat_id, 'Bad month date')
        return 0

    t = list(days.items())

    user_count = []
    days = []

    for (m, l) in t:
        gt_1 = 0
        gt_50 = 0

        for v in l:
            if v > 1.0: gt_1 += 1
            if v > 50.0: gt_50 += 1

    #     pr_1 = gt_1 / len(l) * 100
    #     pr_50 = gt_50 / len(l) * 100
        pr_1 = gt_1
        pr_50 = gt_50

        days.append((m, (pr_1, pr_50)))
        user_count.append((m, len(l)))

    def sort_days(v):
        (y, m, d) = v.split('/')
        y = int(y)
        m = int(m)
        d = int(d)

        return (y * 12 + m) * 31 + d
    
    user_count.sort(key=lambda x: sort_days(x[0]))
    days.sort(key=lambda x: sort_days(x[0]))
    # user_count = user_count[-12:]
    # months = months[-12:]

    x_labels = []
    y1_coord = []
    y2_coord = []
    y3_coord = []

    [(x_labels.append(k), y1_coord.append(v[0]), y2_coord.append(v[1])) for (k, v) in days]
    [y3_coord.append(v) for (_, v) in user_count]

    # plt.plot(x_labels, y3_coord, label='new users')
    plt.plot(x_labels, y1_coord, label='> $1')
    plt.plot(x_labels, y2_coord, label='> $50')
    plt.gca().yaxis.set_major_formatter(lambda x, _: f'{int(x)}')
    plt.gca().xaxis.set_major_formatter(lambda x, p: f'{int(x + 1) if p % 5 == 0 else ""}')

    plt.xlabel(f'{days[0][0]} - {days[-1][0]}')
    plt.ylabel('New Users')
    # plt.ylabel('New Users %')

    # plt.autoscale()
    plt.legend()

    plt.savefig('chart.png')
    plt.clf()

    await context.bot.send_photo(chat_id, open('chart.png', 'rb'), caption='New users payments daily rate')

    plt.plot(x_labels, y3_coord)
    plt.xlabel(f'{days[0][0]} - {days[-1][0]}')
    plt.ylabel('New Users')
    plt.gca().yaxis.set_major_formatter(lambda x, _: f'{int(x)}')
    plt.gca().xaxis.set_major_formatter(lambda x, p: f'{int(x + 1) if p % 5 == 0 else ""}')

    plt.savefig('chart.png')
    plt.clf()

    data_text = '\n'.join([f'{k}: {v}' for (k, v) in user_count])

    await context.bot.send_photo(chat_id, open('chart.png', 'rb'), caption=f'New accounts daily rate\n\n{data_text}')

    return 0


async def cmd_graph_new_user_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    months = db.months_new_users_stats()

    t = list(months.items())

    user_count = []
    months = []

    for (m, l) in t:
        gt_1 = 0
        gt_50 = 0

        for v in l:
            if v > 1.0: gt_1 += 1
            if v > 50.0: gt_50 += 1

    #     pr_1 = gt_1 / len(l) * 100
    #     pr_50 = gt_50 / len(l) * 100
        pr_1 = gt_1
        pr_50 = gt_50

        months.append((m, (pr_1, pr_50)))
        user_count.append((m, len(l)))

    def sort_months(v):
        (y, m) = v.split('/')
        y = int(y)
        m = int(m)

        return y * 12 + m
    
    user_count.sort(key=lambda x: sort_months(x[0]))
    months.sort(key=lambda x: sort_months(x[0]))
    user_count = user_count[-12:]
    months = months[-12:]

    x_labels = []
    y1_coord = []
    y2_coord = []
    y3_coord = []

    [(x_labels.append(k[2:]), y1_coord.append(v[0]), y2_coord.append(v[1])) for (k, v) in months]
    [y3_coord.append(v) for (_, v) in user_count]

    # plt.plot(x_labels, y3_coord, label='new users')
    plt.plot(x_labels, y1_coord, label='> $1')
    plt.plot(x_labels, y2_coord, label='> $50')
    # plt.gca().yaxis.set_major_formatter(lambda x, _: f'{int(x)}%')

    plt.xlabel('Months')
    plt.ylabel('New Users')
    # plt.ylabel('New Users %')

    # plt.autoscale()
    plt.legend()

    plt.savefig('chart.png')
    plt.clf()

    await context.bot.send_photo(chat_id, open('chart.png', 'rb'), caption='New users payments monthly rate')

    plt.plot(x_labels, y3_coord)
    plt.xlabel('Months')
    plt.ylabel('New Users')
    plt.savefig('chart.png')
    plt.clf()

    data_text = [f'{k}: {v}' for (k, v) in user_count]
    data_text = [f'{data_text[i]} - {int(months[i][1][0] / user_count[i][1] * 100)}% payed > $1' for i in range(len(months))]
    data_text = '\n'.join(data_text)

    await context.bot.send_photo(chat_id, open('chart.png', 'rb'), caption=f'New accounts monthly rate\n\n{data_text}')

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

    data_text = '\n'.join([f'{k}: ${int(v * 100) / 100}' for (k, v) in months])

    await context.bot.send_photo(chat_id, open('chart.png', 'rb'), caption=f'Total payments monthly\n\n{data_text}')

    return 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if not str(chat_id) in USERS:
        print(chat_id)
        return 1
    
    chart1_btn = InlineKeyboardButton('📊 Monthly Payments', callback_data=1)
    chart2_btn = InlineKeyboardButton('📊 New Users (Monthly)', callback_data=2)
    chart3_btn = InlineKeyboardButton('📊 New Users (Daily)', callback_data=4)
    user_get_btn = InlineKeyboardButton('👤 User Info', callback_data=3)

    keyboard = InlineKeyboardMarkup([[chart1_btn], [chart2_btn], [chart3_btn], [user_get_btn]])

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
                CallbackQueryHandler(cmd_graph_daily_select, pattern='^4$'),
                CallbackQueryHandler(cmd_get_user, pattern='^3$'),
            ],
            1: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_get_user_search)
            ],
            2: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_graph_new_user_payments_daily)
            ]
        },
        [],
        allow_reentry=True
    )

    application.add_handler(conv)

    application.run_polling(timeout=60, pool_timeout=30)