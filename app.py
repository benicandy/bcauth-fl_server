from flask import Flask, render_template, make_response, request, jsonify
from flask import abort, redirect, url_for
from jinja2 import Template

import urllib.request

import os
import json
import werkzeug
from datetime import datetime

app = Flask(__name__)

# FL-Server API

# limited upload file size: 1MB
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

UPLOAD_DIR = "./uploaded"


@app.route('/fl-server')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['post'])
def upload():

    if 'uid' not in request.form['uid']:
        make_response(jsonify({'result': 'user id is required.'}))
    uid = request.form['uid']

    if 'uploadFile' not in request.files:
        make_response(jsonify({'result': 'uploadFile is required.'}))
    file = request.files['uploadFile']
    filename = file.filename
    if '' == filename:
        make_response(jsonify({'result': 'filename must not be empty.'}))

    os.makedirs(UPLOAD_DIR + "/" + uid, exist_ok=True)

    saveFileName = datetime.now().strftime("%Y%m%d_%H%M%S_") \
        + werkzeug.utils.secure_filename(filename)
    file.save(os.path.join(UPLOAD_DIR+"/"+uid, saveFileName))

    return render_template('upload.html', name=filename)


@app.route('/redirect-pat', methods=['post'])
def redirect_pat():
    return redirect('http://tff-01.ctiport.net:8888/pat', code=301)
    # return redirect('https://www.google.com', code=301)


@app.route('/reg-resource')
def reg_resource():
    # RO が AB に登録したいリソースを指定できるように

    # uid を受け取る
    if request.args.get('uid') != "":
        uid = request.args.get('uid')
    else:
        return jsonify({'message': 'forbidden'}), 403
    # PAT を受け取る
    if request.args.get('pat') != "":
        pat = request.args.get('pat')
    else:
        return jsonify({'message': 'forbidden'}), 403

    # リソース一覧を取得
    path = "./uploaded/" + uid
    try:
        files = os.listdir(path)
    except:
        return jsonify({'message': 'forbidden'}), 403
    li_files = [f for f in files if os.path.isfile(os.path.join(path, f))]

    # checkbox の value を動的に与える方法がわからなかったので python で毎回 html を生成して解決
    html = """
    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 
    Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml">

    <head>
    <title></title>
    </head>

    <body>
    <h1>Reg API</h1>
    <p>ユーザID: {{ uid }}</p>
    <h2>リソース一覧</h2>
    <p> read スコープを許可するリソースを＜一つ＞選択する．</p>
    <form action="/reg-resource" method="post">
    """
    html += '<input type="hidden" name="pat" value=' + pat + '><br>\n'
    for i in range(len(li_files)):
        html += '<input type="checkbox" name="check" value=' \
            + li_files[i] + '>' + li_files[i] + '<br>\n'

    html += """
        <br>
        <input type="submit" name="register">
    </form>
    </body>

    </html>
    """

    template = Template(html)
    data = {'uid': uid}

    return template.render(data)


@app.route('/reg-resource', methods=['post'])
def reg_resource_post():
    # RS は指定されたリソースを AB に登録する
    # ＊注意＊ リソース選択が一つの場合しか実現できていないので，要修正

    # PAT を受け取る
    pat = request.form['pat']
    # 選択したリソース名を受け取る
    checks = request.form.getlist('check')

    # リソースを AB に登録するリクエストを生成する(tff-01.ctiport.net:8888/rreg)
    rreg_url = 'http://tff-01.ctiport.net:8888/rreg'
    data = {
        'resource_description': {
            'resource_scopes': ['read'],
            'description': "sample dataset",
            'icon_uri': "",
            'name': checks[0],
            'type': ""
        },
        'timestamp': "1595230979",
        'timeSig': "vF9Oyfm+G9qS4/Qfns5MgSZNYjOPlAIZVECh2I5Z7HHgdloy5q7gJoxi7c1S2/ebIQbEMLS05x3+b0WD0VJfcWSUwZMHr3jfXYYwbeZ1TerKpvfp1j21nZ+OEP26bc28rLRAYZsVQ4Ilx7qp+uLfxu9X9x37Qj3n0CI2TEiKYSSYDQ0bftQ/3iWSSoGjsDljh9bKz1eVL911KeUGO+t/9IkB6LtZghdbIlnGISbgrVGoEOtGHi0t8uD2Vh/CRyBe+XnQV3HQtkjddLQitAesKTYunK1Ctia3x7klVjRH9XiJ11q6IbR8gz7rchdHYZe6HP+w/LyWMS5z6M26AXQrVw=="
    }
    headers = {
        'Authorization': 'Bearer {}'.format(pat),
        'Content-Type': 'application/json'
    }
    req = urllib.request.Request(url=rreg_url, data=json.dumps(
        data).encode("utf-8"), headers=headers)

    # リクエストを投げてレスポンスを得る
    with urllib.request.urlopen(req) as res:
        body = res.read()
        body = body.decode('utf8').replace("'", '"')
        print("body: ", body)
        body = json.loads(body)
        print("body: ", body)
        resource_id = body['response']['resource_id']

    # リソース ID を表示し，ポリシー設定エンドポイントへ誘導する
    html = """
    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 
    Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml">

    <head>
        <title></title>
    </head>

    <body>
        <h1>FL-Server Upload Form for RO</h1>
        <p>認可ブロックチェーンにリソースが登録されたので，ポリシーを設定する．</p>
        <br>
        <p>Resource << {0} >> is successfully registered.</p>
        <br>
        <h2>ポリシー設定エンドポイントに移動して，ポリシーを設定します．</h2>
        <form action="/set-policy" method="post">
            <button type="submit" value="set-policy">set policy</button>
            <input type="hidden" name="resource" value={1}>
            <input type="hidden" name="rid" value={2}>
        </form>
    </body>

    </html>
    """.format(checks[0], checks[0], resource_id)

    template = Template(html)

    return template.render()


