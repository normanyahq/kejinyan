# -*- coding: utf-8 -*-
import xlsxwriter
import numpy as np

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
        credits: a list of float values, the credits of each question
    '''
    if not credits:
        credits = [1] * len(standard_answers)
    assert len(standard_answers) == len(credits)

    student_info.sort(key=lambda x: x['id'])

    num_question = len(standard_answers)
    num_student = len(student_info)

    # Create a workbook and add a worksheet.
    workbook = xlsxwriter.Workbook(output)
    answer_sheet = workbook.add_worksheet(u"答案与分值")
    score_sheet = workbook.add_worksheet(u"学生成绩")
    stats_sheet = workbook.add_worksheet(u"试卷统计")
    note_sheet = workbook.add_worksheet(u"功能说明")

    # Used for calculation. We cannot compare a row and a column
    # (at least I can't find a method after searching for 3 hours)
    tranposed_answer_sheet = workbook.add_worksheet(u"ans_trans")
    tranposed_answer_sheet.hide()

    bold = workbook.add_format({'bold': 1, 'align': 'center'})
    center = workbook.add_format({'align': 'center'})
    format_wrong = workbook.add_format({'align': 'center',
                                   'bg_color': '#FFC7CE',
                                   })
    format_correct = workbook.add_format({'align': 'center',
                                 'bg_color': '#C6EFCE',
                                 })


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
    score_sheet.set_column(0, 0, 20)
    score_sheet.set_column(2, num_question+1, 6)
    score_sheet.write_string(0, 0, u"学号", bold)
    score_sheet.write_string(0, 1, u"总分", bold)

    for i in range(num_question):
        score_sheet.write_number(0, i+2, i+1, bold)

    for i in range(num_student):
        score_sheet.write_string(i+1, 0, student_info[i]['id'], center)
        for j in range(num_question):
            col_name = getColName(j+2)
            score_sheet.write_string(i+1, j+2, student_info[i]['answer'][j], center)
            score_sheet.conditional_format('{}{}'.format(col_name, i+2),
                                         {'type': 'formula',
                                          'criteria': u'=EXACT(答案与分值!$B${}, ${}${})'.format(j+2, col_name, i+2),
                                          'format': format_correct})
            score_sheet.conditional_format('{}{}'.format(col_name, i+2),
                                         {'type': 'formula',
                                          'criteria': u'=NOT(EXACT(答案与分值!$B${}, ${}${}))'.format(j+2, col_name, i+2),
                                          'format': format_wrong})

        score_sheet.write_formula(i+1,
                                  1,
                                  u'=SUMPRODUCT(--(ans_trans!B2:{}2=C{}:{}{}), ans_trans!B3:{}3)'.format(getColName(num_question),
                                                                                    i+2,
                                                                                    getColName(num_question+1),
                                                                                    i+2,
                                                                                    getColName(num_question)),
                                  center)


    # Excels' built-in format
    # Reference: http://xlsxwriter.readthedocs.io/format.html#format-set-num-format
    format_percentage = workbook.add_format({'align': 'center'})
    format_percentage.set_num_format(0xA)

    stats_sheet.write_string(0, 0, u"总人数", bold)
    stats_sheet.write_formula(0, 1, u'=SUBTOTAL(103, 学生成绩!A:A)-1', center)

    stats_sheet.write_string(1, 0, u"题号", bold)
    stats_sheet.write_string(1, 1, u"答案", bold)
    stats_sheet.write_string(1, 2, u"正确人数", bold)
    stats_sheet.write_string(1, 3, u"正确比例", bold)
    for i, v in enumerate('ABCDE'):
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
                                  visible_correct.format(getColName(i+2),
                                                   getColName(i+2),
                                                   num_student+1,
                                                   getColName(i+1),
                                                   getColName(i+2),
                                                   getColName(i+2),
                                                   getColName(i+2),
                                                   num_student+1,
                                                   getColName(i+2),
                                                   getColName(i+2),
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
        visible_choose = u'=SUMPRODUCT(((学生成绩!{}2:{}{}="{}"))' + \
            u'*(SUBTOTAL(103,OFFSET(学生成绩!{}2,ROW(学生成绩!{}2:{}{})' + \
            u'-MIN(ROW(学生成绩!{}2:{}{})),0))))/B1'

        # TODO: optimize this part
        for j, v in enumerate('ABCDE'):
            stats_sheet.write_formula(i+2,
                                      j+4,
                                      visible_choose.format(getColName(i+2),
                                                            getColName(i+2),
                                                            num_student+1,
                                                            v,
                                                            getColName(i+2),
                                                            getColName(i+2),
                                                            getColName(i+2),
                                                            num_student+1,
                                                            getColName(i+2),
                                                            getColName(i+2),
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
    note_sheet.merge_range("A1:Z1", u"1、可在“答案与分值”一表中修改每题对应分值，学生成绩会自动更新。")
    note_sheet.merge_range("A2:Z2", u"2、可在“学生成绩”一表修改学生成绩，相关数据会自动更新。如果有识别错误（虽然不太可能发生），请把相应的答题卡文件发送到psdn@qq.com以便我分析改进。")
    note_sheet.merge_range("A3:Z3", u"3、本表格文档经过精心设计。可通过数据选项卡中的筛选筛选特定学生（如根据学号筛选特定班级的学生），获得被筛选出学生的统计数据。")

    workbook.close()
