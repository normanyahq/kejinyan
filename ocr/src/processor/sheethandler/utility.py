def getBlockProblemPositions(startRow, startCol, height, width, numProblem, numChoice,
                        leftToRight=True):
    '''
    given the start row and start column of a block,
    return the list of answer areas for each question
    in order
    Args:
        startRow: the starting row of block
        startCol: the starting column of block
        height: the height for each choice
        width: the height for each choice
        numProblem: the number of problems in this block
        numChoice: the number of choice in each problem
        leftToRight: the question answers are listed from left to right
    Returns:
        a list of question positions with height and with

        For example, for input getBlockProblemPositions(0, 1, 1, 2, 5, 5), the return is:
            [(0, 1, 1, 5), (1, 1, 1, 5), (2, 1, 1, 5)]

    '''
    result = list()
    for i in range(numProblem):
        gridPos = (startRow + height * i * leftToRight,
                   startCol + width * i * (not leftToRight),
                   height + height * (numChoice-1) * (not leftToRight),
                   width + width * (numChoice-1) * leftToRight)
        result.append(gridPos)
    return result
