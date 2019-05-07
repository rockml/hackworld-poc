from flask import Flask, session, jsonify, redirect
from flask_session import Session
from flask_oauthlib.client import OAuth
import hacktheworld as hack
import json

app = Flask(__name__)
app.secret_key = "development"
SESSION_TYPE = 'filesystem'
app.config.from_object(__name__)
Session(app)
oauth = OAuth(app)

cms = oauth.remote_app(
    'cms',
    base_url="https://sandbox.bluebutton.cms.gov/v1/o",
    consumer_key="vGeRleIRLnzQbGB8ylsCeUWCkG2oB32x0OjkLAzu",
    consumer_secret="RkT9bH5vBKyITqNUnx70LUXjxvBOMHn1ORZDl87CApH7KKzbv6q9qmYbJoWJWK2q4LH5tJACdOYY0FuZA30yhLlukILcxa0CK9q2ICQiZEjSL2m7WZAUtcQiIPJqBgj3",
    request_token_params={'scope': 'profile'},
    request_token_url=None,
    access_token_url="https://sandbox.bluebutton.cms.gov/v1/o/token/",
    authorize_url="https://sandbox.bluebutton.cms.gov/v1/o/authorize/",
    access_token_method='POST'
)

va = oauth.remote_app(
    'va',
    base_url="https://dev-api.vets.gov/",
    consumer_key="0oa3r2erccoQ1rRmg2p7",
    consumer_secret="nLp6CIis9u9wMcunPNzNa83hlU9eDMQmEyHAl-rq",
    request_token_params={
        'scope': 'openid offline_access profile email launch/patient veteran_status.read patient/Patient.read patient/Condition.read', "state": "12345"},
    request_token_url=None,
    access_token_url="https://dev-api.va.gov/oauth2/token/",
    authorize_url="https://dev-api.va.gov/oauth2/authorization/",
    access_token_method='POST'
)


def nl(line):
    return(line + "</br>")


def save_access_code(filename, mrn, token):
    fp = open(filename, 'w')
    acc = {"patient": mrn, "access_code": token}
    json.dump(acc, fp)
    fp.close()
    return

def authentications():
    auts = []
    if ('va_patient' in session): auts.append('va')
    if ('cms_patient' in session): auts.append('cms')
    return auts

def success_msg(filename, mrn, token):
    html = nl("Success!")
    html += nl('')
    html += nl("Credentials stored in: " + filename)
    html += nl('')
    html += nl("Access token:")
    html += nl(token)
    html += nl('')
    html += nl("Patient ID:")
    html += nl(mrn)
    html += nl('')
    html += '<a href="/">Home</a>'
    return html


@app.route('/')
def home():
    auts = authentications()
    html = nl('Welcome!') + nl('')
    if ('va' in auts):
        html += nl('Your VA patient number is: ' +
                   session["va_patient"]) + nl('')
    else:
        html += nl('<button type="button" onclick="location.href = &quot;/va/authenticate&quot;;" id="VAButton2">Authenticate with VA ID.me</button>')
    if ('cms' in auts):
        html += nl('Your CMS patient number is: ' + session["cms_patient"]) + nl('')
    else:
        html += nl('<button type="button" onclick="location.href = &quot;/cms/authenticate&quot;;" id="CMSButton2">Authenticate with CMS</button>')

    if auts:
        if('trials' not in session):
            html += nl('<button type="button" onclick="location.href = &quot;/getInfo&quot;;" id="infoButton">Find Clinical Trials</button>')
        else:
            html += nl('<button type="button" onclick="location.href = &quot;/displayInfo&quot;;" id="infoButton">View Matched Clinical Trials</button>')
        html += nl('<button type="button" onclick="location.href = &quot;/logout&quot;;" id="logoutButton">Logout</button>')

    return html

@app.route('/cms/authenticate')
def cmsauthenticate():
    return cms.authorize(callback='http://localhost:5000/cmsredirect')


@app.route('/va/authenticate')
def vaauthenticate():
    return va.authorize(callback='http://localhost:5000/varedirect')


