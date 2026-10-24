import fitz
from app.services.reports import wrap_pdf_text


def test_pdf_wrap_uses_measured_width_even_for_long_urls():
    font=fitz.Font('helv')
    text='https://example.com/'+'W'*1000+' readable result'
    lines=wrap_pdf_text(text,font,18)
    assert all(font.text_length(line,fontsize=18)<=505 for line in lines)
    assert ''.join(lines).replace(' ','')==text.replace(' ','')
