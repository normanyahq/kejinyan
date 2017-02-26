# -*- coding: utf-8 -*-
import os
from flask import Flask, request, url_for, send_from_directory, render_template
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
import psycopg2
from pgdb import connect


os.environ["PYTHONPATH"] = os.environ.get("PYTHONPATH", "") + ":{}/../ocr/src/".format(os.path.dirname(__file__))
from processor.interface import recognizeJPG
from processor.utility.ocr import pdf2jpg, getPDFPageNum


DATABASE_INIT = ['create table if not exists standard (token text, value text);',
    'create table if not exists answer (token text, value text);',
    'create table if not exists status (token text, processed int, total int);']

html = '''
    <!DOCTYPE html>
    <html>
    <title>试卷上传</title>
    <h1>试卷上传</h1>
    <form method=post enctype=multipart/form-data>
         <input type=file name=standard>
         <br/>
         <input type=file name=answers multiple>
         <input type=submit value=上传>
    </form>
    </html>
    '''

def get_db():
    # db = getattr(g, '_database', None)
    # if db is None:
        # db = g._database = sqlite3.connect(DATABASE)
        # db = g._database = connect(database='postgres', host='localhost:5432', user='heqing', password='heqing')
    db = connect(database='postgres', host='localhost:5432', user='heqing', password='heqing')
    c = db.cursor()
    for statement in DATABASE_INIT:
        c.execute(statement);
    return db


def getToken():
    return datetime.datetime.now().strftime("%Y%m%d%H%M%S") \
        + "".join([random.choice(string.uppercase + string.lowercase + string.digits)
                   for i in range(0, 10)]) 

ALLOWED_EXTENSIONS = set(['pdf'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'file_storage')
os.system("mkdir -p {}".format(app.config['UPLOAD_FOLDER']))
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024




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

    if standard['status'] == "success":
        c.execute('insert into standard values (%s, %s);', (token, json.dumps(standard)))
        db.commit()
    else:
        return "答卷识别出错，请重新检查后上传。如确认无误……\
            那就是我出问题了，请把下列信息发到 psdn@qq.com" \
            + standard['message']
    for i, f in enumerate(student_files):
        try:
            result = recognizeJPG(f, answersheet_type)
            c.execute('insert into answer values (%s, %s);', (token, json.dumps(result)))
        except:
            print "encountered error: {}".format(f)
            traceback.print_exc()
        c.execute('update status set processed=%s where token=%s;', (i+1, token))
        db.commit()
    time.sleep(1)
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
        result.append('<span style="color:{}">{}</span>'.format(color, student_choice[i].replace('-', "?")))
    return result


@app.route('/results/<token>')
def get_results(token):
    cur = get_db().cursor()
    cur.execute("select processed, total from status where token = %s;", (token, ))
    processed, total = cur.fetchone()
    if processed:
        cur.execute("select value from answer where token = %s;", (token,))
        answers = list(map(lambda x: json.loads(x[0])['result'], cur.fetchall()))
        cur.execute("select value from standard where token = %s;", (token,))
        standard = json.loads(cur.fetchone()[0])['result']
        # print standard
        num_question = len(standard['answer'])
        while standard['answer'][num_question-1] == '-':
            num_question -= 1
        # print num_question
        standard['answer'] = standard['answer'][:num_question]
        for answer in answers:
            answer['answer'] = render_result(standard, answer)
    else:
        standard = answers = {"answer":[], "id":""}
        num_question = 0
    return render_template('results.html', 
        processed= processed, 
        total=total, 
        standard=standard, 
        answers= answers,
        colnum=range(1, num_question+1))



@app.route('/result/<token>')
def get_result(token):
    cur = get_db().cursor()
    cur.execute("select processed, total from status where token = %s;", (token, ))
    processed, total = cur.fetchone()
    cur.execute("select value from answer where token = %s;", (token,))
    answers = list(map(lambda x: json.loads(x[0]), cur.fetchall()))
    cur.execute("select value from standard where token = %s;", (token,))
    standard = json.loads(cur.fetchone()[0])
    return json.dumps({"processed": processed, "total":total, "standard": standard, "answers": answers})

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
                message.insert(0, u"标准答案文件：{} 上传成功，正在处理中……".format(standard.filename))
                os.system("mkdir -p {}".format(os.path.join(upload_path, 'teacher')))
                standard_name = secure_filename(standard.filename)
                valid_filenames.append(os.path.join(upload_path, 'teacher', standard_name))
                standard.save(os.path.join(upload_path, 'teacher', standard_name))
                p = Process(target=convert_and_recognize, args=(token, valid_filenames, request.values['answersheettype']))
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
    app.run(debug=True)