"""
Demo seed script for Print Duka presentation.
Run: python manage.py shell < seed_demo.py
Or:  python manage.py shell -c "exec(open('seed_demo.py').read())"
"""
import os, sys, django, random
from decimal import Decimal
from datetime import date, timedelta, datetime
import django.utils.timezone as tz

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'client.settings')

from django.contrib.auth.models import User, Group
from clientapp.models import (
    Client, Lead, Quote, QuoteLineItem, Job, LPO, LPOLineItem,
    Payment, Delivery, QCInspection, Vendor, Product,
    ActivityLog, Notification,
)

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
TODAY = date.today()

def days(n): return TODAY + timedelta(days=n)

# ──────────────────────────────────────────────
# Existing anchors
# ──────────────────────────────────────────────
admin_user     = User.objects.get(username='printduka')
acc_manager    = User.objects.get(username='tckiprotich')
prod_team      = User.objects.get(username='tckiprotich+1')
vendor_user    = User.objects.get(username='tckiprotich+2')
vendor         = Vendor.objects.first()
existing_prod  = Product.objects.first()

print("✅ Loaded existing anchors")

# ──────────────────────────────────────────────
# 1. CLIENTS
# ──────────────────────────────────────────────
clients_data = [
    dict(client_id='CLT-001', company='Safaricom PLC', name='Jane Mwangi',
         email='jane.mwangi@safaricom.co.ke', phone='0722100200',
         industry='Telecommunications', client_type='B2B', status='Active',
         payment_terms='30_days', credit_limit=500000, risk_rating='low'),
    dict(client_id='CLT-002', company='Kenya Airways', name='David Omondi',
         email='david.omondi@kenya-airways.com', phone='0733200300',
         industry='Aviation', client_type='B2B', status='Active',
         payment_terms='60_days', credit_limit=1000000, risk_rating='low'),
    dict(client_id='CLT-003', company='Equity Bank Kenya', name='Sarah Kamau',
         email='sarah.kamau@equitybank.co.ke', phone='0711300400',
         industry='Banking & Finance', client_type='B2B', status='Active',
         payment_terms='30_days', credit_limit=750000, risk_rating='low'),
    dict(client_id='CLT-004', company='Nation Media Group', name='Peter Njoroge',
         email='peter.njoroge@nation.co.ke', phone='0722400500',
         industry='Media', client_type='B2B', status='Active',
         payment_terms='45_days', credit_limit=300000, risk_rating='medium'),
    dict(client_id='CLT-005', company='Radisson Blu Nairobi', name='Aisha Hassan',
         email='aisha.hassan@radissonblu.com', phone='0733500600',
         industry='Hospitality', client_type='B2B', status='Active',
         payment_terms='30_days', credit_limit=200000, risk_rating='low'),
    dict(client_id='CLT-006', company='Strathmore University', name='Prof. Kimani',
         email='p.kimani@strathmore.edu', phone='0722600700',
         industry='Education', client_type='B2B', status='Inactive',
         payment_terms='on_delivery', credit_limit=100000, risk_rating='low'),
]

created_clients = []
for d in clients_data:
    c, _ = Client.objects.get_or_create(
        client_id=d['client_id'],
        defaults=dict(
            company=d['company'], name=d['name'], email=d['email'],
            phone=d['phone'], industry=d['industry'], client_type=d['client_type'],
            status=d['status'], payment_terms=d['payment_terms'],
            credit_limit=d['credit_limit'], risk_rating=d['risk_rating'],
            address='Nairobi, Kenya', account_manager=acc_manager,
            lead_source='Referral',
        )
    )
    created_clients.append(c)

# include existing client
existing_client = Client.objects.get(id=1)
all_clients = [existing_client] + created_clients
print(f"✅ {len(all_clients)} clients ready")

