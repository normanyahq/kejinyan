# -*- coding: utf-8 -*-
from __future__ import division

import xlsxwriter
import numpy as np
import cv2

getColName = xlsxwriter.utility.xl_col_to_name
options = 'ABCDEFG'
creditValues = {"makesi_new": [1] * 35 + [2] * 5 + [1] * 10}


def encodeAnswer(cell):
    '''
    Given a source cell containing choices, return the excel formula to encode
    it as 7 digit decimal for now (because bit operation is not supported
    below excel 2013):
        G F E D C B A
        0 0 0 0 0 0 0
    for example:
        ABC -> 0000111
        CD  -> 0001100
    param:
        cell: the cell reference
    '''
    template = u'IF(ISNUMBER(SEARCH("{}", {})), {}, 0)'
    return u"=" + u"+".join([template.format(c, cell, 10**i) for i, c in enumerate(options)])


def calculateScore(stdAnswerCell, studentAnswerCell, partialCredit=False):
    # directly do minus, if there is a 9 in result, return it has wrong answer
    template = u'=IF({}={}, 1, IF(AND({}>{}, NOT(ISNUMBER(SEARCH("9", TEXT({}-{}, 0))))), {}, 0))'
    return template.format(stdAnswerCell,
                           studentAnswerCell,
                           stdAnswerCell,
                           studentAnswerCell,
                           stdAnswerCell,
                           studentAnswerCell,
                           0.5 if partialCredit else 0)


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


def getMaxAnswerOption(student_info):
    '''
    return the maximum option number by iterating through students' choices
    params:
        student_info: a list of dictionary, dictionary items are:
            "id": a string of digits, the number of students
            "answer": a list of strings, the student's answers
    '''
    def getMaxChar(obj):
        if isinstance(obj, str):
            return max(obj)
        elif isinstance(obj, list):
            return max([getMaxChar(c) for c in obj])
        else:
            pass

    result = 'A'
    for info in student_info:
        result = max(result, getMaxChar(info['answer']))
    return result


