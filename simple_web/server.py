# -*- coding: utf-8 -*-
from __future__ import division
import os
import subprocess
from flask import Flask, request, url_for, send_from_directory, render_template, make_response
#from werkzeug import secure_filename
#import sqlite3
from flask import g
import datetime
import random
import string
from multiprocessing import Pool, Process
import glob
import traceback
import json
import time
from psycopg2 import connect
from settings import modeDictionary

# Fix the disgusting code problem
# We should consider about python3
import psycopg2
import psycopg2.extensions
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

import re
import utility.excel

os.environ["PYTHONPATH"] = os.environ.get(
    "PYTHONPATH", "") + ":{}/../ocr/src/".format(os.path.dirname(__file__))
table_list = ['standard', 'answer', 'testInfo', 'errorInfo']
from processor.interface import recognizeJPG
from processor.utility.ocr import pdf2jpg, getPDFPageNum

ANSWER_FILE_NAME = "standard.pdf"


def getDiskUsage():
    command = '''df $PWD/file_storage | tail -n 1 | awk {'print $5'}'''
    return int(float(os.popen(command).read().strip().strip("%")))


def countQuestion(standard):
    # print standard
    standard = standard["result"]['answer']
    num_question = len(standard)
    while standard[num_question - 1] == '-':
        num_question -= 1
    return num_question


def isValidToken(token):
    return re.match("^\d{14}[a-zA-Z0-9]{10}$", token)


def isValidNameFilename(filename):
    return re.match("^\d{14}[a-zA-Z0-9]{10}.png$", filename)


def isValidStandardAnswerFilename(filename):
    return filename.startswith("standard") \
        and filename.endswith(".jpg") \
        and filename.count('.') == 1 \
        and filename.count('/') == 0


def isValidAnswersheetFilename(filename):
    return filename.startswith("student_") \
        and filename.endswith(".jpg") \
        and filename.count('.') == 1 \
        and filename.count('/') == 0


def getDb():
    # db = getattr(g, '_database', None)
    # if db is None:
        # db = g._database = sqlite3.connect(DATABASE)
        # db = g._database = connect(database='postgres', host='localhost:5432', user='heqing', password='heqing')
    db = connect(database='kejinyan', host='localhost',
                 user='kejinyan', password='kejinyan')
    return db


def getConfig(key):
    try:
        db = getDb()
        c = db.cursor()
        c.execute("select value from globalConfig where key = %s;", (key, ))
        t = c.fetchone()[0]
        db.close()
        return t
    except:
        traceback.print_exc()
    return ''


def setConfig(key, value):
    command = "update globalConfig set value = %s where key = %s;"
    db = getDb()
    c = db.cursor()
    c.execute(command, (value, key))
    db.commit()
    db.close()


def generateToken():
    return datetime.datetime.now().strftime("%Y%m%d%H%M%S") \
        + "".join([random.choice(string.uppercase + string.lowercase + string.digits)
                   for i in range(0, 10)])