# ──────────────────────────────────────────────
# 2. LEADS
# ──────────────────────────────────────────────
leads_data = [
    dict(lead_id='LEAD-001', name='Michael Otieno', email='m.otieno@techstartup.co.ke',
         phone='0722111222', source='Website', product_interest='Business Cards',
         preferred_contact='Email', preferred_client_type='B2B', status='New'),
    dict(lead_id='LEAD-002', name='Fatuma Ali', email='fatuma@fashionhub.co.ke',
         phone='0733222333', source='Referral', product_interest='Brochures',
         preferred_contact='WhatsApp', preferred_client_type='B2C', status='Contacted'),
    dict(lead_id='LEAD-003', name='James Kariuki', email='jkariuki@logistics.co.ke',
         phone='0711333444', source='Social Media', product_interest='Flyers',
         preferred_contact='Phone', preferred_client_type='B2B', status='Qualified'),
    dict(lead_id='LEAD-004', name='Grace Wanjiku', email='grace@boutique.co.ke',
         phone='0722444555', source='Event', product_interest='Banners',
         preferred_contact='Email', preferred_client_type='B2C', status='Qualified'),
    dict(lead_id='LEAD-005', name='Hassan Mohamed', email='h.mohamed@import.co.ke',
         phone='0733555666', source='Cold Call', product_interest='Packaging',
         preferred_contact='Phone', preferred_client_type='B2B', status='Contacted'),
    dict(lead_id='LEAD-006', name='Lucy Njeri', email='lucy@events.co.ke',
         phone='0722666777', source='Website', product_interest='Roll-up Banners',
         preferred_contact='WhatsApp', preferred_client_type='B2C', status='Lost'),
    dict(lead_id='LEAD-007', name='Robert Maina', email='r.maina@restaurant.co.ke',
         phone='0711777888', source='Referral', product_interest='Menu Cards',
         preferred_contact='Email', preferred_client_type='B2B', status='New'),
]

created_leads = []
for d in leads_data:
    l, _ = Lead.objects.get_or_create(
        lead_id=d['lead_id'],
        defaults=dict(
            name=d['name'], email=d['email'], phone=d['phone'],
            source=d['source'], product_interest=d['product_interest'],
            preferred_contact=d['preferred_contact'],
            preferred_client_type=d['preferred_client_type'],
            status=d['status'], follow_up_date=days(7),
            created_by=acc_manager,
        )
    )
    created_leads.append(l)

print(f"✅ {len(created_leads)} leads created")

# ──────────────────────────────────────────────
# 3. PRODUCTS (print-specific)
# ──────────────────────────────────────────────
products_data = [
    dict(name='Business Cards (Premium)', internal_code='PRD-BC-001',
         primary_category='Stationery', base_price=Decimal('3500.00'),
         short_description='Full colour double-sided premium business cards (500 pcs)'),
    dict(name='A3 Brochures (Tri-fold)', internal_code='PRD-BR-001',
         primary_category='Marketing Materials', base_price=Decimal('8500.00'),
         short_description='Full colour A3 tri-fold brochures (1000 pcs)'),
    dict(name='Roll-up Banner (Pull-up)', internal_code='PRD-BN-001',
         primary_category='Banners & Signage', base_price=Decimal('6500.00'),
         short_description='85x200cm pull-up display banner with carry bag'),
    dict(name='Vinyl Stickers (Cut-out)', internal_code='PRD-ST-001',
         primary_category='Stickers & Labels', base_price=Decimal('2500.00'),
         short_description='Custom cut-out vinyl stickers, waterproof'),
    dict(name='Company Letterheads', internal_code='PRD-LH-001',
         primary_category='Stationery', base_price=Decimal('4500.00'),
         short_description='A4 full colour company letterheads (500 pcs)'),
    dict(name='A1 Poster (Glossy)', internal_code='PRD-PS-001',
         primary_category='Posters', base_price=Decimal('1800.00'),
         short_description='A1 high gloss poster print'),
    dict(name='Branded T-Shirts', internal_code='PRD-TS-001',
         primary_category='Apparel', base_price=Decimal('1200.00'),
         short_description='100% cotton branded T-shirts with logo print'),
    dict(name='Flyers (A5 Full Colour)', internal_code='PRD-FL-001',
         primary_category='Marketing Materials', base_price=Decimal('2200.00'),
         short_description='A5 full colour flyers, both sides (1000 pcs)'),
]

created_products = []
for d in products_data:
    p, _ = Product.objects.get_or_create(
        internal_code=d['internal_code'],
        defaults=dict(
            name=d['name'], primary_category=d['primary_category'],
            base_price=d['base_price'], short_description=d['short_description'],
            long_description=d['short_description'],
            product_type='physical', status='published',
            customization_level='non_customizable',
            unit_of_measure='pieces', stock_status='in_stock',
            stock_quantity=1000, created_by=admin_user, updated_by=admin_user,
        )
    )
    created_products.append(p)

all_products = created_products + [existing_prod]
print(f"✅ {len(created_products)} products created")