@app.route('/cmsredirect')
def cmsredirect():
    resp = cms.authorized_response()
    session['cms_access_token'] = resp['access_token']
    session['cms_patient'] = resp['patient']
    session.pop("trials", None)
    return redirect('/cms/authenticated')


@app.route('/varedirect')
def varedirect():
    resp = va.authorized_response()
    session['va_access_token'] = resp['access_token']
    session['va_patient'] = resp['patient']
    session.pop("trials", None)
    return redirect('/va/authenticated')


@app.route('/cms/authenticated')
def cmsauthenticated():
    token = session.get('cms_access_token')
    mrn = session.get('cms_patient')
    filename = 'accesscodes/cms/' + mrn + '.json'
    save_access_code(filename, mrn, token)
    return redirect("/")


@app.route('/va/authenticated')
def vaauthenticated():
    token = session.get('va_access_token')
    mrn = session.get('va_patient')
    filename = 'accesscodes/va/' + mrn + '.json'
    save_access_code(filename, mrn, token)
    return redirect("/")

@app.route('/getInfo')
def getInfo():
    auts = authentications()
    if (not auts):
        return redirect("/")
    patients = []
    trials = []
    for source in auts:
        if source == 'va':
            mrn = session['va_patient']
            token = session.get('va_access_token')
            pat_token = {"mrn": mrn, "token": token}
            pat = hack.Patient(session['va_patient'], pat_token)
        if source == 'cms':
            mrn = session['cms_patient']
            token = session.get('cms_access_token')
            pat_token = {"mrn": mrn, "token": token}
            pat = hack.CMSPatient(session['cms_patient'], pat_token)
        pat.load_all()
        patients.append(pat)
        trials += pat.trials
    print(type(trials))
    session['trials'] = trials
    session['numTrials'] = len(trials)
    session['index'] = 0
    return redirect("/displayInfo")

@app.route('/displayInfo')
def displayInfo():
    trials = session.get('trials', None)
    index = session['index']
    curTrial = trials[session['index']]
    b1, b2, b3, b4 = False, False, False, False
    if(index != 0):
        b2 = True
    if(index >= 2):
        b1 = True
    if(index != len(trials)-1):
        b3 = True
    if(index <= len(trials)-3):
        b4 = True
    s = ""
    if(b1):
        inDif = min(5, index)
        s += nl('<button type="button" onclick="location.href = &quot;/backFive&quot;;" id="logoutButton">Go back '+str(inDif)+'</button>')
    if(b2):
        s += nl('<button type="button" onclick="location.href = &quot;/backOne&quot;;" id="logoutButton">Go back 1</button>')
    if(b3):
        s += nl('<button type="button" onclick="location.href = &quot;/forOne&quot;;" id="logoutButton">Go forward 1</button>')
    if(b4):
        inDif = min(5, len(trials)-1-index)
        s += nl('<button type="button" onclick="location.href = &quot;/forFive&quot;;" id="logoutButton">Go forward '+str(inDif)+'</button>')
    s += nl('<button type="button" onclick="location.href = &quot;/&quot;;" id="logoutButton">Back to Home</button>')
    return nl("Trial Code: " + curTrial.id) \
            + nl("Trial Title: " + curTrial.title) \
            + nl("Trial Summary: " + curTrial.summary) \
            + s

@app.route('/backOne')
def back_one():
	session['index'] = session['index'] - 1
	return redirect("/displayInfo")
	
@app.route('/forOne')
def for_one():
	session['index'] = session['index'] + 1
	return redirect("/displayInfo")

@app.route('/backFive')
def back_five():
	session['index'] = session['index'] - 5
	session['index'] = max(0, session['index'])
	return redirect("/displayInfo")
	
@app.route('/forFive')
def for_five():
	session['index'] = session['index'] + 5
	session['index'] = min(session['numTrials']-1, session['index'])
	return redirect("/displayInfo")

@app.route('/logout')
def logout():
    session.pop("va_patient", None)
    session.pop("va_access_token", None)
    session.pop("cms_patient", None)
    session.pop("cms_access_token", None)
    return redirect("/")

@cms.tokengetter
def get_cms_token(token=None):
    return session.get('cms_access_token')


@va.tokengetter
def get_va_token(token=None):
    return session.get('va_access_token')