ALLOWED_EXTENSIONS = set(['pdf'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'file_storage')
app.config['ASSETS_FOLDER'] = os.path.join(os.getcwd(), 'templates', 'assets')
app.config['NAME_FOLDER'] = os.path.join('/var/tmp/')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024


os.system("mkdir -p {}".format(app.config['UPLOAD_FOLDER']))
#app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def recognizeAnswersheet(token, answersheetPath, answersheetType):
    db = getDb()
    c = db.cursor()
    result = recognizeJPG(answersheetPath, answersheetType, os.path.join(
        app.config['UPLOAD_FOLDER'], token, 'name'))
    c.execute('insert into answer values (%s, %s);',
              (token, json.dumps(result)))
    if result['status'] == 'error':
        c.execute("insert into errorInfo values (%s, %s, %s);",
                  (token, result['path'], result['message']))
    c.execute('update testInfo set processed=processed+1 where token=%s;',
              (token, ))
    db.commit()
    db.close()


def convert_and_recognize(token, paths, answersheet_type):
    db = getDb()
    c = db.cursor()

    task_dir = os.path.join(app.config['UPLOAD_FOLDER'], token)
    pool = [Process(target=pdf2jpg, args=(path,)) for path in paths]
    for p in pool:
        p.start()
    for p in pool:
        p.join()

    teacher_path = os.path.join(task_dir, 'teacher')
    student_path = os.path.join(task_dir, 'student')
    teacher_files = glob.glob("{}/*.jpg".format(teacher_path))
    student_files = glob.glob("{}/*.jpg".format(student_path))

    standard = recognizeJPG(teacher_files[0], answersheet_type)
    c.execute('insert into standard values (%s, %s);',
              (token, json.dumps(standard)))
    db.commit()

    if standard['status'] == "error":
        c.execute("insert into errorInfo values (%s, %s, %s);",
                  (token, standard['path'], standard['message']))
        db.commit()
    db.close()
    pool = [Process(target=recognizeAnswersheet, args=(
        token, path, answersheet_type)) for path in student_files]
    maxPoolSize = 1
    i = 0
    for path in student_files:
        recognizeAnswersheet(token, path, answersheet_type)


def getPageNumList(filepath_list):
    return [getPDFPageNum(path) for path in filepath_list]


def render_result(standard, answer):
    result = list()
    student_choice = answer['answer']
    correct_choice = standard['answer']
    num_question = len(correct_choice)
    while correct_choice[num_question - 1] == '-':
        num_question -= 1
    for i in range(num_question):
        color = "red"
        if correct_choice[i] == student_choice[i]:
            color = "green"
        result.append(''.format(color, student_choice[i].replace('-', "?")))
    return result


@app.route('/history')
def getHistory():
    db = getDb()
    cur = db.cursor()
    cur.execute('select * from testInfo order by time desc;')
    records = cur.fetchall()
    records = [{'order': t[6],
                'token': t[0],
                'processed': t[1],
                'total': t[2],
                'time': t[4],
                'note': t[5],
                'type': modeDictionary[t[3]],
                'judgeMode': modeDictionary[t[7]]} for t in records]
    for record in records:
        cur.execute('select count(*) from errorInfo where token = %s',
                    (record['token'],))
        errorCount = cur.fetchone()
        errorCount = errorCount[0] if errorCount else 0
        record['errorCount'] = errorCount
    db.close()
    return render_template('history.html', records=records, diskUsage=getDiskUsage())


@app.route('/table/<token>/result.xlsx')
def returnTable(token):
    if not isValidToken(token):
        return json.dumps({"status": 403, "message": "Don't try to hack me."}), 403

    xlsx_path = os.path.join(app.config['UPLOAD_FOLDER'], token, 'table.xlsx')
    if not os.path.isfile(xlsx_path):
        db = getDb()
        cur = db.cursor()
        cur.execute(
            "select judgeMode, type from testInfo where token = %s;", (token, ))
        t = cur.fetchone()
        partialCredit = t[0] == u'partial'
        testType = t[1]
        cur.execute("select value from answer where token = %s;", (token,))
        t = cur.fetchall()
        t = list(map(lambda x: json.loads(x[0]), t))
        t = filter(lambda x: "result" in x, t)
        answers = list(map(lambda x: x['result'], t))
        cur.execute("select value from standard where token = %s;", (token,))
        record = cur.fetchone()
        standard = json.loads(record[0])['result']
        t = len(standard['answer']) - 1
        while standard['answer'][t] == '-':
            t -= 1
        standard['answer'] = standard['answer'][:t + 1]
        utility.excel.generateXlsx(
            xlsx_path, standard['answer'], answers, partialCredit=partialCredit, testType=testType)
        db.close()
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], token), 'table.xlsx')


@app.route('/favicon.ico')
def returnFavicon():
    return send_from_directory("templates", "favicon.ico")


