import json
import requests
import math
import re
import sys
from difflib import ndiff
import mwparserfromhell

api_endpoint = 'https://fa.wikipedia.org/w/api.php'
persian_letters = 'ابپتثجچحخدذرًٌٍَُِّْؤئإأةزژسٔءشصآضطظعغفقکگلمنوهی‌يك'
iranian_names = ['زینب', 'آتنا', 'آراد', 'آرتین', 'آرش', 'آرمین', 'آریا', 'آرین', 'آوا', 'آیدا', 'آیلین', 'آیناز', 'ابوالفضل', 'احسان', 'اسرا', 'اسما', 'النا', 'الناز', 'الینا', 'امیرحافظ', 'امیرحسین', 'امیررضا', 'امیرعباس', 'امیرعلی', 'امیرمحمد', 'امیرمهدی', 'ایلیا', 'باران', 'بنیامین', 'بهار', 'ثنا', 'حدیث', 'حدیثه', 'حسام', 'حسنا', 'حسین', 'حلما', 'حمیدرضا', 'حنانه', 'دانیال', 'رضا', 'رقیه', 'رها', 'ریحانه', 'زهرا', 'زینب', 'سارا', 'سارینا', 'سامیار', 'سبحان', 'ستایش', 'سجاد', 'سهیل', 'سوگند', 'سینا', 'شایان', 'صبا', 'طاها', 'عباس', 'عرشیا', 'عرفان', 'عسل', 'علی', 'علیرضا', 'علی\u200cاصغر', 'علی\u200cاکبر', 'علی\u200cرضا', 'غزل', 'فائزه', 'فاطمه', 'فاطمه زهرا', 'فاطمیا', 'مائده', 'ماهان', 'مبین', 'مبینا', 'متین', 'محدثه', 'محسن', 'محمد', 'محمدامین', 'محمدجواد', 'محمدحسین', 'محمدرضا', 'محمدطاها', 'محمدعلی', 'محمدمتین', 'محمدمهدی', 'محمدپارسا', 'محمدیاسین', 'محیا', 'مریم', 'معصومه', 'ملیکا', 'مهدی', 'مهدیس', 'مهسا', 'نازنین', 'نازنین زهرا', 'نرگس', 'نیایش', 'نیما', 'هانیه', 'هستی', 'هلیا', 'پارسا', 'پرنیا', 'پرهام', 'پریا', 'کوثر', 'کیان', 'کیانا', 'یاسمین', 'یاسین', 'یسنا', 'یلدا', 'یوسف', 'یگانه']
def get_ores_scores(revs: list):
    data = requests.get('https://ores.wikimedia.org/v3/scores/fawiki/?revids=' +  '|'.join([str(i) for i in revs])).json()
    return data['fawiki']['scores']
def get_revs_data(revs: list):
    final_data = {}
    r = requests.get(
        api_endpoint,
        {
            'action': 'query',
            'prop': 'revisions',
            'revids': '|'.join([str(i) for i in revs]),
            'format': 'json',
            'rvslots': 'main',
            'rvprop': 'ids|timestamp|user|userid|size|comment|content|tags|oresscores'
        }
    )
    data = r.json()
    for page_id in data['query']['pages']:
        page_ns = data['query']['pages'][page_id]['ns']
        for revision in data['query']['pages'][page_id]['revisions']:
            parent_id = revision['parentid']
            user_id = revision['userid']
            try:
                timestampt = revision['timestamp']
                content = revision['slots']['main']['*']
                comment = revision['comment']
            except:
                continue
            tags = revision['tags']
            final_data[revision['revid']] = {
                'parent_id': parent_id,
                'user_id': user_id,
                'user': revision['user'],
                'timestamp': timestampt,
                'content': content,
                'comment': comment,
                'tags': tags,
                'page_ns': page_ns
            }
    return final_data

def weighted_score(score):
    return (
        (score['FA'] * 5) +
        (score['GA'] * 4) +
        (score['B'] * 3) +
        (score['C'] * 2) +
        (score['Start'] * 1) +
        score['Stub']
    )

