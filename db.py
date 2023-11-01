import yaml
from pymongo import MongoClient
from datetime import datetime

CONNECT = yaml.safe_load(open('credentials.yaml'))['MONGODB']['CONNECT']
DB = MongoClient(CONNECT).get_database('smm-heaven-stats')

def get_user(username):
    user_data = DB.users.find_one({'username': username})

    if user_data == None:
        user_data = {
            'username': username,
            'email': '',
            'skype': '',
            'user_id': '',
            'payments_total': 0.0,
            'payments_months': {

            },
            'last_login': 0.0,
            'register': 0.0,
        }

        DB.users.insert_one(user_data)

    return user_data

def add_payment(username, data: dict):
    user = get_user(username)
    date = datetime.fromtimestamp(data['timestamp'])
    ym_s = date.strftime('%Y/%m')
    amount = data['amount']

    if not ym_s in user['payments_months']:
        user['payments_months'][ym_s] = 0.0
    
    user['payments_months'][ym_s] += amount
    user['payments_total'] += amount

    DB.users.update_one({'username': username}, {'$set': user})

def update_user(username, data: dict):
    user = get_user(username)
    user['last_login'] = data['timestamp_lastlog']
    user['register'] = data['timestamp_register']
    user['user_id'] = data['user_id']
    user['skype'] = data['skype']
    user['email'] = data['mail']

    DB.users.update_one({'username': username}, {'$set': user})

def months_payments_stats() -> dict:
    users = DB.users.find()
    months = {}

    for u in users:
        for (m, v) in u['payments_months'].items():
            if not m in months:
                months[m] = 0.0
            
            months[m] += v

    return months

def months_new_users_stats() -> dict:
    users = DB.users.find()
    months = {}

    for u in users:
        reg_time = u['register']
        reg_date = datetime.fromtimestamp(reg_time)
        date_s = reg_date.strftime('%Y/%m')

        min_time = datetime.strptime('2023', '%Y').timestamp()

        if reg_time < min_time: continue

        if not date_s in months:
            months[date_s] = []

        amount = 0.0

        if date_s in u['payments_months']:
            amount = u['payments_months'][date_s]

        months[date_s].append(amount)

    return months

def search_user(username) -> dict:
    user = DB.users.find_one({'$text': {'$search': username}})

    return user