@app.route('/progress/<token>')
def getProgress(token):
    db = getDb()
    cur = db.cursor()
    cur.execute(
        "select processed, total from testInfo where token = %s;", (token, ))
    t = cur.fetchone()
    db.close()
    processed, total = t if t else (0, 1)

    task_dir = os.path.join(app.config['UPLOAD_FOLDER'], token)
    student_filedir = os.path.join(task_dir, 'student')

    student_files = glob.glob("{}/*.jpg".format(student_filedir))
    num_converted = len(student_files)

    # we include the conversion part into progress bar, original formula is:
    # percentage = 100 * (processed + num_converted) / (total + total)
    return json.dumps({"processed": processed,
                       "total": total,
                       "percentage": 50 * (processed + num_converted) / total})


@app.route('/standardanswer/<token>')
def getStandardAnswer(token):
    if not isValidToken(token):
        return json.dumps({"status": 403, "message": "Don't try to hack me."}), 403
    answersheet_dir = os.path.join(
        app.config['UPLOAD_FOLDER'], token, 'teacher')
    try:
        answersheet_name = os.path.basename(
            sorted(glob.glob(answersheet_dir + '/*.jpg'))[0])
    except:
        answersheet_name = ''
    return send_from_directory(answersheet_dir, answersheet_name)


@app.route('/answersheet/<token>/<filename>')
def getAnswerSheet(token, filename):
    if not isValidAnswersheetFilename(filename) or not isValidToken(token):
        return json.dumps({"status": 403, "message": "Don't try to hack me."}), 403
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], token, 'student'), filename)


@app.route('/render/<token>')
def renderResults(token):
    def render_ratio(params, num_question):
        '''
        render param list [(correct, total, ratio, width, serial_number), ...]
        '''
        return render_template('statistics.html', params=params, token=token)

    def render_students(correctness):
        '''
        correctness: [(id, num_correct, num_question, err_list), ...]
        '''
        result = render_template('scores.html', info=correctness, token=token)
        return result

    def row_class(correct_ratio):
        if correct_ratio > 0.9:
            return "success"
        elif correct_ratio > 0.5:
            return "info"
        elif correct_ratio > 0.3:
            return "warning"
        else:
            return "danger"

    db = getDb()
    cur = db.cursor()
    cur.execute("select value from standard where token = %s;", (token,))
    standard = cur.fetchone()
    if not standard:
        return json.dumps({"empty": True})
    else:
        cur.execute("select value from answer where token = %s;", (token,))
        t = cur.fetchall()
        t = list(map(lambda x: json.loads(x[0]), t))
        t = filter(lambda x: "result" in x, t)
        _answers = list(map(lambda x: x['result'], t))

        cur.execute("select path from errorInfo where token = %s;", (token,))
        t = cur.fetchall()
        _paths = [u"<li><a target=\"_blank\" href=\"/answersheet/{}/{}\">点击查看</a></li>".format(
            token, os.path.basename(x[0])) for x in t if x]

        # _answers = list(map(lambda x: json.loads(x[0])['result'], cur.fetchall()))
        # print _answers
        standard = json.loads(standard[0])
        # print standard
        correct_ratio = list()
        answers = list()
        num_question = countQuestion(standard)
        correctness = list()
        if _answers:
            for i in range(num_question):
                # print standard, _answers
                correct_count = sum(map(lambda x: x['answer'][i] == standard[
                                    'result']['answer'][i], _answers))
                student_mistake_index = [index for index in range(len(_answers))
                                         if _answers[index]['answer'][i] != standard['result']['answer'][i]]
                student_mistake_info = [(_answers[k]['id'],
                                         os.path.basename(_answers[k]['name_image'])) for k in student_mistake_index]
                correct_ratio.append((correct_count,
                                      len(_answers),
                                      100 * correct_count / len(_answers),
                                      row_class(correct_count / len(_answers)),
                                      i + 1,
                                      student_mistake_info))
            for student in _answers:
                num_correct = 0
                err_list = list()
                for i in range(num_question):
                    if student['answer'][i] != standard['result']['answer'][i]:
                        err_list.append(i + 1)
                    else:
                        num_correct += 1
                err_list = u", ".join(map(lambda x: unicode(x), err_list))
                correctness.append((student['id'],
                                    num_correct,
                                    num_question,
                                    err_list,
                                    os.path.basename(student['name_image']),
                                    os.path.basename(student['file_path'])))
            correctness.sort()
        db.close()
        # print render_ratio(correct_ratio, num_question)
        return json.dumps({"stats": render_ratio(correct_ratio, num_question),
                           "scores": render_students(correctness),
                           "hasError": bool(_paths),
                           "errors": "\n".join(_paths)})


