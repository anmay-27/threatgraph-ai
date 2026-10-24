import zipfile
import fitz
from app.analyzers.file.document import inspect_document
from app.analyzers.file.inspect import detect_mime

def test_office_text_macro_and_external_template(tmp_path):
    path=tmp_path/'sample.docx'
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('[Content_Types].xml','<Types/>')
        z.writestr('word/document.xml','<document><t>Registration fee requested</t></document>')
        z.writestr('word/vbaProject.bin',b'dummy inert fixture')
        z.writestr('word/_rels/document.xml.rels','<Relationships><Relationship TargetMode="External" Target="https://example.com/template" Type="template"/></Relationships>')
    mime=detect_mime(path.read_bytes())
    assert 'wordprocessingml' in mime
    text,evidence,links=inspect_document(path,mime,'a')
    assert 'Registration fee' in text
    assert {'office_macros','office_external_resource'} <= {e.label for e in evidence}
    assert links==['https://example.com/template']

def test_pdf_text_and_link_inventory(tmp_path):
    path=tmp_path/'sample.pdf'
    with fitz.open() as doc:
        page=doc.new_page();page.insert_text((40,40),'Quarterly report')
        page.insert_link({'kind':fitz.LINK_URI,'from':fitz.Rect(40,30,100,45),'uri':'https://example.com'})
        doc.save(path)
    text,evidence,links=inspect_document(path,'application/pdf','a')
    assert 'Quarterly report' in text
    assert links==['https://example.com']
    assert evidence[0].metadata['units_inspected']==1

def test_blank_pdf_does_not_claim_text_was_read(tmp_path):
    path=tmp_path/'scan.pdf'
    with fitz.open() as doc:doc.new_page();doc.save(path)
    text,evidence,_=inspect_document(path,'application/pdf','a')
    assert not text.strip()
    assert any(e.label=='unavailable' for e in evidence)

def test_avi_mime_alias_is_not_disguised_content(tmp_path, monkeypatch):
    import app.analyzers.file.inspect as module
    path=tmp_path/'sample.avi';path.write_bytes(b'fixture')
    monkeypatch.setattr(module,'detect_mime',lambda _: 'video/x-msvideo')
    monkeypatch.setattr(module.mimetypes,'guess_type',lambda _:('video/avi',None))
    monkeypatch.setattr(module.settings,'clamav_host','')
    monkeypatch.setattr(module.shutil,'which',lambda _:None)
    _, evidence=module.inspect_file(path,path.name,'a')
    assert not any(e.label=='extension_mismatch' for e in evidence)
