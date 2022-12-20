import json
with open('fawiki_cases', 'r') as f:
    lines = f.read().split('\n')
cases = {}
for line in lines:
    line = line.split('\t')
    try:
        rev_id = int(line[0])
    except:
        continue
    try:
        parent_rev_id = int(line[1])
    except:
        continue
    serialization = str(rev_id) + '-' + str(parent_rev_id)
    cases[serialization] = cases.get(serialization, False)
    if 'reverted' in line[-1]:
        cases[serialization] = True

with open('training_set.json', 'w') as f:
    f.write(json.dumps(cases))