@app.route('/name/<token>/<filename>')
def getNameImage(token, filename):
    if not isValidNameFilename(filename):
        return json.dumps({"status": 403, "message": "Don't try to hack me."}), 403
    dirname = os.path.join(app.config['UPLOAD_FOLDER'], token, 'name')
    return send_from_directory(dirname, filename)


@app.route('/assets/<path:filename>')
def getAssets(filename):
    path = os.path.join(app.config['ASSETS_FOLDER'], filename)
    dirname = os.path.dirname(path)
    file_name = os.path.basename(path)
    return send_from_directory(dirname, file_name)


@app.route('/delete/<token>', methods=["POST"])
def deleteFolder(token):
    if not isValidToken(token):
        return json.dumps({"status": 403, "message": "Don't try to hack me."}), 403
    os.system(
        "rm -rf {}".format(os.path.join(app.config['UPLOAD_FOLDER'], token)))
    db = getDb()
    cur = db.cursor()
    for table in table_list:
        cur.execute('delete from {} where token = %s;'.format(table), (token,))
    db.commit()
    db.close()
    return json.dumps({"status": "success"}), 200


@app.route('/clear', methods=["POST"])
def clearFolder():
    db = getDb()
    cur = db.cursor()
    cur.execute("select token from testInfo;")
    t = cur.fetchall()
    tokens = set([x[0] for x in t])
    folder_names = [os.path.basename(os.path.normpath(name))
                    for name in glob.glob(app.config['UPLOAD_FOLDER'] + "/*/")]
    print(folder_names, tokens)
    for name in folder_names:
        if name not in tokens:
            os.system(
                "rm -rf {}".format(os.path.join(app.config['UPLOAD_FOLDER'], name)))
            print("deleted {}".format(os.path.join(
                app.config['UPLOAD_FOLDER'], name)))

    for token in tokens:
        if token not in folder_names:
            for table in table_list:
                cur.execute(
                    'delete from {} where token = %s;'.format(table), (token,))
    db.commit()
    db.close()
    return json.dumps({"status": "success"}), 200


