# -*- coding: utf-8 -*-
from __future__ import division

import xlsxwriter
import numpy as np
import cv2

getColName = xlsxwriter.utility.xl_col_to_name

def countCorrect(standard_answers, student_info):
    '''
    count the number of correct answers for each question
    params:
        standard_answers: a list of strings, the correct answers
        student_info: a list of dictionary, dictionary items are:
            "id": a string of digits, the number of students
            "answer": a list of strings, the student's answers
    return:
        a list of integers, the count of correct answers for each question
    '''
    student_answers = [s['answer'] for s in student_info]
    result = np.array([0] * len(standard_answers), dtype=np.int32)
    for ans in student_answers:
        correctness = np.array([(1 if ans[i] == standard_answers[i] else 0)
                                for i in range(len(standard_answers))])
        result += correctness
    return result

def calcScore(standard_answers, student_info, credits):
    '''
    calculate the score for each student
    params:
        standard_answers: a list of strings, the correct answers
        student_info: a list of dictionary, dictionary items are:
            "id": a string of digits, the number of students
            "answer": a list of strings, the student's answers
        credits: the credits for each question
    return:
        a list of float values, the score of each student according to
        the order in student_info
    '''
    result = list()
    for student in student_info:
        t = [(x[0] == x[1]) * credits[i]
             for i, x in enumerate(zip(standard_answers, student['answer']))]
        result.append(sum(t))
    return result