def generateXlsx(output, standard_answers, student_info, partialCredit=True, testType=None):
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
        partialCredit: give half points if partially correct
    '''

    credits = [1 if ans != '-' else 0 for ans in standard_answers]
    if testType in creditValues:
        credits = creditValues[testType]

    assert len(standard_answers) == len(credits)

    student_info.sort(key=lambda x: x['id'])
    max_option = getMaxAnswerOption(student_info)
    assert len(max_option) == 1
    num_question = len(standard_answers)
    num_student = len(student_info)

    # Create a workbook and add a worksheet.
    workbook = xlsxwriter.Workbook(output)

    bold = workbook.add_format({'bold': 1, 'align': 'center'})
    center = workbook.add_format({'align': 'center'})
    format_wrong = workbook.add_format({'align': 'center',
                                        'bg_color': '#FFC7CE',
                                        'font_color': '#9C0006',
                                        'bottom': 1
                                        })
    format_partial = workbook.add_format({'align': 'center',
                                          'bg_color': '#FFEB9C',
                                          'font_color': '#9C6500',
                                          'bottom': 3
                                          })
    format_correct = workbook.add_format({'align': 'center',
                                          'bg_color': '#C6EFCE',
                                          'font_color': '#006100'
                                          })

    note_sheet = workbook.add_worksheet(u"功能说明")
    answer_sheet = workbook.add_worksheet(u"标准答案与分值")
    score_sheet = workbook.add_worksheet(u"学生答案")
    stats_sheet = workbook.add_worksheet(u"试卷统计")
    name_sheet = workbook.add_worksheet(u"学号与姓名")
    detailed_score = workbook.add_worksheet(u"分数详情")

    name_sheet.write_string(0, 0, u"学号", bold)
    name_sheet.write_string(0, 1, u"姓名", bold)

    # Used for calculation. We cannot compare a row and a column
    # (at least I can't find a method after searching for 3 hours)
    tranposed_answer_sheet = workbook.add_worksheet(u"ans_trans")
    tranposed_answer_sheet.hide()

    score_encode = workbook.add_worksheet(u"student_encode")
    score_encode.hide()
    student_points = workbook.add_worksheet(u"student_points")
    student_points.hide()

    answer_sheet.write_string(0, 0, u"题号", bold)
    answer_sheet.write_string(0, 1, u"标准答案", bold)
    answer_sheet.write_string(0, 2, u"分值", bold)
    tranposed_answer_sheet.write_string(0, 0, u"题号", bold)
    tranposed_answer_sheet.write_string(1, 0, u"标准答案", bold)
    tranposed_answer_sheet.write_string(2, 0, u"分值", bold)
    tranposed_answer_sheet.write_string(3, 0, u"编码", bold)
    for i in range(num_question):
        answer_sheet.write_number(i + 1, 0, i + 1, bold)
        answer_sheet.write_string(i + 1, 1, standard_answers[i], center)
        answer_sheet.write_number(i + 1, 2, credits[i], center)
        tranposed_answer_sheet.write_formula(
            0, i + 1, u"=标准答案与分值!A{}".format(i + 2), bold)
        tranposed_answer_sheet.write_formula(
            1, i + 1, u"=标准答案与分值!B{}".format(i + 2), center)
        tranposed_answer_sheet.write_formula(
            2, i + 1, u"=标准答案与分值!C{}".format(i + 2), center)
        tranposed_answer_sheet.write_formula(
            3, i + 1, encodeAnswer(u"标准答案与分值!B{}".format(i + 2)), center)

    # set width of column for ID

    score_sheet.set_column(3, num_question + 2, 6)
    score_sheet.write_string(0, 0, u"姓名", bold)
    score_sheet.write_string(0, 1, u"学号", bold)
    score_encode.write_string(0, 1, u"学号", bold)
    student_points.write_string(0, 1, u"学号", bold)
    detailed_score.write_string(0, 0, u"姓名", bold)
    detailed_score.write_string(0, 1, u"学号", bold)
    detailed_score.write_string(0, 2, u"总分", bold)
    detailed_score.write_string(0, 3, u"排名", bold)
    score_sheet.write_string(0, 2, u"总分", bold)

    for i in range(num_question):
        score_sheet.write_number(0, i + 3, i + 1, bold)
        score_encode.write_number(0, i + 3, i + 1, bold)
        student_points.write_number(0, i + 3, i + 1, bold)
        detailed_score.write_number(0, i + 4, i + 1, bold)

    if testType == "gk_english":
        detailed_score.write_string(0, num_question + 4, u'听力分值(1-20)', bold)
        detailed_score.write_string(0, num_question + 5, u'选择题分值(21-40)', bold)
        detailed_score.write_string(0, num_question + 6, u'完型填空分值(41-60)', bold)
        detailed_score.set_column('BM:BO', 20, center)

    for i in range(num_student):
        # score_sheet.set_row(i+1, 10)
        # h, w = cv2.imread(student_info[i]['name_image'], cv2.IMREAD_GRAYSCALE).shape
        # score_sheet.insert_image("A{}".format(i+1),
        #                          student_info[i]['name_image'],
        #                          {'positioning': 1,
        #                           'y_scale': 40 / h,
        #                           'x_scale': 40 / w})
        score_sheet.write_formula(
            i + 1, 0, u"=VLOOKUP(B{}, 学号与姓名!A:B, 2, false)".format(i + 2), center)
        score_sheet.write_string(i + 1, 1, student_info[i]['id'], center)
        score_encode.write_formula(i + 1, 1, u"=学生答案!B{}".format(i + 2), center)
        student_points.write_formula(
            i + 1, 1, u"=学生答案!B{}".format(i + 2), center)
        detailed_score.write_formula(
            i + 1, 0, u"=VLOOKUP(B{}, 学号与姓名!A:B, 2, false)".format(i + 2), center)
        detailed_score.write_formula(
            i + 1, 1, u"=学生答案!B{}".format(i + 2), center)
        detailed_score.write_formula(
            i + 1, 2, u"=学生答案!C{}".format(i + 2), center)
        detailed_score.write_formula(
            i + 1, 3, u"=RANK(C{}, C:C)".format(i + 2), center)

        for j in range(num_question):
            col_name = getColName(j + 3)
            score_sheet.write_string(
                i + 1, j + 3, student_info[i]['answer'][j], center)
            score_encode.write_formula(
                i + 1, j + 3, encodeAnswer(u'学生答案!{}{}'.format(col_name, i + 2)), center)
            student_points.write_formula(i + 1,
                                         j + 3,
                                         calculateScore(u'ans_trans!{}4'.format(getColName(j + 1)),
                                                        u'student_encode!{}{}'.format(
                                                            col_name, i + 2),
                                                        partialCredit),
                                         center)

            detailed_score.write_formula(
                i + 1, j + 4, u"=student_points!{}{}*标准答案与分值!C{}".format(
                    getColName(j + 3), i + 2, j + 2
                ), center
            )
            score_sheet.conditional_format('{}{}'.format(col_name, i + 2),
                                           {'type': 'formula',
                                            'criteria': u'=student_points!{}{}=0.5'.format(getColName(j + 3), i + 2),
                                            'format': format_partial})
            score_sheet.conditional_format('{}{}'.format(col_name, i + 2),
                                           {'type': 'formula',
                                            'criteria': u'=EXACT(标准答案与分值!$B${}, ${}${})'.format(j + 2, col_name, i + 2),
                                            'format': format_correct})
            score_sheet.conditional_format('{}{}'.format(col_name, i + 2),
                                           {'type': 'formula',
                                            'criteria': u'=NOT(EXACT(标准答案与分值!$B${}, ${}${}))'.format(j + 2, col_name, i + 2),
                                            'format': format_wrong})

        if testType == "gk_english":
            detailed_score.write_formula(
                i + 1, num_question + 4, u'=SUM(E{}:X{})'.format(i + 2, i + 2))
            detailed_score.write_formula(
                i + 1, num_question + 5, u'=SUM(Y{}:AR{})'.format(i + 2, i + 2))
            detailed_score.write_formula(
                i + 1, num_question + 6, u'=SUM(AS{}:BL{})'.format(i + 2, i + 2))

        score_sheet.write_formula(i + 1,
                                  2,
                                  u'=SUMPRODUCT(--(student_points!D{}:{}{}), ans_trans!B3:{}3)'.format(
                                      i + 2,
                                      getColName(num_question + 2),
                                      i + 2,
                                      getColName(num_question)),
                                  center)

    score_sheet.write_string(0, 0, u"姓名", bold)
    score_sheet.set_column(0, 0, 0)
    detailed_score.set_column(0, 0, 0)
    score_sheet.set_column(1, 1, 20)
    detailed_score.set_column(1, 1, 20)
    # Excels' built-in format
    # Reference:
    # http://xlsxwriter.readthedocs.io/format.html#format-set-num-format
    format_percentage = workbook.add_format({'align': 'center'})
    format_percentage.set_num_format(0xA)

    stats_sheet.write_string(0, 0, u"总人数", bold)
    # sometimes students forget to fill in their number,
    # column C is better in this case
    stats_sheet.write_formula(0, 1, u'=SUBTOTAL(103, 学生答案!C:C)-1', center)
    stats_sheet.write_string(0, 2, u"平均分", bold)
    stats_sheet.write_formula(
        0, 3, u"=SUBTOTAL(101, 学生答案!C2:C{})".format(num_student + 1), center)

    stats_sheet.write_string(1, 0, u"题号", bold)
    stats_sheet.write_string(1, 1, u"答案", bold)
    stats_sheet.write_string(1, 2, u"正确人数", bold)
    stats_sheet.write_string(1, 3, u"正确比例", bold)

    problem_average_column = 0
    for i, v in enumerate(options):
        stats_sheet.write_string(1, 4 + i, u"选{}比例".format(v), bold)
        problem_average_column = 4 + i + 1
        if v >= max_option:
            break
    stats_sheet.write_string(1, problem_average_column, u"小题平均分", bold)

    for i in range(num_question):
        stats_sheet.write_number(i + 2, 0, i + 1, bold)
        stats_sheet.write_formula(i + 2, 1, u'=标准答案与分值!B{}'.format(i + 2), bold)
        # Extremely complicated, it took me 1 hour:
        # https://exceljet.net/formula/count-visible-rows-only-with-criteria
        visible_correct = u'=SUMPRODUCT((--(学生答案!{}2:{}{}=ans_trans!{}2))' + \
            u'*(SUBTOTAL(103,OFFSET(学生答案!{}2,ROW(学生答案!{}2:{}{})' + \
            u'-MIN(ROW(学生答案!{}2:{}{})),0))))'

        # TODO: optimize this part
        stats_sheet.write_formula(i + 2,
                                  2,
                                  visible_correct.format(getColName(i + 3),
                                                         getColName(i + 3),
                                                         num_student + 1,
                                                         getColName(i + 1),
                                                         getColName(i + 3),
                                                         getColName(i + 3),
                                                         getColName(i + 3),
                                                         num_student + 1,
                                                         getColName(i + 3),
                                                         getColName(i + 3),
                                                         num_student + 1,),
                                  center)

        # stats_sheet.write_formula(i+2,
        #                           2,
        #                           u"=COUNTIF(学生答案!{}2:{}{}, ans_trans!{}2)".format(getColName(i+2),
        #                                                                            getColName(i+2),
        #                                                                            num_student+1,
        #                                                                            getColName(i+1)),
        #                           center)

        # the number of visible students who chose choice_k
        # shit, it's even more absurdfuckingly complicated
        # I don't expect I can understand it in the future
        visible_choose = u'=SUMPRODUCT((ISNUMBER(SEARCH("{}", 学生答案!{}2:{}{})))' + \
            u'*(SUBTOTAL(103,OFFSET(学生答案!{}2,ROW(学生答案!{}2:{}{})' + \
            u'-MIN(ROW(学生答案!{}2:{}{})),0))))/B1'

        # TODO: optimize this part
        for j, v in enumerate(options):
            if v > max_option:
                break
            stats_sheet.write_formula(i + 2,
                                      j + 4,
                                      visible_choose.format(v,
                                                            getColName(i + 3),
                                                            getColName(i + 3),
                                                            num_student + 1,
                                                            getColName(i + 3),
                                                            getColName(i + 3),
                                                            getColName(i + 3),
                                                            num_student + 1,
                                                            getColName(i + 3),
                                                            getColName(i + 3),
                                                            num_student + 1),
                                      format_percentage)
        problem_average_formula = u'=AVERAGE(student_points!{}2:{}{})*标准答案与分值!C{}'.format(
            getColName(i + 3), getColName(i + 3), num_student + 1, i + 2)
        stats_sheet.write_formula(
            i + 2, problem_average_column, problem_average_formula)
        # for j, v in enumerate('ABCDE'):
        #     stats_sheet.write_formula(i+2,
        #                               j+4,
        #                               u'=COUNTIF(学生答案!{}2:{}{}, "{}")/B1'.format(getColName(i+2),
        #                                                                                getColName(i+2),
        #                                                                                num_student+1,
        #                                                                                v),
        #                               format_percentage)

        # in excel, the row number starts from 1, while
        # in this api, it starts with 0. that's why it's i+3 here
        stats_sheet.write_formula(
            i + 2, 3, '=C{}/B1'.format(i + 3), format_percentage)

    stats_sheet.conditional_format('D3:D{}'.format(num_question + 3),
                                   {'type': '3_color_scale',
                                    'maximum': 1,
                                    'minimum': 0})
    note_sheet.merge_range("A1:Z1", u"1、在“标准答案与分值”表中修改每题对应分值，学生成绩会自动更新。")
    note_sheet.merge_range(
        "A2:Z2", u"2、在“学生答案”表中使用筛选功能筛选学生（如根据学号筛选特定班级的学生），“试卷统计”中会自动更新为筛选出学生的成绩统计信息。")
    note_sheet.merge_range(
        "A3:Z3", u"3、在“学号与姓名”表中填入学生学号与姓名的对应关系，并在“学生答案”表中右键取消隐藏A列，或拖动B列左侧边缘使其显示，即可看到学生对应学生的学号。")
    note_sheet.merge_range(
        "A4:Z4", u"4、可在“学生答案”一表修改学生答案，相关数据会自动更新。如果有识别错误（虽然不太可能发生），请把相应的答题卡文件发送到793048@qq.com以便我分析改进。")
    note_sheet.merge_range("A5:Z5", u"5、若有不清楚的地方，欢迎发邮件咨询或下载相应的功能演示视频观看操作流程。")

    workbook.close()
