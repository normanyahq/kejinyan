# -*- coding: utf-8 -*-
from __future__ import division
import os
from flask import Flask, request, url_for, send_from_directory, render_template, make_response
from werkzeug import secure_filename
import sqlite3
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


os.environ["PYTHONPATH"] = os.environ.get("PYTHONPATH", "") + ":{}/../ocr/src/".format(os.path.dirname(__file__))
from processor.interface import recognizeJPG
from processor.utility.ocr import pdf2jpg, getPDFPageNum

DATABASE_INIT = ['create table if not exists standard (token text, value text);',
    'create table if not exists answer (token text, value text);',
    'create table if not exists status (token text, processed int, total int);',
    'create table if not exists error_list (path text, message text);' ]

def countQuestion(standard):
    # print standard
    standard = standard["result"]['answer']
    num_question = len(standard)
    while standard[num_question-1] == '-':
        num_question -= 1
    return num_question




def get_db():
    # db = getattr(g, '_database', None)
    # if db is None:
        # db = g._database = sqlite3.connect(DATABASE)
        # db = g._database = connect(database='postgres', host='localhost:5432', user='heqing', password='heqing')
    db = connect(database='postgres', host='localhost', user='heqingy', password='heqingy')
    return db


def getToken():
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

def convert_and_recognize(token, paths, answersheet_type):
    db = get_db()
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
    c.execute('insert into standard values (%s, %s);', (token, json.dumps(standard)))
    db.commit()

    if standard['status'] == "error":
        c.execute("insert into error_list values (%s, %s);", (standard['path'], standard['message']))
        db.commit()
    for i, f in enumerate(student_files):
        result = recognizeJPG(f, answersheet_type)
        c.execute('insert into answer values (%s, %s);', (token, json.dumps(result)))
        if result['status'] =='error':
            c.execute("insert into error_list values (%s, %s);", (result['path'], result['message']))
        c.execute('update status set processed=%s where token=%s;', (i+1, token))
        db.commit()

def getTotalPageNum(filepath_list):
    return sum(map(getPDFPageNum, filepath_list))

def render_result(standard, answer):
    result = list()
    student_choice = answer['answer']
    correct_choice = standard['answer']
    num_question = len(correct_choice)
    while correct_choice[num_question-1] == '-':
        num_question -= 1
    for i in range(num_question):
        color = "red"
        if correct_choice[i] == student_choice[i]:
            color = "green"
        result.append(''.format(color, student_choice[i].replace('-', "?")))
    return result

@app.route('/table/<token>')
def returnTable(token):
    cur = get_db().cursor()
    cur.execute("select value from answer where token = %s;", (token,))
    t = cur.fetchall()
    t = list(map(lambda x: json.loads(x[0]), t))
    t = filter(lambda x: "result" in x, t)
    _answers = list(map(lambda x: x['result'], t))
    # _answers = list(map(lambda x: json.loads(x[0])['result'], cur.fetchall()))
    cur.execute("select value from standard where token = %s;", (token,))
    standard = json.loads(cur.fetchone()[0])['result']
    t = len(standard['answer']) - 1
    while standard['answer'][t] == '-':
        t -= 1
    standard['answer'] = standard['answer'][:t+1]
    result = [(u'答案',) +  tuple([(standard['answer'][i], '') for i in range(len(standard['answer']))])]
    t_result = list()
    header = (u'学号',) + tuple([unicode(i+1) for i in range(len(standard['answer']))])
    for ans in _answers:
        t_result.append((ans['id'],) + tuple([(ans['answer'][i],
            'green' if ans['answer'][i] == standard['answer'][i] else 'red') for i in range(len(standard['answer']))]))
    result.extend(sorted(t_result))
    return render_template('table.html', info=result, header=header)



@app.route('/favicon.ico')
def returnFavicon():
    return send_from_directory("templates", "favicon.ico")

@app.route('/progress/<token>')
def getProgress(token):
    db = get_db()
    cur = db.cursor()
    cur.execute("select processed, total from status where token = %s;", (token, ))
    t = cur.fetchone()
    processed, total = t if t else (0, 1)
    return json.dumps({"processed": processed, "total":total, "percentage": 100  * processed / total})