@app.route('/results/<token>')
def get_results(token):
    if not isValidToken(token):
        return json.dumps({"status": 403, "message": "Don't try to hack me."}), 403

    db = getDb()
    cur = db.cursor()
    cur.execute("select value from standard where token = %s;", (token,))
    t = cur.fetchone()
    cur.execute(
        "select type, judgeMode from testInfo where token = %s;", (token, ))
    mode = cur.fetchone()
    if t:
        t = json.loads(t[0])
        status = t['status']
        if status == "error":
            return u"标准答案识别出错，请确认答题卡类型选择正确：<br/><ul><li>答题卡类型：{}</li><li>评分模式：{}</li></ul><br/>同时请确保扫描件的三个定位块完整清晰，可尝试重新扫描。<br/>如仍有问题，\
                请把此网页链接及原始文件发送给客服，以便改进。\
                 <br /><pre>Email: 793048@qq.com QQ: 793048 </pre><br/><pre>".format(modeDictionary[
                mode[0]], modeDictionary[mode[1]]) \
                + u"</pre><br/><img src=/standardanswer/{} width=50%/>".format(token)
    else:
        cur.execute("select * from testInfo where token = %s;", (token,))
        t = cur.fetchone()
        if not t:
            return render_template('redirect.html', message=[u'结果不存在，地址有误或记录已被删除'],
                                   url='/',
                                   time=5)
    cur.execute(
        "select processed, total from testInfo where token = %s;", (token, ))
    t = cur.fetchone()
    processed, total = t if t else (0, 1)
    if processed:
        cur.execute("select value from answer where token = %s;", (token,))
        t = cur.fetchall()
        t = list(map(lambda x: json.loads(x[0]), t))
        t = filter(lambda x: "result" in x, t)
        answers = list(map(lambda x: x['result'], t))
        # answers = list(map(lambda x: json.loads(x[0])['result'], cur.fetchall()))
        cur.execute("select value from standard where token = %s;", (token,))
        standard = json.loads(cur.fetchone()[0])
        # print standard
        num_question = countQuestion(standard)
        standard['answer'] = standard['result']['answer'][:num_question]
        for answer in answers:
            answer['answer'] = render_result(standard, answer)
    else:
        standard = answers = {"answer": [], "id": ""}
        num_question = 0
    db.close()
    return render_template('result.html',
                           processed=processed,
                           total=total,
                           standard=standard,
                           answers=answers,
                           token=token,
                           colnum=range(1, num_question + 1))


# @app.route('/uploads/download/<filename>')
# def uploaded_file(filename):
#     return send_from_directory(app.config['UPLOAD_FOLDER'],
#                                filename)
def tokenExists(token):
    db = getDb()
    c = db.cursor()
    c.execute("select count(*) from testInfo where token = %s;", (token,))
    result = c.fetchone()[0]
    db.close()
    return result != 0


@app.route('/upload/', methods=['POST'])
def upload():
    token = request.form['token']
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], token)
    if not isValidToken(token) or tokenExists(token):
        return json.dumps({"status": 403, "message": "Don't try to hack me."}), 403

    if 'standard' in request.files:
        os.system("mkdir -p {}".format(os.path.join(upload_path, 'teacher')))
        os.system("mkdir -p {}".format(os.path.join(upload_path, 'name')))
        request.files['standard'].save(os.path.join(
            upload_path, 'teacher', ANSWER_FILE_NAME))
    elif 'answers' in request.files:
        os.system("mkdir -p {}".format(os.path.join(upload_path, 'student')))
        answers = request.files.getlist('answers')
        for f in answers:
            if allowed_file(f.filename):
                f.save(os.path.join(upload_path, 'student',
                                    'student_{}.pdf'.format(generateToken())))
    return json.dumps({"status": 200, "message": "file sucessfully uploaded"}), 200


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "GET":
        validationUrl = getConfig('validationUrl')
        registrationCode = getConfig('registrationCode')
        return render_template('register.html',
                               validationUrl=validationUrl,
                               registrationCode=registrationCode,
                               isValid=isRegistered())
    elif request.method == "POST":
        validationUrl = request.form.get('validationUrl', '')
        registrationCode = request.form.get('registrationCode', '')
        setConfig('validationUrl', validationUrl)
        setConfig('registrationCode', registrationCode)
        waitingTime = 10  # seconds
        return render_template('redirect.html', message=[u'正在激活中，若成功将跳转到首页……请等待{}秒'.format(waitingTime)],
                               url="/",
                               time=waitingTime)