# ──────────────────────────────────────────────
# 4. QUOTES
# ──────────────────────────────────────────────
quotes_data = [
    dict(num='002', client=all_clients[0], prod=all_products[0], qty=1000, unit=3.50,  status='Approved',          days_ago=30),
    dict(num='003', client=all_clients[1], prod=all_products[1], qty=2000, unit=8.50,  status='Approved',          days_ago=25),
    dict(num='004', client=all_clients[2], prod=all_products[2], qty=5,    unit=6500,  status='Approved',          days_ago=20),
    dict(num='005', client=all_clients[3], prod=all_products[3], qty=500,  unit=5.0,   status='Sent to Customer',  days_ago=15),
    dict(num='006', client=all_clients[4], prod=all_products[4], qty=500,  unit=9.0,   status='Sent to Customer',  days_ago=12),
    dict(num='007', client=all_clients[5], prod=all_products[5], qty=10,   unit=1800,  status='Costed',            days_ago=10),
    dict(num='008', client=all_clients[0], prod=all_products[6], qty=50,   unit=1200,  status='Draft',             days_ago=5),
    dict(num='009', client=all_clients[1], prod=all_products[7], qty=5000, unit=2.20,  status='Draft',             days_ago=3),
    dict(num='010', client=all_clients[2], prod=all_products[0], qty=2000, unit=3.50,  status='Lost',              days_ago=40),
    dict(num='011', client=all_clients[3], prod=all_products[1], qty=1000, unit=8.50,  status='Sent to PT',        days_ago=8),
    dict(num='012', client=all_clients[4], prod=all_products[2], qty=3,    unit=6500,  status='Sent to PT',        days_ago=6),
]

created_quotes = []
for d in quotes_data:
    qty     = d['qty']
    unit    = Decimal(str(d['unit']))
    subtotal = unit * qty
    tax     = subtotal * Decimal('0.16')
    total   = subtotal + tax
    qdate   = TODAY - timedelta(days=d['days_ago'])
    qid     = f"QT-2026-{d['num']}"

    q, created = Quote.objects.get_or_create(
        quote_id=qid,
        defaults=dict(
            client=d['client'],
            product=d['prod'],
            product_name=d['prod'].name,
            channel='Direct',
            quantity=qty,
            unit_price=unit,
            subtotal=subtotal,
            total_amount=total,
            tax_rate=Decimal('16.00'),
            tax_total=tax,
            discount_total=Decimal('0'),
            adjustment_amount=Decimal('0'),
            shipping_charges=Decimal('0'),
            status=d['status'],
            production_status='Not Started',
            payment_terms='30_days',
            quote_date=qdate,
            valid_until=qdate + timedelta(days=30),
            due_date=qdate + timedelta(days=45),
            notes=f'Demo quote for {d["prod"].name}',
            created_by=acc_manager,
            costed_by=admin_user if d['status'] not in ('Draft',) else None,
        )
    )
    created_quotes.append(q)

print(f"✅ {len(created_quotes)} quotes created")

# ──────────────────────────────────────────────
# 5. JOBS (for Approved quotes)
# ──────────────────────────────────────────────
approved_quotes = [q for q in created_quotes if q.status == 'Approved']
job_statuses = ['pending', 'in_progress', 'completed']
created_jobs = []

for i, q in enumerate(approved_quotes):
    jnum = f"JOB-2026-{str(i+1).zfill(3)}"
    status = job_statuses[i % len(job_statuses)]
    start = q.quote_date + timedelta(days=5)
    expected = start + timedelta(days=14)
    actual = expected if status == 'completed' else None

    j, _ = Job.objects.get_or_create(
        job_number=jnum,
        defaults=dict(
            client=q.client,
            quote=q,
            job_name=f"{q.product_name} - {q.client.company}",
            job_type='Print',
            priority='normal',
            source='Quote',
            product=q.product_name,
            quantity=q.quantity,
            person_in_charge=prod_team,
            status=status,
            start_date=start,
            expected_completion=expected,
            delivery_date=expected + timedelta(days=2),
            actual_completion=actual,
            delivery_method='Delivery',
            notes=f'Production job for {q.quote_id}',
            created_by=acc_manager,
        )
    )
    created_jobs.append(j)

print(f"✅ {len(created_jobs)} jobs created")

# ──────────────────────────────────────────────
# 6. LPOs (for Approved quotes)
# ──────────────────────────────────────────────
created_lpos = []
lpo_statuses = ['Pending', 'Approved', 'Invoiced']

for i, q in enumerate(approved_quotes):
    lnum = f"LPO-2026-{str(i+1).zfill(3)}"
    status = lpo_statuses[i % len(lpo_statuses)]
    vat = q.subtotal * Decimal('0.16')
    total = q.subtotal + vat

    lpo, _ = LPO.objects.get_or_create(
        lpo_number=lnum,
        defaults=dict(
            client=q.client,
            quote=q,
            status=status,
            subtotal=q.subtotal,
            vat_amount=vat,
            total_amount=total,
            payment_terms='30_days',
            delivery_date=q.due_date,
            notes=f'LPO for {q.quote_id}',
            created_by=acc_manager,
            approved_by=admin_user if status != 'Pending' else None,
            approved_at=tz.now() if status != 'Pending' else None,
        )
    )
    created_lpos.append(lpo)