def generateXlsx(output, standard_answers, student_info, credits=None):
    '''
    generate an xlsx files to output path. the files has two sheets:
        1. statistics of questions
        2. original answers, and scores from students
    params:
        output: a string, path to the output file
        standard_answers: a list of strings, the correct answers
        student_info: a list of dictionary, dictionary items are:
            "id": a string of digits, the number of students
            "answer": a list of strings, the student's answers
        credits: a list of float values, the credits of each question, all 1 by
            default
    '''
    if not credits:
        credits = [1] * len(standard_answers)
    assert len(standard_answers) == len(credits)

    student_info.sort(key=lambda x: x['id'])

    num_question = len(standard_answers)
    num_student = len(student_info)




    # Create a workbook and add a worksheet.
    workbook = xlsxwriter.Workbook(output)

    bold = workbook.add_format({'bold': 1, 'align': 'center'})
    center = workbook.add_format({'align': 'center'})
    format_wrong = workbook.add_format({'align': 'center',
                                   'bg_color': '#FFC7CE',
                                   })
    format_correct = workbook.add_format({'align': 'center',
                                 'bg_color': '#C6EFCE',
                                 })


    note_sheet = workbook.add_worksheet(u"功能说明")
    answer_sheet = workbook.add_worksheet(u"答案与分值")
    score_sheet = workbook.add_worksheet(u"学生成绩")
    stats_sheet = workbook.add_worksheet(u"试卷统计")
    name_sheet = workbook.add_worksheet(u"学号与姓名")

    name_sheet.write_string(0, 0, u"学号", bold)
    name_sheet.write_string(0, 1, u"姓名", bold)

    # Used for calculation. We cannot compare a row and a column
    # (at least I can't find a method after searching for 3 hours)
    tranposed_answer_sheet = workbook.add_worksheet(u"ans_trans")
    tranposed_answer_sheet.hide()



    answer_sheet.write_string(0, 0, u"题号", bold)
    answer_sheet.write_string(0, 1, u"标准答案", bold)
    answer_sheet.write_string(0, 2, u"分值", bold)
    tranposed_answer_sheet.write_string(0, 0, u"题号", bold)
    tranposed_answer_sheet.write_string(1, 0, u"标准答案", bold)
    tranposed_answer_sheet.write_string(2, 0, u"分值", bold)

    for i in range(num_question):
        answer_sheet.write_number(i+1, 0, i+1, bold)
        answer_sheet.write_string(i+1, 1, standard_answers[i], center)
        answer_sheet.write_number(i+1, 2, credits[i], center)
        tranposed_answer_sheet.write_formula(0, i+1, u"=答案与分值!A{}".format(i+2), bold)
        tranposed_answer_sheet.write_formula(1, i+1, u"=答案与分值!B{}".format(i+2), center)
        tranposed_answer_sheet.write_formula(2, i+1, u"=答案与分值!C{}".format(i+2), center)

    # set width of column for ID


    score_sheet.set_column(3, num_question+2, 6)
    score_sheet.write_string(0, 0, u"姓名", bold)
    score_sheet.write_string(0, 1, u"学号", bold)
    score_sheet.write_string(0, 2, u"总分", bold)

    for i in range(num_question):
        score_sheet.write_number(0, i+3, i+1, bold)


    for i in range(num_student):
        # score_sheet.set_row(i+1, 10)
        # h, w = cv2.imread(student_info[i]['name_image'], cv2.IMREAD_GRAYSCALE).shape
        # score_sheet.insert_image("A{}".format(i+1),
        #                          student_info[i]['name_image'],
        #                          {'positioning': 1,
        #                           'y_scale': 40 / h,
        #                           'x_scale': 40 / w})
        score_sheet.write_formula(i+1, 0, u"=VLOOKUP(B{}, 学号与姓名!A:B, 2)".format(i+2), center)
        score_sheet.write_string(i+1, 1, student_info[i]['id'], center)
        for j in range(num_question):
            col_name = getColName(j+3)
            score_sheet.write_string(i+1, j+3, student_info[i]['answer'][j], center)
            score_sheet.conditional_format('{}{}'.format(col_name, i+2),
                                         {'type': 'formula',
                                          'criteria': u'=EXACT(答案与分值!$B${}, ${}${})'.format(j+2, col_name, i+2),
                                          'format': format_correct})
            score_sheet.conditional_format('{}{}'.format(col_name, i+2),
                                         {'type': 'formula',
                                          'criteria': u'=NOT(EXACT(答案与分值!$B${}, ${}${}))'.format(j+2, col_name, i+2),
                                          'format': format_wrong})
        score_sheet.write_formula(i+1,
                                  2,
                                  u'=SUMPRODUCT(--(ans_trans!B2:{}2=D{}:{}{}), ans_trans!B3:{}3)'.format(getColName(num_question),
                                                                                    i+2,
                                                                                    getColName(num_question+2),
                                                                                    i+2,
                                                                                    getColName(num_question)),
                                  center)

    score_sheet.write_string(0, 0, u"姓名", bold)
    score_sheet.set_column(0, 0, 0)

    score_sheet.set_column(1, 1, 20)
    # Excels' built-in format
    # Reference: http://xlsxwriter.readthedocs.io/format.html#format-set-num-format
    format_percentage = workbook.add_format({'align': 'center'})
    format_percentage.set_num_format(0xA)

    stats_sheet.write_string(0, 0, u"总人数", bold)
    # sometimes students forget to fill in their number,
    # column C is better in this case
    stats_sheet.write_formula(0, 1, u'=SUBTOTAL(103, 学生成绩!C:C)-1', center)

    stats_sheet.write_string(1, 0, u"题号", bold)
    stats_sheet.write_string(1, 1, u"答案", bold)
    stats_sheet.write_string(1, 2, u"正确人数", bold)
    stats_sheet.write_string(1, 3, u"正确比例", bold)
    for i, v in enumerate('ABCDEFG'):
        stats_sheet.write_string(1, 4+i, u"选{}比例".format(v), bold)
    for i in range(num_question):
        stats_sheet.write_number(i+2, 0, i+1, bold)
        stats_sheet.write_formula(i+2, 1, u'=答案与分值!B{}'.format(i+2), bold)
        # Extremely complicated, it took me 1 hour:
        # https://exceljet.net/formula/count-visible-rows-only-with-criteria
        visible_correct = u'=SUMPRODUCT((--(学生成绩!{}2:{}{}=ans_trans!{}2))' + \
            u'*(SUBTOTAL(103,OFFSET(学生成绩!{}2,ROW(学生成绩!{}2:{}{})' + \
            u'-MIN(ROW(学生成绩!{}2:{}{})),0))))'

        # TODO: optimize this part
        stats_sheet.write_formula(i+2,
                                  2,
                                  visible_correct.format(getColName(i+3),
                                                   getColName(i+3),
                                                   num_student+1,
                                                   getColName(i+1),
                                                   getColName(i+3),
                                                   getColName(i+3),
                                                   getColName(i+3),
                                                   num_student+1,
                                                   getColName(i+3),
                                                   getColName(i+3),
                                                   num_student+1,),
                                  center)

        # stats_sheet.write_formula(i+2,
        #                           2,
        #                           u"=COUNTIF(学生成绩!{}2:{}{}, ans_trans!{}2)".format(getColName(i+2),
        #                                                                            getColName(i+2),
        #                                                                            num_student+1,
        #                                                                            getColName(i+1)),
        #                           center)

        # the number of visible students who chose choice_k
        # shit, it's even more absurdfuckingly complicated
        # I don't expect I can understand it in the future
        visible_choose = u'=SUMPRODUCT((ISNUMBER(SEARCH("{}", 学生成绩!{}2:{}{})))' + \
            u'*(SUBTOTAL(103,OFFSET(学生成绩!{}2,ROW(学生成绩!{}2:{}{})' + \
            u'-MIN(ROW(学生成绩!{}2:{}{})),0))))/B1'

        # TODO: optimize this part
        for j, v in enumerate('ABCDEFG'):
            stats_sheet.write_formula(i+2,
                                      j+4,
                                      visible_choose.format(v,
                                                            getColName(i+3),
                                                            getColName(i+3),
                                                            num_student+1,
                                                            getColName(i+3),
                                                            getColName(i+3),
                                                            getColName(i+3),
                                                            num_student+1,
                                                            getColName(i+3),
                                                            getColName(i+3),
                                                            num_student+1),
                                      format_percentage)

        # for j, v in enumerate('ABCDE'):
        #     stats_sheet.write_formula(i+2,
        #                               j+4,
        #                               u'=COUNTIF(学生成绩!{}2:{}{}, "{}")/B1'.format(getColName(i+2),
        #                                                                                getColName(i+2),
        #                                                                                num_student+1,
        #                                                                                v),
        #                               format_percentage)


        # in excel, the row number starts from 1, while
        # in this api, it starts with 0. that's why it's i+3 here
        stats_sheet.write_formula(i+2, 3, '=C{}/B1'.format(i+3), format_percentage)


    stats_sheet.conditional_format('D3:D{}'.format(num_question+3),
                                   {'type': '3_color_scale',
                                    'maximum': 1,
                                    'minimum': 0})
    note_sheet.merge_range("A1:Z1", u"1、在“答案与分值”表中修改每题对应分值，学生成绩会自动更新。")
    note_sheet.merge_range("A2:Z2", u"2、在“学生成绩”表中使用筛选功能筛选学生（如根据学号筛选特定班级的学生），“试卷统计”中会自动更新为筛选出学生的成绩统计信息。")
    note_sheet.merge_range("A3:Z3", u"3、在“学号与姓名”表中填入学生学号与姓名的对应关系，并在“学生成绩”表中右键取消隐藏A列，或拖动B列左侧边缘使其显示，即可看到学生对应学生的学号。")
    note_sheet.merge_range("A4:Z4", u"4、可在“学生成绩”一表修改学生答案，相关数据会自动更新。如果有识别错误（虽然不太可能发生），请把相应的答题卡文件发送到psdn@qq.com以便我分析改进。")
    note_sheet.merge_range("A5:Z5", u"5、若有不清楚的地方，欢迎发邮件咨询或下载相应的功能演示视频观看操作流程。")

    workbook.close()