@app.route('/render/<token>')
def renderResults(token):
    def render_ratio(params, num_question):
        '''
        render param list [(correct, total, ratio, width, serial_number), ...]
        '''
        return render_template('statistics.html', params=params)

    def render_students(correctness):
        '''
        correctness: [(id, num_correct, num_question, err_list), ...]
        '''
        result = render_template('scores.html', info=correctness)
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

    db = get_db()
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
                correct_count = sum(map(lambda x: x['answer'][i]==standard['result']['answer'][i], _answers))
                student_mistake_index = [index for index in range(len(_answers))  \
                    if _answers[index]['answer'][i] != standard['result']['answer'][i]]
                student_mistake_info = [(_answers[k]['id'],
                    os.path.basename(_answers[k]['name_image'])) for k in student_mistake_index]
                correct_ratio.append((correct_count,
                    len(_answers),
                    100 * correct_count / len(_answers),
                    row_class(correct_count / len(_answers)),
                    i+1,
                    student_mistake_info))
            for student in _answers:
                num_correct = 0
                err_list = list()
                for i in range(num_question):
                    if student['answer'][i] != standard['result']['answer'][i]:
                        err_list.append(i+1)
                    else:
                        num_correct += 1
                err_list = u", ".join(map(lambda x: unicode(x), err_list))
                correctness.append((student['id'],
                    num_correct,
                    num_question,
                    err_list,
                    os.path.basename(student['name_image'])))
            correctness.sort()
        # print render_ratio(correct_ratio, num_question)
        return json.dumps({"stats": render_ratio(correct_ratio, num_question),
            "scores": render_students(correctness)})

@app.route('/name/<filename>')
def getNameImage(filename):
    return send_from_directory(app.config['NAME_FOLDER'], filename)


@app.route('/assets/<path:filename>')
def getAssets(filename):
    path = os.path.join(app.config['ASSETS_FOLDER'], filename)
    dirname = os.path.dirname(path)
    file_name = os.path.basename(path)
    return send_from_directory(dirname, file_name)


@app.route('/results/<token>')
def get_results(token):
    db = get_db()
    cur = db.cursor()
    cur.execute("select value from standard where token = %s;", (token,))
    t = cur.fetchone()
    if t:
        t = json.loads(t[0])
        status = t['status']
        if status == "error":
            return u"答卷识别出错，请重新检查后上传。如确认无误……\
                那就是我出问题了，请把下列信息发给俺爹牙牙，让他把我变得更强\
                 <br /><pre>Email: psdn@qq.com QQ: 793048 </pre><br/><pre>" \
                + t['message'] + u"</pre>"
    cur.execute("select processed, total from status where token = %s;", (token, ))
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
        standard = answers = {"answer":[], "id":""}
        num_question = 0
    db.close()
    return render_template('result.html',
        processed= processed,
        total=total,
        standard=standard,
        answers= answers,
        token=token,
        colnum=range(1, num_question+1))


@app.route('/uploads/download/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    message = []
    token = getToken()
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], token)
    success = True
    if request.method == 'POST' and request.values['answersheettype'] in ['fullpage', 'halfpage', 'handwriting']:
        standard = request.files['standard']
        if allowed_file(standard.filename):
            valid_filenames = list()
            answers = request.files.getlist('answers')
            for f in answers:
                if allowed_file(f.filename):
                    filename = secure_filename(f.filename)
                    os.system("mkdir -p {}".format(os.path.join(upload_path, 'student')))
                    f.save(os.path.join(upload_path, 'student', filename))
                    file_url = url_for('uploaded_file', filename=filename)
                    message.append(u"答题卡文件：{} 上传成功，正在处理中……".format(f.filename))
                    valid_filenames.append(os.path.join(upload_path, 'student', filename))
                else:
                    message.append(u"答题卡文件：{} 由于后缀名不合法已被忽略，请上传pdf文件。".format(f.filename))
            if valid_filenames:
                os.system("mkdir -p {}".format(os.path.join(upload_path, 'teacher')))
                standard_name = secure_filename(standard.filename)
                valid_filenames.append(os.path.join(upload_path, 'teacher', standard_name))
                standard.save(os.path.join(upload_path, 'teacher', standard_name))

                if getPDFPageNum(valid_filenames[-1]) == 1:
                    message.insert(0, u"标准答案文件：{} 上传成功，正在处理中……".format(standard.filename))
                else:
                    message.insert(0, u"标准答案文件：{} 超过一页，任取一页识别……".format(standard.filename))
                p = Process(target=convert_and_recognize,
                    args=(token,
                        valid_filenames,
                        request.values['answersheettype']))
                db = get_db()
                c = db.cursor()
                c.execute("insert into status (token, processed, total) values (%s, 0, %s);",
                    (token, getTotalPageNum(valid_filenames[:-1]))) # the last file is standard answer
                db.commit()
                p.start()
            else:
                message.append(u"没有提交有效的答题卡文件，请检查后重新上传。")
                success = False
        else:
            message.append(u"标准答案文件：{} 后缀名不合法，请选择正确的PDF文件。".format(standard.filename))
            success = False
    else:
        return render_template('index.html')
    return render_template('redirect.html', message=message, url = '/' if not success else '/results/{}'.format(token),
        time=3 if success else 5)


if __name__ == '__main__':
    db = get_db()
    c = db.cursor()
    for statement in DATABASE_INIT:
        c.execute(statement);
    db.commit()
    #app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
    #app.run(host="0.0.0.0", debug=True)
    app.run(host="0.0.0.0", threaded=True)
