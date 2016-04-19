import findsame as fs

def test_subpath():
    assert fs.is_subpath('a/b', 'a')
    assert fs.is_subpath('a/b/', 'a')
    assert fs.is_subpath('a/b', 'a/')
    assert fs.is_subpath('a/b/', 'a/')
    assert fs.is_subpath('/a/b', '/a/')
    assert fs.is_subpath('/a/b/', '/a/')
    
    assert not fs.is_subpath('a', 'a')
    assert not fs.is_subpath('/a', '/a')
    assert not fs.is_subpath('a/', 'a/')
    assert not fs.is_subpath('/a/', '/a/')
