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


@app.route('/')
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
        make_response(jsonify({'result': 'filename must not empth.'}))

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
        }
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
        <p>Resource << {0} >> is successfully registered!</p>
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


# ---------------------------------------------------------------------- #

@app.route('/req-resource')
def req_resource():
    # rpt がなければ tff-01.ctiport.net:8888/token へ誘導
    if request.args.get('rpt') == None:
        return redirect(url_for('authorize'), code=301)

    rpt = request.args.get('rpt')

    # rpt を検証(tff-01.ctiport.net:8888/intro)
    if rpt != "string":
        return make_response(jsonify({'message': "Invalid RPT"}), 400)

    return make_response(jsonify({'message': "success"}), 200)


@app.route('/authorize')
def authorize():
    return make_response(jsonify({'message': "redirect to tff-01.ctiport.net:8888/token"}), 200)


if __name__ == "__main__":
    # app.run(debug=True)
    app.run(debug=True, host='0.0.0.0', port=8080)
