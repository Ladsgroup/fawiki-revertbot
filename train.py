from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score
from sklearn.neural_network import MLPClassifier
from sklearn import svm
import pickle
import json
with open('x.json', 'r') as f:
    X = json.loads(f.read())
with open('y.json', 'r') as f:
    y = json.loads(f.read())

scaler = StandardScaler()
scaler.fit(X)
with open('fawiki.scaler', 'wb') as f:
    pickle.dump(scaler, f)

X = scaler.transform(X)
clf = MLPClassifier(solver='lbfgs', alpha=1e-5, max_iter=500,
                    hidden_layer_sizes=(5, 5, 2), random_state=1)
#clf = svm.SVC(kernel='poly', C=1, random_state=42)
#scores = cross_val_score(clf, X, y, cv=5)
#print(sum(scores)/len(scores))
clf.fit(X, y)
with open('fawiki.model', 'wb') as f:
    pickle.dump(clf, f)

