from sqlalchemy import select
from .models import Document, Plan, Audit
from .settings import SOURCE_URL, REVIEW_DATE

PACK = [
 ('What mjPROConnect provides', 'mjPROConnect helps suppliers create a detailed business profile, advertise their products and services, receive buyer requests for quotations (RFQs), and track advertisement engagement. Buyers can find suppliers by category, location, or specialization and view business capabilities.'),
 ('Who can subscribe', 'Suppliers already registered on mjPRO and suppliers new to mjPRO can subscribe to mjPROConnect. Buyer RFQ alerts are matched to supplier product categories and can include buyers the supplier has not worked with before.'),
 ('Subscription and registration', 'The public FAQ lists a six-month subscription at INR 15,000 and a twelve-month subscription at INR 25,000. Both plans include all features. Tax treatment is not stated in that FAQ. Existing users can log in with mjPRO credentials, choose Paid Services, select mjPROConnect, and choose a subscription plan. New suppliers should follow registration on the official website.'),
 ('Subscription expiry', 'The website says subscribers are notified before renewal. If a subscription is not renewed, enhanced visibility of profiles and advertisements ends, and RFQ alerts stop.'),
 ('Support and responsible expectations', 'The published mjPRO helpdesk is +91 33 6603 1747 and support.mjpro@mjunction.in, Monday to Saturday, 9:00 AM to 5:30 PM. The public page contains individual success stories; these do not establish guaranteed leads, orders, revenue, or conversion rates for a new subscriber. Discounts and refund terms have not been verified in this demonstration information pack.')
]

async def seed(db):
    if not await db.scalar(select(Document.id).limit(1)):
        for title, content in PACK:
            doc = Document(title=title, text=content, source=SOURCE_URL, effective_date=REVIEW_DATE, approved=True)
            db.add(doc)
            await db.flush()
            db.add(Audit(document_id=doc.id, action='demo_public_pack', details={'label':'Public website information for demonstration','review_date':REVIEW_DATE}))
    if not await db.scalar(select(Plan.id).limit(1)):
        db.add_all([Plan(name='Six months', amount_minor=1500000, months=6, source=SOURCE_URL, effective_date=REVIEW_DATE), Plan(name='Twelve months', amount_minor=2500000, months=12, source=SOURCE_URL, effective_date=REVIEW_DATE)])
    await db.commit()
