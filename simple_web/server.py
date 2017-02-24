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

os.environ["PYTHONPATH"] = os.environ.get("PYTHONPATH", "") + ":{}/../ocr/src/".format(os.path.dirname(__file__))
from processor.interface import recognizeJPG
from processor.utility.ocr import pdf2jpg

PROCESS_POOL_SIZE = 1


DATABASE = 'database.db'

DATABASE_INIT = ['create table if not exists standard (token string, value string);',
    'create table if not exists answer (token string, value string);',
    'create table if not exists number (token string, processed int, total int);']

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
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    c = db.cursor()
    # for statement in DATABASE_INIT:
    #     c.execute(statement);
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

def convert_and_recognize(token, paths):
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
    c.execute('update number set total = ? where token = ?;',(len(student_files), token))
    # g._database.commit()

    try:
        standard = recognizeJPG(teacher_files[0], "halfpage")
        c.execute('insert into standard values (?, ?);', (token, json.dumps(standard)))
    except:
        print "encountered error: {}".format(teacher_files[0])
        traceback.print_exc()
    for i, f in enumerate(student_files):
        try:
            result = recognizeJPG(f, "halfpage")
            c.execute('insert into answer values (?, ?);', (token, json.dumps(result)))
        except:
            print "encountered error: {}".format(f)
            traceback.print_exc()
        c.execute('update number set processed=? where token=?;', (i+1, token))
    time.sleep(1)
    g._database.commit()

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
    cur.execute("select processed, total from number where token = ?;", (token, ))
    processed, total = cur.fetchone()
    cur.execute("select value from answer where token = ?;", (token,))
    answers = list(map(lambda x: json.loads(x[0]), cur.fetchall()))
    cur.execute("select value from standard where token = ?;", (token,))
    standard = json.loads(cur.fetchone()[0])
    # print standard
    num_question = len(standard['answer'])
    while standard['answer'][num_question-1] == '-':
        num_question -= 1
    # print num_question
    standard['answer'] = standard['answer'][:num_question]
    for answer in answers:
        answer['answer'] = render_result(standard, answer)
    return render_template('results.html', 
        processed= processed, 
        total=total, 
        standard=standard, 
        answers= answers,
        colnum=range(1, num_question+1))



@app.route('/result/<token>')
def get_result(token):
    cur = get_db().cursor()
    cur.execute("select processed, total from number where token = ?;", (token, ))
    processed, total = cur.fetchone()
    cur.execute("select value from answer where token = ?;", (token,))
    answers = list(map(lambda x: json.loads(x[0]), cur.fetchall()))
    cur.execute("select value from standard where token = ?;", (token,))
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
    if request.method == 'POST':
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
                p = Process(target=convert_and_recognize, args=(token, valid_filenames,))
                c = get_db().cursor()
                c.execute("insert into number values (?, 0, ?)", (token, len(valid_filenames)))
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