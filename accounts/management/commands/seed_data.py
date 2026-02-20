"""
python manage.py seed_data
Seeds: 5 portal users, 28 NDA templates, 13 people
"""
import hashlib
from django.core.management.base import BaseCommand
from accounts.models import User
from ndas.models import NDATemplate, NDAVersion
from people.models import Person


NDAS = [
    ("Employee NDA", "employee", "2.1", "Core confidentiality — trade secrets, client data, methodologies, tools."),
    ("Employee IP & Invention Assignment", "employee", "1.3", "All work product, tools, scripts, code belong to the company."),
    ("Non-Compete & Non-Solicitation", "employee", "1.5", "Prevents competing or poaching clients/employees after departure."),
    ("Acceptable Use Policy", "employee", "3.0", "Rules for using company and client systems, networks, data."),
    ("Exit / Separation NDA", "employee", "1.2", "Reinforced obligations signed during offboarding."),
    ("Remote Work Security Agreement", "employee", "2.0", "Security requirements for remote and hybrid work."),
    ("Client Mutual NDA", "client", "2.4", "Standard mutual NDA before client engagement begins."),
    ("PenTest / VAPT Authorization", "client", "1.8", "Authorization + confidentiality for penetration testing."),
    ("Incident Response NDA", "client", "1.1", "Heightened confidentiality during breach response engagements."),
    ("Data Processing Agreement (DPA)", "client", "3.2", "GDPR/DPDP compliant data processing agreement."),
    ("Red Team / Forensics NDA", "client", "1.0", "NDA for offensive security and digital forensics."),
    ("Business Partner Mutual NDA", "partner", "2.0", "Standard mutual NDA for business partnerships."),
    ("Technology Integration Partner NDA", "partner", "1.4", "For sharing APIs, source code, infrastructure with tech partners."),
    ("Channel / Reseller Partner NDA", "partner", "1.2", "Confidentiality for channel and reseller partners."),
    ("Consultant NDA", "consultant", "1.6", "Core confidentiality agreement for external consultants."),
    ("Consultant IP & Work Product", "consultant", "1.3", "All consultant deliverables are company property."),
    ("Consultant Data Handling & Destruction", "consultant", "1.1", "Data management, retention, and secure destruction."),
    ("Freelancer NDA", "freelancer", "2.0", "Core confidentiality for freelance contractors."),
    ("Freelancer IP Assignment", "freelancer", "1.5", "IP assignment for all freelancer deliverables."),
    ("Subcontracting Restriction", "freelancer", "1.0", "Prevents outsourcing work to third parties."),
    ("Freelancer Exit & Data Destruction", "freelancer", "1.0", "Data return and destruction after engagement ends."),
    ("Vendor NDA", "vendor", "1.8", "Standard confidentiality for vendors and suppliers."),
    ("SaaS / Cloud Provider NDA", "vendor", "2.1", "Enhanced NDA for cloud and SaaS vendors."),
    ("Subcontractor Flow-Down NDA", "vendor", "1.0", "Vendor subcontractors bound by same confidentiality terms."),
    ("Investor / Funding NDA", "additional", "1.3", "Confidentiality for investor due diligence."),
    ("Visitor / Facility Access NDA", "additional", "1.0", "Short-form NDA for office and facility visitors."),
    ("Recruitment Candidate NDA", "additional", "1.5", "NDA for candidates exposed to sensitive info during interviews."),
    ("Threat Intelligence Sharing NDA", "additional", "1.0", "Framework for sharing threat intel with CERTs and ISACs."),
]

PEOPLE = [
    ("employee", "Raj Patel", "raj@company.com", "Security Analyst", "", "EMP001", "SOC"),
    ("employee", "Priya Sharma", "priya@company.com", "SOC Engineer", "", "EMP002", "SOC"),
    ("employee", "Anita Desai", "anita@company.com", "Pen Tester", "", "EMP003", "Red Team"),
    ("employee", "Vikram Singh", "vikram@company.com", "Security Architect", "", "EMP004", "Engineering"),
    ("customer", "Alex Chen", "alex@techcorp.com", "CTO", "TechCorp Inc.", "", ""),
    ("customer", "John Murray", "john@financehub.com", "CISO", "FinanceHub Ltd.", "", ""),
    ("customer", "Kenji Tanaka", "kenji@globalretail.jp", "VP Engineering", "GlobalRetail", "", ""),
    ("vendor", "Sarah Williams", "sarah@vendor.io", "Account Manager", "Vendor.io", "", ""),
    ("vendor", "Tom Baker", "tom@cloudhost.com", "Solutions Architect", "CloudHost Systems", "", ""),
    ("freelancer", "Mike Johnson", "mike@freelance.dev", "Full Stack Developer", "", "", ""),
    ("freelancer", "Emily Zhang", "emily@freelance.io", "Security Researcher", "", "", ""),
    ("consultant", "Lisa Brown", "lisa@consulting.co", "Senior Consultant", "Brown Consulting", "", ""),
    ("consultant", "David Kim", "david@advisors.com", "Strategy Director", "Kim & Partners", "", ""),
]


