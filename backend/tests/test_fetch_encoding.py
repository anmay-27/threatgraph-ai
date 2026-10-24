import gzip
import zlib
import pytest
from app.core.fetch import BoundedBody, UnsafeURL

@pytest.mark.parametrize('encoding,encode',[('gzip',gzip.compress),('deflate',zlib.compress),('identity',lambda b:b)])
def test_bounded_stream_reads_html(encoding,encode):
    original=b'<html><title>Known page</title></html>'
    encoded=encode(original);body=BoundedBody(encoding,1024)
    for i in range(0,len(encoded),3):body.feed(encoded[i:i+3])
    assert body.finish()==original

def test_gzip_bomb_stops_at_expanded_limit():
    body=BoundedBody('gzip',1024)
    with pytest.raises(UnsafeURL,match='Expanded'):body.feed(gzip.compress(b'A'*1000000))
    assert len(body.body)<=1025

def test_truncated_gzip_is_not_inspected_as_complete():
    body=BoundedBody('gzip',1024);body.feed(gzip.compress(b'page')[:-4])
    with pytest.raises(UnsafeURL,match='Incomplete'):body.finish()
