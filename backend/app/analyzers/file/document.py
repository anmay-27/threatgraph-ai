"""Bounded document extraction and active-content inspection; never execute content."""
import re
import zipfile
import shutil
from xml.etree import ElementTree as ET
from app.schemas.evidence import finding


def inspect_document(path, mime, asset):
    evidence, texts, links, gaps = [], [], [], []
    metadata = {'format': mime, 'units_inspected': 0, 'units_total': 0, 'qr_values': [], 'ocr_pages': []}
    def flag(label, explanation, score):
        evidence.append(finding(asset, 'document_inspector', 'file_security', label, explanation, score, .85))
    if mime == 'application/pdf':
        import fitz
        with fitz.open(path) as doc:
            if doc.needs_pass:
                return '', [finding(asset,'document_inspector','metadata','unavailable','Password-protected PDF: remove encryption from a copy you are authorized to inspect.')], []
            metadata['units_total'] = len(doc)
            metadata['embedded_files'] = doc.embfile_count()
            if doc.embfile_count(): flag('embedded_document_files', 'PDF contains embedded files. Their contents were not extracted or executed.', .5)
            # Inspect parsed objects rather than searching compressed raw PDF bytes.
            for index in range(1, min(doc.xref_length(), 10001)):
                obj = doc.xref_object(index)
                if re.search(r'/(JavaScript|JS)\b', obj):
                    flag('pdf_javascript', 'PDF contains JavaScript actions. Scripts were not executed; review before opening in a script-enabled reader.', .65); break
            if doc.xref_length() > 10001: gaps.append('PDF object inspection limited to 10,000 objects.')
            for page in list(doc)[:30]:
                text = page.get_text()[:20000]
                if page.number < 10:
                    import numpy as np
                    from app.analyzers.image.inspect import decode_qr
                    scale = min(1.5, 1800 / max(page.rect.width,page.rect.height))
                    pix = page.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csRGB,alpha=False)
                    pixels=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,3)
                    metadata['qr_values'].extend(decode_qr(pixels))
                    if not text.strip() and page.number < 5 and shutil.which('tesseract'):
                        try:
                            import pytesseract
                            text=pytesseract.image_to_string(pixels,timeout=5)[:20000]
                            if text.strip():metadata['ocr_pages'].append(page.number+1)
                        except (ImportError,RuntimeError):
                            gaps.append(f'OCR did not complete on page {page.number + 1}.')
                if not text.strip(): gaps.append(f'Page {page.number + 1} has no extractable text; scanned-image text was not read.')
                texts.append(text)
                links.extend(link['uri'] for link in page.get_links() if link.get('uri','').startswith(('https://','http://')))
                metadata['units_inspected'] += 1
            if len(doc)>30: gaps.append('Text and links inspected on the first 30 pages only.')
            if len(doc)>10: gaps.append('QR inspection covers the first 10 pages only.')
    else:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if len(entries)>2000 or sum(e.file_size for e in entries)>50*1024*1024 or any(e.file_size>5*1024*1024 or e.file_size/max(e.compress_size,1)>200 for e in entries):
                return '', [finding(asset,'document_inspector','metadata','unavailable','Office document expansion exceeds inspection limits; contents were not decompressed.')], []
            names = {e.filename for e in entries}
            if any(n.lower().endswith('vbaproject.bin') for n in names): flag('office_macros','Office document contains a VBA macro project. Macros were not executed.',.7)
            if any('/embeddings/' in n for n in names): flag('office_embedded_objects','Office document contains embedded objects. Their contents were not executed or analyzed.',.5)
            for entry in entries:
                name=entry.filename
                if not name.endswith(('.xml','.rels')): continue
                data=archive.read(entry)
                if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
                    gaps.append('XML declarations prevented safe parsing of a document part.'); continue
                try: root=ET.fromstring(data)
                except ET.ParseError:
                    gaps.append('A document XML part could not be parsed.'); continue
                if name.endswith('.rels'):
                    for element in root.iter():
                        target=element.attrib.get('Target','')
                        if element.attrib.get('TargetMode')=='External':
                            if target.startswith(('http://','https://')): links.append(target)
                            if not element.attrib.get('Type','').endswith('/hyperlink'):
                                flag('office_external_resource','Document declares an external template or resource. Opening it may request remote content.',.5)
                elif name.startswith(('word/','ppt/slides/','xl/')):
                    metadata['units_total'] += 1
                    if metadata['units_inspected']<100:
                        texts.append(' '.join(e.text or '' for e in root.iter() if e.tag.rsplit('}',1)[-1] in {'t','v'})[:20000])
                        metadata['units_inspected'] += 1
            if metadata['units_total']>100: gaps.append('Only the first 100 XML content parts were read.')
    text='\n'.join(texts)[:100000]
    metadata.update(text_characters=len(text), text_preview=text[:3000], links=list(dict.fromkeys(links))[:50], limitations=list(dict.fromkeys(gaps)))
    evidence.insert(0,finding(asset,'document_inspector','metadata','document_summary',f"Inspected {metadata['units_inspected']} document pages or content parts; extracted {len(text)} text characters and {len(set(links))} external links. Document origin and factual accuracy are not established.",metadata=metadata))
    if gaps: evidence.append(finding(asset,'document_inspector','metadata','unavailable',' '.join(dict.fromkeys(gaps))))
    return text,evidence,metadata['links']
