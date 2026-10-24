from app.analyzers.file.inspect import detect_mime


def test_svg_namespace_is_not_treated_as_prose():
    assert detect_mime(b'<?xml version="1.0"?>\n<!-- logo -->\n<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0"/></svg>') == 'image/svg+xml'
    assert detect_mime(b'This text mentions <svg> as an example.') == 'text/plain'
    assert detect_mime(b'<html><body><svg></svg></body></html>') == 'text/html'
