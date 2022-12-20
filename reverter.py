import pickle
import pywikibot
import time
import sys
import os
from feature_extraction import get_ores_scores, get_revs_data, build_features

dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(dir, 'fawiki.model'), 'rb') as f:
    clf = pickle.load(f)

with open(os.path.join(dir, 'fawiki.scaler'), 'rb') as f:
    scaler = pickle.load(f)

site = pywikibot.Site('fa')
site.login()

def rollback(rc_data, rev_data):
    if int(rc_data['pageid']) == 6062377:
        return
    params = {
        'action': 'rollback',
        'markbot': False,
        'pageid': rc_data['pageid'],
        'user': rev_data['user'],
        'summary': 'واگردانی خودکار [[وپ:خرابکاری|خرابکاری]] بر پایه [[وپ:امتیاز خرابکاری|امتیاز خرابکاری]]. واگردانی اشتباه ربات را همراه با [[راهنما:تفاوت|پیوند تفاوت]] در [[کاربر:Dexbot/گزارش اشتباه]] اعلام کنید. همچنین توصیه میشود [[ویکی‌پدیا:چرا حساب بسازیم؟|حساب کاربری بسازید.]]',
        'token': site.get_tokens(['rollback'])['rollback']
    }
    req = site._request(**params)
    try:
        data = req.submit()
    except KeyboardInterrupt:
        sys.exit()
    except:
        return
    print(data)


def handle_round(previous_revs):
    params = {
        'action': 'query',
        'prop': 'info',
        'generator': 'recentchanges',
        'grcshow': '!patrolled',
        'grctype': 'edit',
        'format': 'json',
        'grclimit': 50,
        'grctoponly': True,
        'grcgeneraterevisions': True
    }
    rc_data = {}
    req = site._request(**params)
    data = req.submit()
    revs = []
    for page_id in data['query']['pages']:
        if 'lastrevid' not in data['query']['pages'][page_id]:
            continue
        rev_id = int(data['query']['pages'][page_id]['lastrevid'])
        if rev_id in previous_revs:
            continue
        rc_data[rev_id] = data['query']['pages'][page_id]
        revs.append(rev_id)
    if not revs:
        return previous_revs
    
    previous_revs += revs

    data_currents = get_revs_data(revs)

    parents = {
        j: data_currents[j]['parent_id'] for j in data_currents if data_currents[j]['parent_id'] != 0
    }
    data_parents = get_revs_data(parents.values())
    ores_currents = get_ores_scores(revs)
    ores_parents = get_ores_scores(parents.values())
    for rev_id in revs:
        if data_currents[rev_id]['user_id']:
            continue
        if not parents[rev_id]:
            continue
        try:
            features = build_features(
                data_currents[rev_id],
                data_parents[parents[rev_id]],
                ores_currents[str(rev_id)],
                ores_parents[str(parents[rev_id])],
            )
            features = scaler.transform([[float(i) for i in features]])
        except KeyboardInterrupt:
            sys.exit()
        except:
            continue
        if clf.predict(features)[0]:
            rollback(rc_data[rev_id], data_currents[rev_id])
        print('*[[Special:Diff/{}]]: {}'.format(rev_id, str(clf.predict(features)[0])))
    return previous_revs

def main():
    revs = []
    while True:
        revs = handle_round(revs)
        time.sleep(60)

        

if __name__ == "__main__":
    main()