def isRegistered():
    return True
    return getConfig('valid') == 'true'


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if not isRegistered():
        return render_template('redirect.html', message=[u'产品尚未激活，3秒后转到注册页面'],
                               url="/register",
                               time=3)
    message = []
    if request.method == "GET":
        token = generateToken()
    elif request.method == "POST":
        token = request.values['token']
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], token)
    if request.method == "GET" and request.values.get('upload') == 'true':
        return render_template("index.html", token=token, popover=True)
    elif request.method == 'POST' and request.values['answersheettype'] in ['full',
                                                                            'half',
                                                                            # 'full_old',
                                                                            # 'half_old',
                                                                            # 'makesi',
                                                                            'makesi_new',
                                                                            'gk_english',
                                                                            'full_4option']:
        success = True
        task_dir = os.path.join(app.config['UPLOAD_FOLDER'], token)
        note = request.values.get('note', '')
        teacher_filepath = os.path.join(task_dir, 'teacher', ANSWER_FILE_NAME)
        student_filedir = os.path.join(task_dir, 'student')
        try:
            teacher_pagenum = getPDFPageNum(teacher_filepath)
            if teacher_pagenum == 1:
                message.append(u"标准答案文件上传成功，正在处理中……")
            elif teacher_pagenum > 1:
                message.append(u"标准答案文件超过一页，任取一页作为答案……")
            else:
                message.append(u"似乎标准答案的页数为0？你别逗我啊……")
        except IndexError:
            success = False
            message.append("没有有效的标准答案文件，请检查后重新上传")
        db = getDb()
        c = db.cursor()
        c.execute("select * from testInfo where token = %s;", (token, ))
        t = c.fetchone()
        if t:
            return json.dumps({"status": 403, "message": "考试记录已存在，请尝试回到主页刷新重新上传。"}), 403
        c.execute("insert into testInfo (token, processed, total, type, note, judgeMode) values (%s, 0, %s, %s, %s, %s);",
                  (token, 1, request.values['answersheettype'], note, request.values['judgeMode']))
        db.commit()
        student_files = glob.glob("{}/*.pdf".format(student_filedir))
        student_page_nums = getPageNumList(student_files)
        total_page_num = sum(student_page_nums)
        if success and total_page_num:
            p = Process(target=convert_and_recognize,
                        args=(token,
                              [teacher_filepath] + student_files,
                              request.values['answersheettype']))
            c.execute("update testInfo set total = %s where token = %s;",
                      (total_page_num, token))
            p.start()
            message.append(u"答题卡上传成功，正在处理中……")
            invalid_file_count = student_page_nums.count(0)
            if invalid_file_count > 0:
                message.append(
                    u"存在{}个无效的答题卡文件，已忽略这些文件。请检查您上传的答题卡文件。".format(invalid_file_count))
        else:
            success = False
            message = [u"没有提交有效的答题卡文件，请检查您提交的答题卡文件是否有效。"]
            # displaying succeed message makes client confused
            # reserve only error message

        pause_time = 3 if success else 5

        db.commit()
        db.close()

        return render_template('redirect.html',
                               message=message,
                               url='/' if not success else '/results/{}'.format(
                                   token),
                               time=pause_time)
    else:
        return render_template('index.html',
                               token=token,
                               popover=False)


def init():
    DATABASE_INIT = ['create table if not exists standard (token text primary key, value text);',
                     'create table if not exists answer (token text, value text);',
                     'create table if not exists testInfo (token text primary key, processed int, total int, type text, time timestamp default current_timestamp, note text default \'\', number serial, judgeMode text);',
                     'create table if not exists errorInfo (token text, path text, message text);',
                     'create table if not exists globalConfig (key text primary key, value text);',
                     'insert into globalConfig values (\'valid\', \'true\') on conflict do nothing;',
                     'insert into globalConfig values (\'validationUrl\', \'\') on conflict do nothing;',
                     'insert into globalConfig values (\'registrationCode\', \'\') on conflict do nothing;']
    db = getDb()
    c = db.cursor()
    for statement in DATABASE_INIT:
        c.execute(statement)
    db.commit()
    db.close()


if __name__ == '__main__':
    init()
    app.run(host="0.0.0.0", port=3389, debug=True)
    # app.run(host="0.0.0.0", threaded=True)
