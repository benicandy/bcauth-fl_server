from flask import Flask, render_template, make_response, request, jsonify
from flask import abort, redirect, url_for
from jinja2 import Template

import urllib.request
import zipfile

import os
import json
import werkzeug
from datetime import datetime

app = Flask(__name__)

# FL-Server API

# limited upload file size: 100MB
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024 * 100


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
        return make_response(jsonify({'result': 'uploadFile is required.'}))
    file = request.files['uploadFile']
    filename = file.filename
    if '' == filename:
        return make_response(jsonify({'result': 'filename must not be empty.'}))

    try:
        saveFileName = datetime.now().strftime("%Y%m%d_%H%M%S_") \
            + werkzeug.utils.secure_filename(filename)
        file.save(os.path.join(UPLOAD_DIR+"/"+uid, saveFileName))
    except:
        return make_response(jsonify({'response': "error: invalid user id"}))

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
    <p>ユーザID: {0}</p>
    <h2>リソース一覧</h2>
    <p> tff スコープを許可するリソースを＜一つ＞選択する．</p>
    <form action="/reg-resource" method="post">
    """
    html += '<input type="hidden" name="pat" value=' + pat + '><br>\n'
    for i in range(len(li_files)):
        html += '<input type="checkbox" name="check" value=' \
            + li_files[i] + '>' + li_files[i] + '<br>\n'

    html += """
        <br>
        <input type="hidden" name="uid" value={0}>
        <input type="submit" name="register">
    </form>
    </body>

    </html>
    """.format(uid)

    return template.render()


@app.route('/reg-resource', methods=['post'])
def reg_resource_post():
    # RS は指定されたリソースを AB に登録する
    # ＊注意＊ リソース選択が一つの場合しか実現できていないので，要修正

    # PAT を受け取る
    pat = request.form['pat']
    # 選択したリソース名を受け取る
    checks = request.form.getlist('check')
    # uid を受け取る
    uid = request.form['uid']

    # リソースを AB に登録するリクエストを生成する(tff-01.ctiport.net:8888/rreg)
    rreg_url = 'http://tff-01.ctiport.net:8888/rreg'
    data = {
        'resource_description': {
            'resource_scopes': ['tff'],
            'description': "sample_dataset",
            'icon_uri': "",
            'name': uid + '/' + checks[0],
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
    # RPT を検証後，RqP の ACL を作成・更新する
    """
    :req_header Content-Type application/json:
    :req_header Authorization Bearer: RPT
    :req_param string resource_id: 要求するリソースの ID
    :req_param list resource_scopes: 要求するリソースのスコープ
    """
    # ヘッダをチェック
    if not request.headers.get('Content-Type') == 'application/json':
        error_message = {
            'error': 'not supported Content-Type'
        }
        return make_response(json.dumps({'response': error_message}), 400)
    try:
        header_authz = request.headers.get('Authorization')
        bearer = header_authz.split('Bearer ')[-1]
    # rpt がなければ tff-01.ctiport.net:8888/token へ誘導
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
    intro_req = urllib.request.Request(
        url=intro_url, data=json.dumps(data).encode('utf8'), headers=headers)

    # Request to http://tff-01.ctiport.net:8888/intro
    with urllib.request.urlopen(intro_req) as res:
        body = res.read()
        body = body.decode('utf8').replace("'", '"')
        body = json.loads(body)

    # RPT の情報を取り出す
    try:
        active = body['response']['Active']  # RPT がアクティブか否か
        expire = body['response']['Expire']  # RPT の有効期限
        li_permissions = body['response']['Permissions']  # 許可されるパーミッションのリスト
    except:
        err_msg = body['response']
        return make_response(json.dumps({'response': err_msg}), 400)

    print("response: ", body['response'])

    # active に関する処理
    # some process

    # expire に関する処理
    # some process

    # li_permissions (include 'resource_id', 'expire', 'resource_scopes')に関する処理
    # 条件を満たすリソース名の一覧を作成

    # PAT の呼び出し（方法は未定）
    # (ro01, rs) - rid = 08db20ba-2666-5b91-9bef-3d5b7d9138ae
    pat = "0xddb5ab8c5405830359d2af4ec8d4bdf27bc4b8ee7d20f64ec1a71a634e551"
    # (ro02, rs) - rid = 1c1f1d9f-051c-592f-bb06-5ec8cef664ba
    #pat = "0x23e6958b1f555b905ade2f915c8c64453bd9514c4e1750d995f17215cbc4"

    permitted_resources = []
    for perm in li_permissions:
        # expire に関する処理
        # some process

        # resource_id と resource_scopes に関する処理
        # Step 1. リソース ID とそのスコープを抽出
        resource_id = perm['ResourceId']
        resource_scopes = perm['ResourceScopes']

        # Step 2. スコープに 'tff' が含まれて入れば，リソース ID からリソース名を呼び出す(from tff-01.ctiport.net)
        flag = False
        for e in resource_scopes:
            if e == 'tff':
                flag = True

        if flag:
            rreg_endpoint = "http://tff-01.ctiport.net:8888/rreg-call"
            data = {
                'resource_id': resource_id
            }
            headers = {
                'Content-Type': 'application/json',
                'Authorization': "Bearer {}".format(pat)
            }
            rreg_req = urllib.request.Request(
                url=rreg_endpoint,
                data=json.dumps(data).encode('utf8'),
                headers=headers
            )
            # Request to http://tff-01.ctiport.net:8888/rreg-call
            with urllib.request.urlopen(rreg_req) as res:
                body = res.read()
                body = body.decode('utf8').replace("'", '"')
                body = json.loads(body)
                name = body['response']['name']  # リソース名

        # Step 3. リソース名をリストに格納
        DIR = './uploaded/'  # データディレクトリ
        permitted_resources.append(DIR + name)

    # リソースの zip を作成する
    print("permitted_resources: ", permitted_resources)
    ZIP_DIR = './resource_zip/'
    FILENAME = 'resource.zip'
    ZIP_PATH = ZIP_DIR + FILENAME
    with zipfile.ZipFile(ZIP_PATH, 'w', compression=zipfile.ZIP_DEFLATED) as new_zip:
        DIR = './uploaded/'
        for name in permitted_resources:
            ARC_PATH = DIR + name
            new_zip.write(ZIP_PATH, arcname=ARC_PATH)
    
    # Client にダウンロードさせる
    downloadFile = ZIP_PATH
    downloadFileName = FILENAME
    ZIP_MIMETYPE = 'application/json'
    
    response = make_response()
    response.data = open(downloadFile, 'rb').read()
    response.headers = ['Content-Disposition'] = 'attachment; filename=' + downloadFileName
    response.mimetype = ZIP_MIMETYPE
    return response

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


@app.route('/train-model', methods=['post'])
def train_model():
    
    # tff モジュールにデータを与えてモデルを作成する
    import my_fl_server
    model = my_fl_server.federated_train(permitted_resources)
    # model を返す（要修正）
    return make_response(json.dumps({'response': body['response']}), 200)


if __name__ == "__main__":
    # app.run(debug=True)
    app.run(debug=True, host='0.0.0.0', port=8080)
