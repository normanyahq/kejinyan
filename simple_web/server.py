# -*- coding: utf-8 -*-
from __future__ import division
import os
from flask import Flask, request, url_for, send_from_directory, render_template, make_response
#from werkzeug import secure_filename
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
import re
import utility.excel

os.environ["PYTHONPATH"] = os.environ.get("PYTHONPATH", "") + ":{}/../ocr/src/".format(os.path.dirname(__file__))
from processor.interface import recognizeJPG
from processor.utility.ocr import pdf2jpg, getPDFPageNum

DATABASE_INIT = ['create table if not exists standard (token text, value text);',
    'create table if not exists answer (token text, value text);',
    'create table if not exists status (token text, processed int, total int);',
    'create table if not exists error_list (token text, path text, message text);' ]

ANSWER_FILE_NAME = "standard.pdf"


def countQuestion(standard):
    # print standard
    standard = standard["result"]['answer']
    num_question = len(standard)
    while standard[num_question-1] == '-':
        num_question -= 1
    return num_question

def isValidToken(token):
    return re.match("^\d{14}[a-zA-Z0-9]{10}$", token)


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
        c.execute("insert into error_list values (%s, %s, %s);", (token, standard['path'], standard['message']))
        db.commit()
    for i, f in enumerate(student_files):
        result = recognizeJPG(f, answersheet_type, os.path.join(app.config['UPLOAD_FOLDER'], token, 'name'))
        c.execute('insert into answer values (%s, %s);', (token, json.dumps(result)))
        if result['status'] =='error':
            c.execute("insert into error_list values (%s, %s, %s);", (token, result['path'], result['message']))
        c.execute('update status set processed=%s where token=%s;', (i+1, token))
        db.commit()

def getPageNumList(filepath_list):
    return [getPDFPageNum(path) for path in filepath_list]

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

@app.route('/table/<token>/result.xlsx')
def returnTable(token):
    if not isValidToken(token):
        return json.dumps({"status": 403, "message": "Don't try to hack me."}), 403

    xlsx_path = os.path.join(app.config['UPLOAD_FOLDER'], token, 'table.xlsx')
    if not os.path.isfile(xlsx_path):
        cur = get_db().cursor()
        cur.execute("select value from answer where token = %s;", (token,))
        t = cur.fetchall()
        t = list(map(lambda x: json.loads(x[0]), t))
        t = filter(lambda x: "result" in x, t)
        answers = list(map(lambda x: x['result'], t))
        cur.execute("select value from standard where token = %s;", (token,))
        standard = json.loads(cur.fetchone()[0])['result']
        t = len(standard['answer']) - 1
        while standard['answer'][t] == '-':
            t -= 1
        standard['answer'] = standard['answer'][:t+1]
        utility.excel.generateXlsx(xlsx_path, standard['answer'], answers)
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], token), 'table.xlsx')



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

    task_dir = os.path.join(app.config['UPLOAD_FOLDER'], token)
    student_filedir = os.path.join(task_dir, 'student')

    student_files = glob.glob("{}/*.jpg".format(student_filedir))
    num_converted = len(student_files)

    # we include the conversion part into progress bar, original formula is:
    # percentage = 100 * (processed + num_converted) / (total + total)
    return json.dumps({"processed": processed,
                       "total":total,
                       "percentage": 50  * (processed + num_converted) / total})


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

@app.route('/name/<token>/<filename>')
def getNameImage(token, filename):
    dirname = os.path.join(app.config['UPLOAD_FOLDER'], token, 'name')
    return send_from_directory(dirname, filename)


@app.route('/assets/<path:filename>')
def getAssets(filename):
    path = os.path.join(app.config['ASSETS_FOLDER'], filename)
    dirname = os.path.dirname(path)
    file_name = os.path.basename(path)
    return send_from_directory(dirname, file_name)


@app.route('/results/<token>')
def get_results(token):
    if not isValidToken(token):
        return json.dumps({"status": 403, "message": "Don't try to hack me."}), 403

    db = get_db()
    cur = db.cursor()
    cur.execute("select value from standard where token = %s;", (token,))
    t = cur.fetchone()
    if t:
        t = json.loads(t[0])
        status = t['status']
        if status == "error":
            return u"答卷识别出错，请重新检查后上传。如确认无误，\
                请把此网页链接及原始文件发送给网站管理员，以便改进。\
                 <br /><pre>Email: psdn@qq.com QQ: 793048 </pre><br/><pre>" \
                 + u"</pre>"

                # + t['message'] + u"</pre>"
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

@app.route('/upload/', methods=['POST'])
def upload():
    token = request.form['token']
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], token)
    if not isValidToken(token):
        return json.dumps({"status": 403, "message": "Don't try to hack me."}), 403

    if 'standard' in request.files:
        os.system("mkdir -p {}".format(os.path.join(upload_path, 'teacher')))
        os.system("mkdir -p {}".format(os.path.join(upload_path, 'name')))
        request.files['standard'].save(os.path.join(upload_path, 'teacher', ANSWER_FILE_NAME))
    elif 'answers' in request.files:
        os.system("mkdir -p {}".format(os.path.join(upload_path, 'student')))
        answers = request.files.getlist('answers')
        for f in answers:
            if allowed_file(f.filename):
                f.save(os.path.join(upload_path, 'student', 'student_{}.pdf'.format(getToken())))
    return json.dumps({"status": 200, "message": "file sucessfully uploaded"}), 200



@app.route('/', methods=['GET', 'POST'])
def upload_file():
    message = []
    if request.method == "GET":
        token = getToken()
    elif request.method == "POST":
        token = request.values['token']
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], token)
    if request.method == "GET" and request.values.get('upload') == 'true':
        return render_template("index.html", token=token, popover=True)
    elif request.method == 'POST' and request.values['answersheettype'] in ['full',
                                                                            'half',
                                                                            'full_old',
                                                                            'half_old',
                                                                            'makesi',
                                                                            'english']:
        success = True
        task_dir = os.path.join(app.config['UPLOAD_FOLDER'], token)

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
        student_files = glob.glob("{}/*.pdf".format(student_filedir))
        student_page_nums = getPageNumList(student_files)
        total_page_num = sum(student_page_nums)
        if success and total_page_num:
            p = Process(target=convert_and_recognize,
                args=(token,
                    [teacher_filepath] + student_files,
                    request.values['answersheettype']))
            db = get_db()
            c = db.cursor()
            c.execute("insert into status (token, processed, total) values (%s, 0, %s);",
                (token, total_page_num))
            db.commit()
            p.start()
            message.append(u"答题卡上传成功，正在处理中……")
            invalid_file_count = student_page_nums.count(0)
            if invalid_file_count > 0:
                message.append(u"存在{}个无效的答题卡文件，已忽略。请检查您上传的答题卡文件。".format(invalid_file_count))
        else:
            success = False
            message = [u"没有提交有效的答题卡文件，请检查您提交的答题卡文件是否有效。"]
            # displaying succeed message makes client confused
            # reserve only error message

        pause_time = 3 if success else 5
        return render_template('redirect.html', message=message, url = '/' if not success else '/results/{}'.format(token),
            time=pause_time)
    else:
        return render_template('index.html', token=token, popover=False)



if __name__ == '__main__':
    db = get_db()
    c = db.cursor()
    for statement in DATABASE_INIT:
        c.execute(statement);
    db.commit()
    app.run(host="0.0.0.0", debug=True)
    # app.run(host="0.0.0.0", threaded=True)