@app.route('/set-policy', methods=['post'])
def set_policy():
    # RO は登録されたリソースにポリシーを設定する
    resource = request.form['resource']
    rid = request.form['rid']
    # RO を tff-01.ctiport.net:8888/policy に誘導する
    param = {'resource': resource, 'rid': rid}
    qs = urllib.parse.urlencode(param)
    return redirect('http://tff-01.ctiport.net:8888/policy?' + qs, code=301)


# --- リソースアクセスフェーズ ---------------------------------------------------- #

@app.route('/resource', methods=['post'])
def req_resource():
    """
    :req_header Content-Type application/json:
    :req_header Authorization Bearer: RPT
    :req_param string resource_id: 要求するリソースの ID
    :req_param list resource_scopes: 要求するリソースのスコープ
    """
    # rpt がなければ tff-01.ctiport.net:8888/token へ誘導
    # -> 現状，通信相手は backend としているので，リダイレクトではなく uri を示す
    if not request.headers.get('Content-Type') == 'application/json':
        error_message = {
            'error': 'not supported Content-Type'
        }
        return make_response(json.dumps({'response': error_message}), 400)
    try:
        header_authz = request.headers.get('Authorization')
        bearer = header_authz.split('Bearer ')[-1]
    except:
        body = request.get_data().decode('utf8').replace("'", '"')
        body = json.loads(body)

        rid = body['resource_id']
        request_scopes = body['request_scopes']
        param = {
            'resource_id': rid,
            'request_scopes': request_scopes
        }
        qs = urllib.parse.urlencode(param)
        return redirect(url_for('authorize') + '?' + qs, 301)

    # rpt を検証(tff-01.ctiport.net:8888/intro)
    intro_url = "http://tff-01.ctiport.net:8888/intro"
    data = {
        'access_token': bearer
    }
    headers = {
        'Content-Type': 'application/json'
    }
    intro_req = urllib.request.Request(url=intro_url, data=json.dumps(data).encode('utf8'), headers=headers)
    
    # Request to http://tff-01.ctiport.net:8888/intro
    with urllib.request.urlopen(intro_req) as res:
        body = res.read()
        body = body.decode('utf8').replace("'", '"')
        body = json.loads(body)
    
    try:
        active = body['response']['Active']
        expire = body['response']['Expire']
        permissions = body['response']['Permissions']
    except:
        err_msg = body['response']
        return make_response(json.dumps({'response': err_msg}), 400)

    return make_response(json.dumps({'response': body['response']}), 200)


@app.route('/authorize')
def authorize():
    # パラメータの受け取り
    rid = request.args.get('resource_id')
    _scopes = request.args.get('request_scopes')
    _scopes = _scopes.replace("[", "").replace(
        "]", "").replace("'", "").strip()  # 文字列処理
    print("_scopes: ", _scopes)
    try:
        # スコープが複数ある場合
        request_scopes = _scopes.split(",")
    except:
        request_scopes = [_scopes]

    # 認可エンドポイント(/perm)との通信
    perm_url = 'http://tff-01.ctiport.net:8888/perm'
    timestamp = "1595230979"
    timeSig = "vF9Oyfm+G9qS4/Qfns5MgSZNYjOPlAIZVECh2I5Z7HHgdloy5q7gJoxi7c1S2/ebIQbEMLS05x3+b0WD0VJfcWSUwZMHr3jfXYYwbeZ1TerKpvfp1j21nZ+OEP26bc28rLRAYZsVQ4Ilx7qp+uLfxu9X9x37Qj3n0CI2TEiKYSSYDQ0bftQ/3iWSSoGjsDljh9bKz1eVL911KeUGO+t/9IkB6LtZghdbIlnGISbgrVGoEOtGHi0t8uD2Vh/CRyBe+XnQV3HQtkjddLQitAesKTYunK1Ctia3x7klVjRH9XiJ11q6IbR8gz7rchdHYZe6HP+w/LyWMS5z6M26AXQrVw=="
    data = {
        'resource_id': rid,
        'request_scopes': request_scopes,
        'timestamp': timestamp,
        'timeSig': timeSig
    }
    print("data: ", data)
    headers = {
        'Content-Type': 'application/json'
    }
    perm_req = urllib.request.Request(
        url=perm_url, data=json.dumps(data).encode('utf8'), headers=headers)

    # Request to http://tff-01.ctiport.net:8888/perm
    with urllib.request.urlopen(perm_req) as res:
        body = res.read()
        body = body.decode('utf8').replace("'", '"')
        body = json.loads(body)

    try:
        ticket = body['response']['ticket']
    except:
        err_msg = body['response']
        return make_response(json.dumps({'response': err_msg}), 400)
    token_endpoint = "http://tff-01.ctiport.net:8888/token"

    # web client へのレスポンス
    res = {
        'response': {
            'ticket': ticket,
            'token_endpoint': token_endpoint
        }
    }

    return make_response(json.dumps(res), 200)


@app.route('/authorize', methods=['post'])
def authorize_post():
    # rpt がない場合
    return None


if __name__ == "__main__":
    # app.run(debug=True)
    app.run(debug=True, host='0.0.0.0', port=8080)