print(f"✅ {len(created_lpos)} LPOs created")

# ──────────────────────────────────────────────
# 7. PAYMENTS (for Approved/Invoiced LPOs)
# ──────────────────────────────────────────────
payable_lpos = [l for l in created_lpos if l.status in ('Approved', 'Invoiced')]
payment_methods = ['bank_transfer', 'mpesa', 'cheque']
created_payments = []

for i, lpo in enumerate(payable_lpos):
    ref = f"PAY-2026-{str(i+1).zfill(3)}"
    method = payment_methods[i % len(payment_methods)]
    p, _ = Payment.objects.get_or_create(
        reference_number=ref,
        defaults=dict(
            lpo=lpo,
            payment_date=TODAY - timedelta(days=random.randint(1, 10)),
            amount=lpo.total_amount,
            payment_method=method,
            status='completed',
            notes=f'Payment for {lpo.lpo_number}',
            recorded_by=acc_manager,
        )
    )
    created_payments.append(p)

print(f"✅ {len(created_payments)} payments created")

# ──────────────────────────────────────────────
# 8. QC INSPECTIONS (for jobs)
# ──────────────────────────────────────────────
qc_statuses = ['passed', 'passed', 'failed', 'rework']
created_qcs = []

for i, job in enumerate(created_jobs):
    qc_status = qc_statuses[i % len(qc_statuses)]
    qc, _ = QCInspection.objects.get_or_create(
        job=job,
        defaults=dict(
            vendor=vendor,
            inspector=prod_team,
            status=qc_status,
            inspection_date=tz.now() - timedelta(days=random.randint(1, 5)),
            color_accuracy=qc_status == 'passed',
            print_quality=qc_status == 'passed',
            cutting_accuracy=qc_status in ('passed', 'rework'),
            finishing_quality=qc_status == 'passed',
            quantity_verified=True,
            packaging_checked=qc_status == 'passed',
            notes=f'QC for {job.job_number} — {qc_status}',
        )
    )
    created_qcs.append(qc)

print(f"✅ {len(created_qcs)} QC inspections created")

# ──────────────────────────────────────────────
# 9. DELIVERIES (for completed/in_progress jobs)
# ──────────────────────────────────────────────
deliverable_jobs = [j for j in created_jobs if j.status in ('completed', 'in_progress')]
delivery_statuses = ['staged', 'in_transit', 'delivered']
created_deliveries = []

for i, job in enumerate(deliverable_jobs):
    if Delivery.objects.filter(job=job).exists():
        created_deliveries.append(Delivery.objects.get(job=job))
        continue
    dnum = f"DEL-2026-{str(i+1).zfill(3)}"
    dstatus = 'delivered' if job.status == 'completed' else delivery_statuses[i % len(delivery_statuses)]
    qc = QCInspection.objects.filter(job=job).first()
    d = Delivery.objects.create(
        delivery_number=dnum,
        job=job,
        qc_inspection=qc,
        status=dstatus,
        staging_location='shelf-a',
        packaging_verified={'boxes': True, 'labels': True},
        package_photos=[],
        notes_to_am=f'Ready for collection — {job.job_name}',
        actual_cost=job.quote.total_amount * Decimal('0.6') if job.quote else Decimal('0'),
        handoff_confirmed=dstatus == 'delivered',
        handoff_confirmed_at=tz.now() if dstatus == 'delivered' else None,
        handoff_confirmed_by=acc_manager if dstatus == 'delivered' else None,
        created_by=prod_team,
    )
    created_deliveries.append(d)

print(f"✅ {len(created_deliveries)} deliveries created")

# ──────────────────────────────────────────────
# Summary
# ──────────────────────────────────────────────
print("\n" + "="*50)
print("🎉 SEED COMPLETE — DEMO DATA SUMMARY")
print("="*50)
print(f"  Clients:       {Client.objects.count()}")
print(f"  Leads:         {Lead.objects.count()}")
print(f"  Products:      {Product.objects.count()}")
print(f"  Quotes:        {Quote.objects.count()}")
print(f"  Jobs:          {Job.objects.count()}")
print(f"  LPOs:          {LPO.objects.count()}")
print(f"  Payments:      {Payment.objects.count()}")
print(f"  QC Inspections:{QCInspection.objects.count()}")
print(f"  Deliveries:    {Delivery.objects.count()}")
print("="*50)
