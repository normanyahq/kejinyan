import excel

output = "./test.xlsx"
standard_answers = ['A', 'AB', 'AC', 'ACD']
student_info = [{"id": "21", "answer": ['A', 'B', 'C', 'D']},
                {"id": "12", "answer": list("ABAB")},
                {"id": "13", "answer": list("AAAA")}]
credits = [1, 2, 2.5, 10]
excel.generateXlsx(output, standard_answers, student_info, credits)
