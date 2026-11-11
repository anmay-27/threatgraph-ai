"""Create fictional input files, never canned detector results."""
from pathlib import Path
from email.message import EmailMessage
import cv2
import fitz


def main():
    out=Path('frontend/public/demo');out.mkdir(parents=True,exist_ok=True)
    qr=cv2.QRCodeEncoder_create().encode('https://example.com/')
    qr=cv2.copyMakeBorder(qr,4,4,4,4,cv2.BORDER_CONSTANT,value=255)
    qr=cv2.resize(qr,(420,420),interpolation=cv2.INTER_NEAREST)
    pdf=fitz.open();page=pdf.new_page()
    page.insert_text((40,40),'FICTIONAL DEMO - NOT A REAL JOB OFFER',fontsize=15)
    page.insert_text((40,75),'Registration fee: pay before onboarding. UPI ID: recruitment-demo@demo')
    page.insert_text((40,95),'This invented payment handle must not be used for payments.')
    page.insert_text((40,115),'QR points to benign example.com, not a phishing or payment site.')
    page.insert_image(fitz.Rect(60,150,480,570),stream=cv2.imencode('.png',qr)[1].tobytes())
    content=pdf.tobytes();pdf.close();(out/'fictional-offer.pdf').write_bytes(content)
    email=EmailMessage();email['From']='Demo Recruiter <hr@fictional-employer.example>';email['Reply-To']='review@fictional-payments.example';email['Subject']='FICTIONAL DEMO: job offer'
    email.set_content('FICTIONAL SECURITY DEMO. You have been selected for a job offer. See attached onboarding instructions. All names and identifiers are invented. Do not pay anyone.')
    email.add_attachment(content,maintype='application',subtype='pdf',filename='fictional-offer.pdf')
    (out/'fictional-offer.eml').write_bytes(email.as_bytes())
    (out/'previous-payment.txt').write_text('FICTIONAL PRIOR CASE INPUT. Reported payment identifier: UPI ID: recruitment-demo@demo\nThis invented handle is for correlation demonstration only; no criminal intent is established.\n')
    print(out.resolve())


if __name__=='__main__':main()
