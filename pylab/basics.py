# example of a python module

def lin_interp(x,x1,x2,y1,y2):
    '''
    Given two pairs of numbers provide interpolation
    '''

    y = y1 + (x-x1)*(y2 - y1)/(x2 - x1)
    return y