class Command(BaseCommand):
    help = "Seed database: 5 users, 28 NDA templates, 13 people"

    def handle(self, *args, **kwargs):
        self.stdout.write("\n🛡️  NDA Shield — Seeding Database...\n")

        # ── Users ──
        users_config = [
            ("admin@cybersec.com", "Admin User", "super_admin", "admin123", True),
            ("legal@cybersec.com", "Legal Lead", "legal", "legal123", True),
            ("hr@cybersec.com", "HR Manager", "hr", "hr123", False),
            ("manager@cybersec.com", "Team Manager", "manager", "manager123", False),
            ("employee@cybersec.com", "Regular Employee", "employee", "employee123", False),
        ]

        admin_user = None
        for email, name, role, pwd, is_staff in users_config:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "full_name": name,
                    "role": role,
                    "is_staff": is_staff,
                },
            )
            if created:
                user.set_password(pwd)
                user.save()
                self.stdout.write(f"  ✅ User: {name} ({email} / {pwd})")
            if role == "super_admin":
                admin_user = user

        # ── NDA Templates ──
        self.stdout.write(f"\n  📄 Creating {len(NDAS)} NDA templates...")
        for name, category, version, description in NDAS:
            slug = (
                name.lower()
                .replace(" ", "-")
                .replace("/", "-")
                .replace("&", "and")
                .replace("(", "")
                .replace(")", "")
            )[:240]

            tpl, created = NDATemplate.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "category": category,
                    "description": description,
                    "status": "active",
                    "created_by": admin_user,
                },
            )
            if created:
                html = (
                    f"<h1>{name}</h1>"
                    f"<h2>Confidentiality Agreement</h2>"
                    f"<p><strong>Company:</strong> CyberSec Corp</p>"
                    f"<p><strong>Category:</strong> {category.title()}</p>"
                    f"<hr/>"
                    f"<p>{description}</p>"
                    f"<h3>1. Definitions</h3>"
                    f"<p>'Confidential Information' means all non-public information disclosed by the Company...</p>"
                    f"<h3>2. Obligations</h3>"
                    f"<p>The Receiving Party shall hold and maintain the Confidential Information in strict confidence...</p>"
                    f"<h3>3. Term</h3>"
                    f"<p>This agreement shall remain in effect for 5 years from the date of signing.</p>"
                    f"<h3>4. Return of Materials</h3>"
                    f"<p>Upon termination, all materials must be returned or destroyed within 30 days.</p>"
                )
                plain = (
                    f"{name}\nConfidentiality Agreement\n\n"
                    f"Company: CyberSec Corp\nCategory: {category.title()}\n\n"
                    f"{description}\n\n"
                    f"1. DEFINITIONS\n'Confidential Information' means all non-public information...\n\n"
                    f"2. OBLIGATIONS\nThe Receiving Party shall hold and maintain...\n\n"
                    f"3. TERM\nThis agreement shall remain in effect for 5 years.\n\n"
                    f"4. RETURN OF MATERIALS\nUpon termination, all materials must be returned or destroyed.\n"
                )

                ver = NDAVersion.objects.create(
                    template=tpl,
                    version_number=version,
                    changelog="Initial version",
                    content_html=html,
                    content_plain=plain,
                    content_hash=hashlib.sha256(plain.encode()).hexdigest(),
                    created_by=admin_user,
                )
                tpl.current_version = ver
                tpl.save(update_fields=["current_version"])

        # ── People ──
        self.stdout.write(f"\n  👥 Creating {len(PEOPLE)} people...")
        for ptype, name, email, desig, company, eid, dept in PEOPLE:
            Person.objects.get_or_create(
                email=email,
                person_type=ptype,
                defaults={
                    "full_name": name,
                    "designation": desig,
                    "company_name": company,
                    "employee_id": eid,
                    "department": dept,
                    "created_by": admin_user,
                },
            )

        self.stdout.write(self.style.SUCCESS("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛡️  Database seeded successfully!

   Login:  admin@cybersec.com / admin123
   API:    http://localhost:8000/api/docs/
   Admin:  http://localhost:8000/admin/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""))