def build_features(current_data, parent_data, ores_data_current, ores_data_parent):
    diff = ndiff(parent_data['content'].splitlines(keepends=True), current_data['content'].splitlines(keepends=True))
    lines_added = []
    lines_removed = []
    for line in diff:
        if line.startswith('+ '):
            if not line[2:-1]:
                continue
            lines_added.append(line[2:-1])
        if line.startswith('- '):
            if not line[2:-1]:
                continue
            lines_removed.append(line[2:-1])
    wikicode_lines_added = mwparserfromhell.parse('\n'.join(lines_added))
    wikicode_lines_removed = mwparserfromhell.parse('\n'.join(lines_removed))
    ext_links_in_added = set([str(i.url) for i in wikicode_lines_added.filter_external_links()])
    ext_links_in_removed = set([str(i.url) for i in wikicode_lines_removed.filter_external_links()])
    wiki_links_in_added = set([str(i.title) for i in wikicode_lines_added.filter_wikilinks()])
    wiki_links_in_removed = set([str(i.title) for i in wikicode_lines_removed.filter_wikilinks()])
    refs_in_added = set([str(i.contents) for i in wikicode_lines_added.filter_tags() if i.tag == 'ref' and i.contents])
    refs_in_removed = set([str(i.contents) for i in wikicode_lines_removed.filter_tags() if i.tag == 'ref' and i.contents])
    words_in_added = re.findall(r'[%s]{2,}' % persian_letters, '\n'.join(lines_added))
    words_in_removed = re.findall(r'[%s]{2,}' % persian_letters, '\n'.join(lines_removed))
    words_added = set(words_in_added) - set(words_in_removed)
    words_removed = set(words_in_removed) - set(words_in_added)
    persian_digits_in_added = set(re.findall(r'[۱۲۳۴۵۶۷۸۹۰]+', '\n'.join(lines_added)))
    persian_digits_in_removed = set(re.findall(r'[۱۲۳۴۵۶۷۸۹۰]+', '\n'.join(lines_removed)))
    latin_digits_in_added = set(re.findall(r'[0123456789]+', '\n'.join(lines_added)))
    latin_digits_in_removed = set(re.findall(r'[0123456789]+', '\n'.join(lines_added)))
    files_in_added = set()
    for wikilink in wiki_links_in_added:
        if re.search(r'^([Ff]ile:|[Ii]mage:|تصویر:|پرونده:)', wikilink):
            files_in_added.add(wikilink)
    
    files_in_removed = set()
    for wikilink in wiki_links_in_removed:
        if re.search(r'^([Ff]ile:|[Ii]mage:|تصویر:|پرونده:)', wikilink):
            files_in_removed.add(wikilink)

    is_blp = '[[رده:افراد زنده' in current_data['content'] or '[[رده:افراد زنده' in parent_data['content']
    is_iran_city = '{{جعبه شهر ایران' in current_data['content'] or '{{جعبه شهر ایران' in parent_data['content']
    is_user = bool(current_data['user_id'])
    content_len = math.log(len(current_data['content']) + 1)
    diff_len = len(parent_data['content']) - len(current_data['content'])
    comment_len = math.log(len(current_data['comment']) + 1)
    comment_words = current_data['comment'].count(' ')
    tags_len = len(current_data['tags'])
    is_revert = 'mw-manual-revert' in current_data['tags']
    is_main_ns = int(current_data['page_ns']) == 0
    hour_of_day = current_data['timestamp'].split('T')[1].split(':')[0]
    damaging_score = ores_data_current['damaging']['score']['probability']['true']
    good_faith_score = ores_data_current['goodfaith']['score']['probability']['true']
    parent_wp_score = weighted_score(ores_data_current['articlequality']['score']['probability'])
    current_wp_score = weighted_score(ores_data_parent['articlequality']['score']['probability'])
    return [
        is_blp,
        is_iran_city,
        is_user,
        is_revert,
        content_len,
        math.log(abs(diff_len) + 1),
        diff_len > 0,
        comment_len,
        comment_words,
        tags_len,
        is_main_ns,
        hour_of_day,
        damaging_score,
        good_faith_score,
        parent_wp_score - current_wp_score,
        len(lines_added),
        len(lines_removed),
        len(ext_links_in_added - ext_links_in_removed),
        len(ext_links_in_removed - ext_links_in_added),
        len(wiki_links_in_added - wiki_links_in_removed),
        len(wiki_links_in_removed - wiki_links_in_added),
        len(refs_in_added - refs_in_removed),
        len(refs_in_removed - refs_in_added),
        len(words_added),
        len(words_removed),
        len(words_in_added) - len(words_in_removed),
        len(persian_digits_in_added - persian_digits_in_removed),
        len(persian_digits_in_removed - persian_digits_in_added),
        len(latin_digits_in_added - latin_digits_in_removed),
        len(latin_digits_in_removed - latin_digits_in_added),
        len(files_in_added - files_in_removed),
        len(files_in_removed - files_in_added),
        len([i for i in words_added if i in iranian_names]),
        len([i for i in words_removed if i in iranian_names])
    ]

def main():
    with open('training_set.json', 'r') as f:
        cases = json.loads(f.read())
    c = 0
    cases_list = list(cases.keys())
    X = []
    y = []
    c = 0
    for i in range(0, len(cases_list), 50):
        c += 1
        print('One batch done', c)
        #if c > 10:
        #    break
        fff = cases_list[i:i+50]
        revs = {
            int(j.split('-')[0]): int(j.split('-')[1]) for j in fff
        }
        data_currents = get_revs_data(revs.keys())
        parents = [j['parent_id'] for j in data_currents.values() if j['parent_id'] != 0]
        data_parents = get_revs_data(parents)
        ores_currents = get_ores_scores(revs.keys())
        ores_parents = get_ores_scores(parents)
        for rev_id in revs:
            if not revs[rev_id]:
                continue
            try:
                features = build_features(
                    data_currents[rev_id],
                    data_parents[revs[rev_id]],
                    ores_currents[str(rev_id)],
                    ores_parents[str(revs[rev_id])],
                )
                X.append([float(i) for i in features])
                y.append(float(cases['{}-{}'.format(rev_id, revs[rev_id])]))
            except KeyboardInterrupt:
                sys.exit()
            except:
                continue
    with open('x.json', 'w') as f:
        f.write(json.dumps(X))
    with open('y.json', 'w') as f:
        f.write(json.dumps(y))

if __name__ == "__main__":
    main()
