def join(words):

    """Joins list of stings with ',' and 'and'"""
    
    if len(words) > 2:
        return '%s, and %s' % ( ', '.join(words[:-1]), words[-1] )
    else:
        return ' and '.join(words)